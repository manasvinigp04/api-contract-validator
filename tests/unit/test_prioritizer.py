"""
Unit tests for risk-based prioritizer.
"""

import pytest

from api_contract_validator.config.models import TestGenerationConfig
from api_contract_validator.generation.base import TestCase, TestCaseType, TestSuite
from api_contract_validator.generation.prioritizer.risk_ranker import RiskBasedPrioritizer
from api_contract_validator.input.normalizer.models import HTTPMethod


@pytest.mark.unit
class TestRiskBasedPrioritizer:
    """Test RiskBasedPrioritizer class."""

    @pytest.fixture
    def config(self):
        """Default test generation config."""
        return TestGenerationConfig(enable_prioritization=True)

    @pytest.fixture
    def prioritizer(self, config):
        """Create RiskBasedPrioritizer instance."""
        return RiskBasedPrioritizer(config)

    @pytest.fixture
    def sample_test_suite(self, valid_test_case, invalid_test_case, boundary_test_case):
        """Create sample test suite with mixed priorities."""
        suite = TestSuite(name="Test Suite", description="Sample")
        suite.add_test(valid_test_case)
        suite.add_test(invalid_test_case)
        suite.add_test(boundary_test_case)
        return suite

    def test_prioritize_modifies_priorities(self, prioritizer, sample_test_suite):
        """Test that prioritize recalculates all priorities."""
        original_priorities = [t.priority for t in sample_test_suite.test_cases]

        result = prioritizer.prioritize(sample_test_suite)

        # Priorities should be recalculated
        new_priorities = [t.priority for t in result.test_cases]
        # At least some should be different (due to multipliers)
        assert new_priorities != original_priorities or len(new_priorities) < 2

    def test_prioritize_sorts_by_priority(self, prioritizer, sample_test_suite):
        """Test that tests are sorted by priority descending."""
        result = prioritizer.prioritize(sample_test_suite)

        priorities = [t.priority for t in result.test_cases]
        assert priorities == sorted(priorities, reverse=True)

    def test_critical_endpoint_multiplier(self, prioritizer, simple_post_endpoint):
        """Test that POST/PUT/DELETE endpoints get priority boost."""
        test_case = TestCase(
            test_id="test_1",
            endpoint=simple_post_endpoint,
            test_type=TestCaseType.VALID,
            description="Test",
            method=HTTPMethod.POST,
            path="/users",
            expected_status=201,
            priority=1.0,
        )

        suite = TestSuite(name="Test", description="Test")
        suite.add_test(test_case)

        result = prioritizer.prioritize(suite)

        # POST should get 1.5x multiplier
        assert result.test_cases[0].priority >= 1.4  # ~1.5 accounting for rounding

    def test_high_complexity_multiplier(self, prioritizer, simple_post_endpoint):
        """Test that high complexity tests get priority boost."""
        # Create test with many fields (>10 for high complexity)
        request_body = {f"field{i}": f"value{i}" for i in range(15)}

        test_case = TestCase(
            test_id="test_1",
            endpoint=simple_post_endpoint,
            test_type=TestCaseType.VALID,
            description="Complex test",
            method=HTTPMethod.POST,
            path="/users",
            request_body=request_body,
            expected_status=201,
            priority=1.0,
        )

        suite = TestSuite(name="Test", description="Test")
        suite.add_test(test_case)

        result = prioritizer.prioritize(suite)

        # High complexity should get 1.2x multiplier
        assert result.test_cases[0].priority > 1.0

    def test_invalid_test_multiplier(self, prioritizer, invalid_test_case):
        """Test that invalid tests get priority boost."""
        suite = TestSuite(name="Test", description="Test")
        suite.add_test(invalid_test_case)

        result = prioritizer.prioritize(suite)

        # Invalid tests get 1.3x multiplier
        assert result.test_cases[0].priority >= 1.3 * invalid_test_case.priority

    def test_select_top_tests(self, prioritizer):
        """Test selecting top N tests by priority."""
        # Create suite with varying priorities
        suite = TestSuite(name="Test", description="Test")
        for i, priority in enumerate([1.0, 2.0, 0.5, 1.5, 0.8]):
            from api_contract_validator.input.normalizer.models import Endpoint, HTTPMethod, ResponseBody

            endpoint = Endpoint(
                path="/test", method=HTTPMethod.GET, responses=[ResponseBody(status_code=200, schema={})]
            )
            test = TestCase(
                test_id=f"test_{i}",
                endpoint=endpoint,
                test_type=TestCaseType.VALID,
                description=f"Test {i}",
                method=HTTPMethod.GET,
                path="/test",
                expected_status=200,
                priority=priority,
            )
            suite.add_test(test)

        top_tests = prioritizer.select_top_tests(suite, max_tests=3)

        assert len(top_tests) == 3
        # Should be top 3 priorities: 2.0, 1.5, 1.0
        priorities = [t.priority for t in top_tests]
        assert priorities == [2.0, 1.5, 1.0]

    def test_priority_distribution(self, prioritizer, sample_test_suite):
        """Test getting priority distribution."""
        distribution = prioritizer.get_priority_distribution(sample_test_suite)

        assert isinstance(distribution, dict)
        # Should have at least some priority levels
        assert len(distribution) > 0

    def test_calculate_complexity(self, prioritizer):
        """Test complexity calculation."""
        from api_contract_validator.input.normalizer.models import Endpoint, HTTPMethod, ResponseBody, Parameter, FieldType, FieldConstraint

        # High complexity: many path params + query params + body fields
        endpoint = Endpoint(
            path="/test/{id}/{category}",
            method=HTTPMethod.POST,
            parameters=[
                Parameter(name="id", location="path", type=FieldType.INTEGER, constraints=FieldConstraint(required=True)),
                Parameter(name="category", location="path", type=FieldType.STRING, constraints=FieldConstraint(required=True)),
                Parameter(name="filter", location="query", type=FieldType.STRING, constraints=FieldConstraint(required=False)),
            ],
            responses=[ResponseBody(status_code=201, schema={})],
        )

        test_case = TestCase(
            test_id="test_1",
            endpoint=endpoint,
            test_type=TestCaseType.VALID,
            description="Complex test",
            method=HTTPMethod.POST,
            path="/test/{id}/{category}",
            path_params={"id": 1, "category": "cat"},
            query_params={"filter": "active"},
            request_body={f"field{i}": f"value{i}" for i in range(8)},
            expected_status=201,
            priority=1.0,
        )

        complexity = prioritizer._calculate_complexity(test_case)

        # 2 path + 1 query + 8 body = 11 fields
        assert complexity >= 11

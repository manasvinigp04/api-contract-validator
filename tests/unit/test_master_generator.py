"""
Unit tests for master test generator.
"""

import pytest

from api_contract_validator.config.models import TestGenerationConfig
from api_contract_validator.generation.base import TestCase, TestCaseType
from api_contract_validator.generation.test_generator import MasterTestGenerator, generate_tests


@pytest.mark.unit
class TestMasterTestGenerator:
    """Test MasterTestGenerator orchestrator."""

    @pytest.fixture
    def default_config(self):
        """Default test generation config."""
        return TestGenerationConfig(
            generate_valid=True,
            generate_invalid=True,
            generate_boundary=True,
            max_tests_per_endpoint=50,
            enable_prioritization=True,
        )

    @pytest.fixture
    def generator(self, default_config):
        """Create MasterTestGenerator instance."""
        return MasterTestGenerator(default_config)

    def test_generate_test_suite_all_types(self, generator, simple_unified_spec):
        """Test generating test suite with all test types."""
        test_suite = generator.generate_test_suite(simple_unified_spec)

        assert test_suite.name == f"Test Suite - {simple_unified_spec.metadata.title}"
        assert len(test_suite.test_cases) > 0

        # Should have valid, invalid, and boundary tests
        valid_tests = test_suite.get_valid_tests()
        invalid_tests = test_suite.get_invalid_tests()
        boundary_tests = test_suite.get_boundary_tests()

        assert len(valid_tests) > 0
        assert len(invalid_tests) > 0
        assert len(boundary_tests) > 0

    def test_generate_with_prioritization_enabled(self, simple_unified_spec):
        """Test that prioritization is applied when enabled."""
        config = TestGenerationConfig(enable_prioritization=True, max_tests_per_endpoint=100)
        generator = MasterTestGenerator(config)

        test_suite = generator.generate_test_suite(simple_unified_spec)

        # Tests should be sorted by priority (descending)
        priorities = [t.priority for t in test_suite.test_cases]
        assert priorities == sorted(priorities, reverse=True)

    def test_generate_with_prioritization_disabled(self, simple_unified_spec):
        """Test generation with prioritization disabled."""
        config = TestGenerationConfig(enable_prioritization=False, max_tests_per_endpoint=100)
        generator = MasterTestGenerator(config)

        test_suite = generator.generate_test_suite(simple_unified_spec)

        # Tests should still be generated
        assert len(test_suite.test_cases) > 0

    def test_respect_config_flags(self, simple_unified_spec):
        """Test that generator respects config flags."""
        # Only generate valid tests
        config = TestGenerationConfig(
            generate_valid=True,
            generate_invalid=False,
            generate_boundary=False,
        )
        generator = MasterTestGenerator(config)

        test_suite = generator.generate_test_suite(simple_unified_spec)

        # Should only have valid tests
        assert len(test_suite.get_valid_tests()) > 0
        assert len(test_suite.get_invalid_tests()) == 0
        assert len(test_suite.get_boundary_tests()) == 0

    def test_limit_tests_per_endpoint(self, simple_unified_spec):
        """Test that tests are limited per endpoint."""
        config = TestGenerationConfig(
            max_tests_per_endpoint=5,  # Low limit
            enable_prioritization=True,
        )
        generator = MasterTestGenerator(config)

        test_suite = generator.generate_test_suite(simple_unified_spec)

        # Count tests per endpoint
        from collections import defaultdict

        tests_per_endpoint = defaultdict(int)
        for test in test_suite.test_cases:
            tests_per_endpoint[test.endpoint.endpoint_id] += 1

        # Each endpoint should have at most 5 tests
        for endpoint_id, count in tests_per_endpoint.items():
            assert count <= 5

    def test_limit_total_tests(self):
        """Test that total tests are capped."""
        from api_contract_validator.input.normalizer.models import (
            APIMetadata,
            Endpoint,
            HTTPMethod,
            ResponseBody,
            SourceType,
            UnifiedAPISpec,
        )

        # Create spec with 3 endpoints
        endpoints = [
            Endpoint(path=f"/resource{i}", method=HTTPMethod.GET, responses=[ResponseBody(status_code=200, schema={})])
            for i in range(3)
        ]

        spec = UnifiedAPISpec(
            source_type=SourceType.OPENAPI,
            source_path="/test/spec.yaml",
            metadata=APIMetadata(title="Multi Endpoint API", version="1.0.0"),
            endpoints=endpoints,
        )

        # Max 10 tests per endpoint, 3 endpoints = max 30 total
        config = TestGenerationConfig(max_tests_per_endpoint=10)
        generator = MasterTestGenerator(config)

        test_suite = generator.generate_test_suite(spec)

        # Should be capped at 30 tests
        assert len(test_suite.test_cases) <= 30

    def test_test_distribution_calculation(self, generator, simple_unified_spec):
        """Test that test distribution is calculated correctly."""
        test_suite = generator.generate_test_suite(simple_unified_spec)

        distribution = generator._get_test_distribution(test_suite)

        assert "valid" in distribution
        assert "invalid" in distribution
        assert "boundary" in distribution
        assert "total" in distribution

        # Total should equal sum of all types
        assert distribution["total"] == (
            distribution["valid"] + distribution["invalid"] + distribution["boundary"]
        )

    def test_multiple_endpoints_all_tested(self):
        """Test that all endpoints in spec are tested."""
        from api_contract_validator.input.normalizer.models import (
            APIMetadata,
            Endpoint,
            HTTPMethod,
            ResponseBody,
            SourceType,
            UnifiedAPISpec,
        )

        endpoints = [
            Endpoint(path="/users", method=HTTPMethod.GET, responses=[ResponseBody(status_code=200, schema={})]),
            Endpoint(path="/users", method=HTTPMethod.POST, responses=[ResponseBody(status_code=201, schema={})]),
            Endpoint(path="/posts", method=HTTPMethod.GET, responses=[ResponseBody(status_code=200, schema={})]),
        ]

        spec = UnifiedAPISpec(
            source_type=SourceType.OPENAPI,
            source_path="/test/spec.yaml",
            metadata=APIMetadata(title="Multi Resource API", version="1.0.0"),
            endpoints=endpoints,
        )

        config = TestGenerationConfig()
        generator = MasterTestGenerator(config)

        test_suite = generator.generate_test_suite(spec)

        # Should have tests for all 3 endpoints
        tested_endpoints = {t.endpoint.endpoint_id for t in test_suite.test_cases}
        expected_endpoints = {e.endpoint_id for e in endpoints}
        assert tested_endpoints == expected_endpoints

    def test_convenience_function(self, simple_unified_spec, default_config):
        """Test the convenience function wrapper."""
        test_suite = generate_tests(simple_unified_spec, default_config)

        assert test_suite.name == f"Test Suite - {simple_unified_spec.metadata.title}"
        assert len(test_suite.test_cases) > 0

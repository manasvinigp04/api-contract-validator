"""
Unit tests for result collector.
"""

import pytest

from api_contract_validator.execution.collector.result_collector import (
    ExecutionSummary,
    ResultCollector,
)
from api_contract_validator.execution.runner.executor import TestResult


@pytest.mark.unit
class TestResultCollector:
    """Test ResultCollector class."""

    @pytest.fixture
    def collector(self):
        """Create ResultCollector instance."""
        return ResultCollector()

    @pytest.fixture
    def sample_test_results(self, valid_test_case, invalid_test_case):
        """Create sample test results."""
        return [
            TestResult(
                test_case=valid_test_case,
                status_code=200,
                response_body={"id": 1},
                execution_time_ms=150.0,
                passed=True,
            ),
            TestResult(
                test_case=invalid_test_case,
                status_code=400,
                response_body={"error": "bad_request"},
                execution_time_ms=120.0,
                passed=True,
            ),
            TestResult(
                test_case=valid_test_case,
                status_code=500,
                response_body={"error": "internal_error"},
                execution_time_ms=200.0,
                error="Server error",
                passed=False,
            ),
        ]

    def test_add_result_single(self, collector, sample_test_results):
        """Test adding a single result."""
        collector.add_result(sample_test_results[0])

        assert len(collector.results) == 1

    def test_add_results_multiple(self, collector, sample_test_results):
        """Test adding multiple results."""
        collector.add_results(sample_test_results)

        assert len(collector.results) == 3

    def test_get_summary_statistics(self, collector, sample_test_results):
        """Test summary statistics calculation."""
        collector.add_results(sample_test_results)
        summary = collector.get_summary()

        assert isinstance(summary, ExecutionSummary)
        assert summary.total == 3
        assert summary.passed == 2
        assert summary.failed == 1
        assert summary.pass_rate == pytest.approx(66.67, rel=0.1)

    def test_get_summary_avg_execution_time(self, collector, sample_test_results):
        """Test average execution time calculation."""
        collector.add_results(sample_test_results)
        summary = collector.get_summary()

        # (150 + 120 + 200) / 3 = 156.67
        assert summary.avg_execution_time == pytest.approx(156.67, rel=0.1)

    def test_get_results_by_endpoint(self, collector, sample_test_results):
        """Test getting results for a specific endpoint."""
        collector.add_results(sample_test_results)

        # Get unique endpoint IDs
        endpoint_ids = {r.test_case.endpoint.endpoint_id for r in sample_test_results}

        for endpoint_id in endpoint_ids:
            results = collector.get_results_by_endpoint(endpoint_id)
            assert isinstance(results, list)
            assert all(r.test_case.endpoint.endpoint_id == endpoint_id for r in results)

    def test_get_failed_results_filter(self, collector, sample_test_results):
        """Test filtering failed results."""
        collector.add_results(sample_test_results)
        summary = collector.get_summary()

        failed = summary.get_failed_results()

        assert len(failed) == 1
        assert failed[0].passed is False
        assert failed[0].status_code == 500

    def test_get_status_code_distribution(self, collector, sample_test_results):
        """Test status code distribution calculation."""
        collector.add_results(sample_test_results)
        summary = collector.get_summary()

        distribution = summary.get_status_code_distribution()

        assert isinstance(distribution, dict)
        assert distribution.get(200) == 1
        assert distribution.get(400) == 1
        assert distribution.get(500) == 1

    def test_clear_results(self, collector, sample_test_results):
        """Test clearing results collection."""
        collector.add_results(sample_test_results)
        assert len(collector.results) == 3

        collector.clear()

        assert len(collector.results) == 0

    def test_empty_results_edge_case(self, collector):
        """Test summary with no results."""
        summary = collector.get_summary()

        assert summary.total == 0
        assert summary.passed == 0
        assert summary.failed == 0
        assert summary.pass_rate == 0.0
        assert summary.avg_execution_time == 0.0

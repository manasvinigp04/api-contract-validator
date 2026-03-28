"""
Result Collector

Aggregates and analyzes test execution results.
"""

from typing import Dict, List

from api_contract_validator.config.logging import get_logger
from api_contract_validator.execution.runner.executor import TestResult
from api_contract_validator.generation.base import TestCaseType

logger = get_logger(__name__)


class ExecutionSummary:
    """Summary of test execution results."""

    def __init__(self, results: List[TestResult]):
        self.results = results
        self.total = len(results)
        self.passed = sum(1 for r in results if r.passed)
        self.failed = self.total - self.passed
        self.pass_rate = (self.passed / self.total * 100) if self.total > 0 else 0.0
        self.avg_execution_time = (
            sum(r.execution_time_ms for r in results) / self.total if self.total > 0 else 0.0
        )
        self.errors = [r for r in results if r.error]

    def get_by_type(self, test_type: TestCaseType) -> List[TestResult]:
        """Get results filtered by test type."""
        return [r for r in self.results if r.test_case.test_type == test_type]

    def get_failed_results(self) -> List[TestResult]:
        """Get all failed test results."""
        return [r for r in self.results if not r.passed]

    def get_status_code_distribution(self) -> Dict[int, int]:
        """Get distribution of status codes."""
        distribution = {}
        for result in self.results:
            if result.status_code:
                distribution[result.status_code] = distribution.get(result.status_code, 0) + 1
        return distribution


class ResultCollector:
    """Collects and aggregates test results."""

    def __init__(self):
        self.results: List[TestResult] = []

    def add_result(self, result: TestResult) -> None:
        """Add a test result."""
        self.results.append(result)

    def add_results(self, results: List[TestResult]) -> None:
        """Add multiple test results."""
        self.results.extend(results)

    def get_summary(self) -> ExecutionSummary:
        """Get execution summary."""
        return ExecutionSummary(self.results)

    def get_results_by_endpoint(self, endpoint_id: str) -> List[TestResult]:
        """Get results for a specific endpoint."""
        return [r for r in self.results if r.test_case.endpoint.endpoint_id == endpoint_id]

    def clear(self) -> None:
        """Clear all results."""
        self.results = []

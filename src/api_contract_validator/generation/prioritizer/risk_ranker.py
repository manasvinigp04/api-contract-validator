"""
Risk-Based Test Prioritizer

Prioritizes test cases based on risk factors.
"""

from typing import Dict, List

from api_contract_validator.config.logging import get_logger
from api_contract_validator.config.models import TestGenerationConfig
from api_contract_validator.generation.base import TestCase, TestSuite
from api_contract_validator.input.normalizer.models import HTTPMethod

logger = get_logger(__name__)


class RiskBasedPrioritizer:
    """
    Prioritizes test cases based on risk assessment.
    """

    def __init__(self, config: TestGenerationConfig):
        self.config = config
        self.weights = config.prioritization_weights

    def prioritize(self, test_suite: TestSuite) -> TestSuite:
        """
        Apply risk-based prioritization to test suite.

        Args:
            test_suite: Test suite to prioritize

        Returns:
            Test suite with updated priorities
        """
        logger.info(f"Applying risk-based prioritization to {len(test_suite.test_cases)} tests")

        for test_case in test_suite.test_cases:
            priority = self._calculate_priority(test_case)
            test_case.priority = priority

        # Sort by priority (highest first)
        test_suite.test_cases.sort(key=lambda tc: tc.priority, reverse=True)

        logger.info(f"Prioritization complete. Top priority: {test_suite.test_cases[0].priority:.2f}")

        return test_suite

    def _calculate_priority(self, test_case: TestCase) -> float:
        """Calculate priority score for a test case."""
        base_priority = test_case.priority

        # Critical endpoint weight (POST, PUT, DELETE, PATCH)
        if test_case.method in [HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.DELETE, HTTPMethod.PATCH]:
            base_priority *= self.weights.get("critical_endpoints", 1.5)

        # Complexity weight (based on number of fields)
        complexity_score = self._calculate_complexity(test_case)
        if complexity_score > 10:
            base_priority *= self.weights.get("high_complexity", 1.2)

        # Invalid tests are more important (find bugs)
        if not test_case.should_pass:
            base_priority *= 1.3

        # Required field violations are critical
        if "required" in test_case.description.lower() and not test_case.should_pass:
            base_priority *= 1.4

        return round(base_priority, 2)

    def _calculate_complexity(self, test_case: TestCase) -> int:
        """Calculate complexity score based on request structure."""
        complexity = 0

        # Count path parameters
        complexity += len(test_case.path_params)

        # Count query parameters
        complexity += len(test_case.query_params)

        # Count request body fields
        if test_case.request_body:
            complexity += self._count_fields(test_case.request_body)

        return complexity

    def _count_fields(self, data: dict) -> int:
        """Recursively count fields in a dictionary."""
        count = 0
        for key, value in data.items():
            count += 1
            if isinstance(value, dict):
                count += self._count_fields(value)
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                count += self._count_fields(value[0])
        return count

    def select_top_tests(
        self, test_suite: TestSuite, max_tests: int
    ) -> List[TestCase]:
        """
        Select top N tests based on priority.

        Args:
            test_suite: Test suite
            max_tests: Maximum number of tests to select

        Returns:
            List of selected test cases
        """
        return test_suite.test_cases[:max_tests]

    def get_priority_distribution(self, test_suite: TestSuite) -> Dict[str, int]:
        """Get distribution of tests by priority level."""
        distribution = {
            "critical": 0,  # priority >= 1.5
            "high": 0,      # 1.2 <= priority < 1.5
            "medium": 0,    # 0.8 <= priority < 1.2
            "low": 0,       # priority < 0.8
        }

        for test_case in test_suite.test_cases:
            if test_case.priority >= 1.5:
                distribution["critical"] += 1
            elif test_case.priority >= 1.2:
                distribution["high"] += 1
            elif test_case.priority >= 0.8:
                distribution["medium"] += 1
            else:
                distribution["low"] += 1

        return distribution

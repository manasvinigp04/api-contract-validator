"""
Validation Drift Detector

Detects when the API incorrectly accepts invalid inputs that should have been rejected.
"""

from typing import List

from api_contract_validator.analysis.drift.models import (
    DriftSeverity,
    ValidationDriftIssue,
)
from api_contract_validator.config.logging import get_logger
from api_contract_validator.execution.collector.result_collector import ExecutionSummary
from api_contract_validator.generation.base import TestCaseType

logger = get_logger("api_contract_validator.analyzer")


class ValidationDriftDetector:
    """
    Detects validation drift by identifying invalid/boundary tests that
    unexpectedly passed when they should have failed.
    """

    def detect(self, execution_summary: ExecutionSummary) -> List[ValidationDriftIssue]:
        """
        Detect validation drift from test execution results.

        Validation drift occurs when:
        - Invalid tests pass (should return 4xx)
        - Boundary tests fail unexpectedly
        - API accepts malformed input

        Args:
            execution_summary: Test execution results

        Returns:
            List of validation drift issues
        """
        logger.info("Starting validation drift detection")
        drift_issues: List[ValidationDriftIssue] = []

        # Analyze invalid and boundary test results
        for result in execution_summary.results:
            test_case = result.test_case

            # Check if invalid tests incorrectly passed
            if test_case.test_type == TestCaseType.INVALID:
                if result.passed:
                    # Invalid test passed when it should have failed
                    issue = ValidationDriftIssue(
                        endpoint_id=test_case.endpoint.endpoint_id,
                        test_id=test_case.test_id,
                        test_type="INVALID",
                        violated_constraint=test_case.description,
                        input_data=test_case.request_body or {},
                        actual_status_code=result.status_code,
                        expected_status_code_range="400-499",
                        message=(
                            f"API accepted invalid input that should have been rejected. "
                            f"Expected 4xx status, got {result.status_code}"
                        ),
                        severity=DriftSeverity.HIGH,
                    )
                    drift_issues.append(issue)

            # Check if boundary tests have unexpected results
            elif test_case.test_type == TestCaseType.BOUNDARY:
                # Boundary tests should pass (they're valid edge cases)
                if not result.passed and 200 <= result.status_code < 300:
                    # Got 2xx but test marked as failed (likely schema validation issue)
                    issue = ValidationDriftIssue(
                        endpoint_id=test_case.endpoint.endpoint_id,
                        test_id=test_case.test_id,
                        test_type="BOUNDARY",
                        violated_constraint=test_case.description,
                        input_data=test_case.request_body or {},
                        actual_status_code=result.status_code,
                        expected_status_code_range="200-299",
                        message=(
                            f"Boundary test received {result.status_code} but failed validation. "
                            f"Response may not match expected schema."
                        ),
                        severity=DriftSeverity.MEDIUM,
                    )
                    drift_issues.append(issue)

        logger.info(f"Validation drift detection complete: {len(drift_issues)} issues found")
        return drift_issues

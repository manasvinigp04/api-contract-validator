"""
Contract Drift Detector

Detects mismatches between expected API contracts and actual responses.
"""

from typing import List

from api_contract_validator.analysis.drift.models import ContractDriftIssue, DriftSeverity
from api_contract_validator.config.logging import get_logger
from api_contract_validator.execution.collector.result_collector import ExecutionSummary
from api_contract_validator.generation.base import TestCaseType
from api_contract_validator.schema.contract.contract_model import (
    APIContract,
    ViolationType,
)
from api_contract_validator.schema.contract.rules_engine import RulesEngine

logger = get_logger("api_contract_validator.analyzer")


class ContractDriftDetector:
    """
    Detects contract drift by comparing actual API responses against
    expected contract specifications.
    """

    def __init__(self, api_contract: APIContract):
        """
        Initialize contract drift detector.

        Args:
            api_contract: Complete API contract with rules
        """
        self.api_contract = api_contract
        self.rules_engine = RulesEngine()

    def detect(self, execution_summary: ExecutionSummary) -> List[ContractDriftIssue]:
        """
        Detect contract drift from test execution results.

        Contract drift occurs when:
        - Expected fields are missing from responses
        - Field types don't match specification
        - Schema constraints are violated
        - Response structure deviates from contract

        Args:
            execution_summary: Test execution results

        Returns:
            List of contract drift issues
        """
        logger.info("Starting contract drift detection")
        drift_issues: List[ContractDriftIssue] = []

        # Analyze VALID tests that passed - their responses should match contract
        valid_tests = [
            result
            for result in execution_summary.results
            if result.test_case.test_type == TestCaseType.VALID and result.passed
        ]

        logger.info(f"Analyzing {len(valid_tests)} valid test responses for contract drift")

        for test_result in valid_tests:
            endpoint_id = test_result.test_case.endpoint.endpoint_id
            status_code = test_result.status_code
            response_body = test_result.response_body or {}

            # Get contract for this endpoint
            contract = self.api_contract.get_contract(endpoint_id)
            if not contract:
                logger.warning(f"No contract found for endpoint: {endpoint_id}")
                continue

            # Get response rules for the status code
            response_rules = contract.response_rules.get(status_code, [])
            if not response_rules:
                # Try default 2xx rules if no specific status code rule
                response_rules = contract.response_rules.get(200, [])

            if not response_rules:
                logger.debug(f"No response rules for {endpoint_id} status {status_code}")
                continue

            # Validate response against contract rules
            violations = self.rules_engine.validate_against_rules(
                data=response_body,
                rules=response_rules,
                endpoint_id=endpoint_id,
                location="response_body",
            )

            # Convert violations to contract drift issues
            for violation in violations:
                severity = self._determine_severity(violation.violation_type)
                issue = ContractDriftIssue(
                    endpoint_id=endpoint_id,
                    test_id=test_result.test_case.test_id,
                    location=violation.location,
                    field_path=violation.field_path,
                    violation_type=violation.violation_type.value,
                    expected=violation.expected,
                    actual=violation.actual,
                    message=violation.message,
                    severity=severity,
                    status_code=status_code,
                )
                drift_issues.append(issue)

        logger.info(f"Contract drift detection complete: {len(drift_issues)} issues found")
        return drift_issues

    def _determine_severity(self, violation_type: ViolationType) -> DriftSeverity:
        """
        Determine severity level based on violation type.

        Args:
            violation_type: Type of contract violation

        Returns:
            DriftSeverity level
        """
        severity_map = {
            ViolationType.MISSING_FIELD: DriftSeverity.CRITICAL,
            ViolationType.TYPE_MISMATCH: DriftSeverity.HIGH,
            ViolationType.INVALID_ENUM: DriftSeverity.HIGH,
            ViolationType.CONSTRAINT_VIOLATION: DriftSeverity.MEDIUM,
            ViolationType.PATTERN_MISMATCH: DriftSeverity.MEDIUM,
            ViolationType.RANGE_VIOLATION: DriftSeverity.MEDIUM,
            ViolationType.UNEXPECTED_FIELD: DriftSeverity.LOW,
        }
        return severity_map.get(violation_type, DriftSeverity.MEDIUM)

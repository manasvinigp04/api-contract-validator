"""
Drift Detector

Main orchestrator for multi-dimensional drift detection.
"""

from api_contract_validator.analysis.drift.behavioral_drift import BehavioralDriftDetector
from api_contract_validator.analysis.drift.contract_drift import ContractDriftDetector
from api_contract_validator.analysis.drift.models import DriftReport
from api_contract_validator.analysis.drift.validation_drift import ValidationDriftDetector
from api_contract_validator.config.exceptions import DriftDetectionError
from api_contract_validator.config.logging import get_logger
from api_contract_validator.config.models import DriftDetectionConfig
from api_contract_validator.execution.collector.result_collector import ExecutionSummary
from api_contract_validator.schema.contract.contract_model import APIContract

logger = get_logger("api_contract_validator.analyzer")


class DriftDetector:
    """
    Coordinates multi-dimensional drift detection across contract,
    validation, and behavioral dimensions.
    """

    def __init__(self, api_contract: APIContract, config: DriftDetectionConfig):
        """
        Initialize drift detector.

        Args:
            api_contract: Complete API contract with rules
            config: Drift detection configuration
        """
        self.api_contract = api_contract
        self.config = config
        self.contract_detector = ContractDriftDetector(api_contract)
        self.validation_detector = ValidationDriftDetector()
        self.behavioral_detector = BehavioralDriftDetector()

    def detect_drift(self, execution_summary: ExecutionSummary) -> DriftReport:
        """
        Detect drift across all dimensions from test execution results.

        Args:
            execution_summary: Test execution results and statistics

        Returns:
            DriftReport with all detected drift

        Raises:
            DriftDetectionError: If drift detection fails
        """
        logger.info("Starting multi-dimensional drift detection")

        try:
            # Initialize drift report
            drift_report = DriftReport(
                api_url="",  # Will be set by caller
                spec_source=self.api_contract.spec.source_path,
                spec_version=self.api_contract.spec.metadata.version,
                total_tests_executed=execution_summary.total,
                tests_passed=execution_summary.passed,
                tests_failed=execution_summary.failed,
            )

            # Detect contract drift (if enabled)
            if self.config.detect_contract_drift:
                logger.info("Detecting contract drift...")
                contract_issues = self.contract_detector.detect(execution_summary)
                drift_report.contract_drift = contract_issues
                logger.info(f"Found {len(contract_issues)} contract drift issues")

            # Detect validation drift (if enabled)
            if self.config.detect_validation_drift:
                logger.info("Detecting validation drift...")
                validation_issues = self.validation_detector.detect(execution_summary)
                drift_report.validation_drift = validation_issues
                logger.info(f"Found {len(validation_issues)} validation drift issues")

            # Detect behavioral drift (if enabled)
            if self.config.detect_behavioral_drift:
                logger.info("Detecting behavioral drift...")
                behavioral_issues = self.behavioral_detector.detect(execution_summary)
                drift_report.behavioral_drift = behavioral_issues
                logger.info(f"Found {len(behavioral_issues)} behavioral drift issues")

            # Calculate summary statistics
            drift_report.calculate_summary()

            logger.info(
                f"Drift detection complete: {drift_report.summary.total_issues} total issues, "
                f"{len(drift_report.summary.affected_endpoints)} affected endpoints"
            )

            return drift_report

        except Exception as e:
            error_msg = f"Drift detection failed: {str(e)}"
            logger.error(error_msg)
            raise DriftDetectionError(error_msg) from e

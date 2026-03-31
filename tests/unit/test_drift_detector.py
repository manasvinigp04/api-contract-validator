"""
Unit tests for drift detector orchestrator.
"""

import pytest
from unittest.mock import Mock, MagicMock

from api_contract_validator.analysis.drift.detector import DriftDetector
from api_contract_validator.analysis.drift.models import (
    DriftReport,
    ContractDriftIssue,
    ValidationDriftIssue,
    BehavioralDriftIssue,
    DriftSeverity,
)
from api_contract_validator.config.models import DriftDetectionConfig
from api_contract_validator.execution.collector.result_collector import ExecutionSummary


class TestDriftDetector:
    """Test DriftDetector orchestrator."""

    @pytest.fixture
    def mock_contract(self):
        """Create mock API contract."""
        contract = Mock()
        contract.spec.source_path = "/path/to/spec.yaml"
        contract.spec.metadata.version = "1.0.0"
        return contract

    @pytest.fixture
    def drift_config(self):
        """Create drift detection config."""
        return DriftDetectionConfig(
            detect_contract_drift=True,
            detect_validation_drift=True,
            detect_behavioral_drift=True,
        )

    @pytest.fixture
    def execution_summary(self):
        """Create mock execution summary."""
        summary = Mock(spec=ExecutionSummary)
        summary.total = 100
        summary.passed = 85
        summary.failed = 15
        return summary

    def test_detector_initialization(self, mock_contract, drift_config):
        """Test detector initializes correctly."""
        detector = DriftDetector(mock_contract, drift_config)

        assert detector.api_contract == mock_contract
        assert detector.config == drift_config
        assert detector.contract_detector is not None
        assert detector.validation_detector is not None
        assert detector.behavioral_detector is not None

    def test_detect_drift_all_types(self, mock_contract, drift_config, execution_summary, monkeypatch):
        """Test drift detection across all dimensions."""
        detector = DriftDetector(mock_contract, drift_config)

        # Mock the individual detectors
        contract_issue = ContractDriftIssue(
            endpoint_id="GET /users",
            test_id="test_001",
            location="response_body",
            field_path="data.email",
            violation_type="MISSING_REQUIRED_FIELD",
            expected="string",
            actual=None,
            message="Required field missing",
            status_code=200,
        )

        validation_issue = ValidationDriftIssue(
            endpoint_id="POST /users",
            test_id="test_002",
            test_type="INVALID",
            violated_constraint="email format",
            input_data={"email": "invalid"},
            actual_status_code=200,
            expected_status_code_range="400-499",
            message="Invalid input accepted",
        )

        behavioral_issue = BehavioralDriftIssue(
            endpoint_id="GET /users/{id}",
            test_ids=["test_003"],
            anomaly_type="inconsistent_response",
            description="Inconsistent behavior",
            evidence={},
        )

        detector.contract_detector.detect = Mock(return_value=[contract_issue])
        detector.validation_detector.detect = Mock(return_value=[validation_issue])
        detector.behavioral_detector.detect = Mock(return_value=[behavioral_issue])

        # Execute
        report = detector.detect_drift(execution_summary)

        # Verify
        assert isinstance(report, DriftReport)
        assert len(report.contract_drift) == 1
        assert len(report.validation_drift) == 1
        assert len(report.behavioral_drift) == 1
        assert report.total_tests_executed == 100
        assert report.tests_passed == 85
        assert report.tests_failed == 15
        assert report.summary.total_issues == 3

    def test_detect_drift_contract_only(self, mock_contract, execution_summary):
        """Test detection with only contract drift enabled."""
        config = DriftDetectionConfig(
            detect_contract_drift=True,
            detect_validation_drift=False,
            detect_behavioral_drift=False,
        )
        detector = DriftDetector(mock_contract, config)

        contract_issue = ContractDriftIssue(
            endpoint_id="GET /users",
            test_id="test_001",
            location="response_body",
            field_path="data",
            violation_type="MISSING_REQUIRED_FIELD",
            expected="object",
            actual=None,
            message="Missing field",
            status_code=200,
        )

        detector.contract_detector.detect = Mock(return_value=[contract_issue])

        report = detector.detect_drift(execution_summary)

        assert len(report.contract_drift) == 1
        assert len(report.validation_drift) == 0
        assert len(report.behavioral_drift) == 0
        detector.contract_detector.detect.assert_called_once()

    def test_detect_drift_no_issues(self, mock_contract, drift_config, execution_summary):
        """Test detection when no drift issues are found."""
        detector = DriftDetector(mock_contract, drift_config)

        # Mock detectors to return empty lists
        detector.contract_detector.detect = Mock(return_value=[])
        detector.validation_detector.detect = Mock(return_value=[])
        detector.behavioral_detector.detect = Mock(return_value=[])

        report = detector.detect_drift(execution_summary)

        assert len(report.contract_drift) == 0
        assert len(report.validation_drift) == 0
        assert len(report.behavioral_drift) == 0
        assert report.summary.total_issues == 0
        assert not report.has_issues()

    def test_detect_drift_summary_calculation(self, mock_contract, drift_config, execution_summary):
        """Test that summary is calculated correctly."""
        detector = DriftDetector(mock_contract, drift_config)

        # Create issues with different severities
        contract_issues = [
            ContractDriftIssue(
                endpoint_id="GET /users",
                test_id=f"test_{i}",
                location="response_body",
                field_path=f"data.field{i}",
                violation_type="MISSING_REQUIRED_FIELD",
                expected="string",
                actual=None,
                message="Missing field",
                status_code=200,
                severity=DriftSeverity.CRITICAL if i == 0 else DriftSeverity.HIGH,
            )
            for i in range(3)
        ]

        detector.contract_detector.detect = Mock(return_value=contract_issues)
        detector.validation_detector.detect = Mock(return_value=[])
        detector.behavioral_detector.detect = Mock(return_value=[])

        report = detector.detect_drift(execution_summary)

        assert report.summary.total_issues == 3
        assert report.summary.critical_count == 1
        assert report.summary.high_count == 2
        assert report.summary.by_type["contract"] == 3
        assert len(report.summary.affected_endpoints) == 1
        assert "GET /users" in report.summary.affected_endpoints

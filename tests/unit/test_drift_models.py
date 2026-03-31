"""
Unit tests for drift detection models.
"""

import pytest
from datetime import datetime

from api_contract_validator.analysis.drift.models import (
    ContractDriftIssue,
    ValidationDriftIssue,
    BehavioralDriftIssue,
    DriftReport,
    DriftSeverity,
    DriftSummary,
)


class TestDriftSeverity:
    """Test DriftSeverity enum."""

    def test_severity_values(self):
        """Test that severity levels have correct values."""
        assert DriftSeverity.CRITICAL.value == "critical"
        assert DriftSeverity.HIGH.value == "high"
        assert DriftSeverity.MEDIUM.value == "medium"
        assert DriftSeverity.LOW.value == "low"
        assert DriftSeverity.INFO.value == "info"


class TestContractDriftIssue:
    """Test ContractDriftIssue model."""

    def test_create_contract_drift_issue(self):
        """Test creating a contract drift issue."""
        issue = ContractDriftIssue(
            endpoint_id="GET /users",
            test_id="test_001",
            location="response_body",
            field_path="data.email",
            violation_type="MISSING_REQUIRED_FIELD",
            expected="string",
            actual=None,
            message="Required field 'email' is missing",
            status_code=200,
        )

        assert issue.endpoint_id == "GET /users"
        assert issue.test_id == "test_001"
        assert issue.severity == DriftSeverity.HIGH
        assert issue.status_code == 200

    def test_custom_severity(self):
        """Test setting custom severity."""
        issue = ContractDriftIssue(
            endpoint_id="GET /users",
            test_id="test_001",
            location="response_body",
            field_path="data.age",
            violation_type="TYPE_MISMATCH",
            expected="integer",
            actual="string",
            message="Field type mismatch",
            status_code=200,
            severity=DriftSeverity.CRITICAL,
        )

        assert issue.severity == DriftSeverity.CRITICAL


class TestValidationDriftIssue:
    """Test ValidationDriftIssue model."""

    def test_create_validation_drift_issue(self):
        """Test creating a validation drift issue."""
        issue = ValidationDriftIssue(
            endpoint_id="POST /users",
            test_id="test_invalid_001",
            test_type="INVALID",
            violated_constraint="email format",
            input_data={"email": "not-an-email", "name": "John"},
            actual_status_code=200,
            expected_status_code_range="400-499",
            message="API accepted invalid email format",
        )

        assert issue.endpoint_id == "POST /users"
        assert issue.test_type == "INVALID"
        assert issue.actual_status_code == 200
        assert issue.severity == DriftSeverity.HIGH


class TestBehavioralDriftIssue:
    """Test BehavioralDriftIssue model."""

    def test_create_behavioral_drift_issue(self):
        """Test creating a behavioral drift issue."""
        issue = BehavioralDriftIssue(
            endpoint_id="GET /users/{id}",
            test_ids=["test_001", "test_002", "test_003"],
            anomaly_type="inconsistent_response",
            description="Same request returns different field counts",
            evidence={
                "test_001": {"field_count": 5},
                "test_002": {"field_count": 7},
                "test_003": {"field_count": 5},
            },
        )

        assert issue.endpoint_id == "GET /users/{id}"
        assert len(issue.test_ids) == 3
        assert issue.severity == DriftSeverity.MEDIUM
        assert "field_count" in issue.evidence["test_001"]


class TestDriftReport:
    """Test DriftReport model."""

    def test_create_empty_drift_report(self):
        """Test creating an empty drift report."""
        report = DriftReport(
            api_url="https://api.example.com",
            spec_source="/path/to/spec.yaml",
            spec_version="1.0.0",
        )

        assert report.api_url == "https://api.example.com"
        assert report.spec_source == "/path/to/spec.yaml"
        assert report.spec_version == "1.0.0"
        assert len(report.contract_drift) == 0
        assert len(report.validation_drift) == 0
        assert len(report.behavioral_drift) == 0
        assert not report.has_issues()

    def test_drift_report_with_issues(self):
        """Test drift report with various issues."""
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
            severity=DriftSeverity.CRITICAL,
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
            severity=DriftSeverity.HIGH,
        )

        behavioral_issue = BehavioralDriftIssue(
            endpoint_id="GET /users/{id}",
            test_ids=["test_003"],
            anomaly_type="unexpected_null",
            description="Unexpected null values",
            evidence={"null_fields": ["age", "phone"]},
            severity=DriftSeverity.MEDIUM,
        )

        report = DriftReport(
            api_url="https://api.example.com",
            spec_source="/path/to/spec.yaml",
            contract_drift=[contract_issue],
            validation_drift=[validation_issue],
            behavioral_drift=[behavioral_issue],
        )

        report.calculate_summary()

        assert report.has_issues()
        assert report.has_critical_issues()
        assert report.summary.total_issues == 3
        assert report.summary.critical_count == 1
        assert report.summary.high_count == 1
        assert report.summary.medium_count == 1
        assert report.summary.by_type["contract"] == 1
        assert report.summary.by_type["validation"] == 1
        assert report.summary.by_type["behavioral"] == 1

    def test_get_issues_by_endpoint(self):
        """Test retrieving issues for a specific endpoint."""
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
            endpoint_id="GET /users",
            test_id="test_002",
            test_type="INVALID",
            violated_constraint="limit parameter",
            input_data={"limit": -1},
            actual_status_code=200,
            expected_status_code_range="400-499",
            message="Invalid parameter accepted",
        )

        other_issue = ContractDriftIssue(
            endpoint_id="POST /users",
            test_id="test_003",
            location="response_body",
            field_path="data.id",
            violation_type="TYPE_MISMATCH",
            expected="integer",
            actual="string",
            message="Type mismatch",
            status_code=201,
        )

        report = DriftReport(
            api_url="https://api.example.com",
            spec_source="/path/to/spec.yaml",
            contract_drift=[contract_issue, other_issue],
            validation_drift=[validation_issue],
        )

        issues = report.get_issues_by_endpoint("GET /users")

        assert len(issues["contract"]) == 1
        assert len(issues["validation"]) == 1
        assert len(issues["behavioral"]) == 0

    def test_get_all_affected_endpoints(self):
        """Test getting all affected endpoints."""
        report = DriftReport(
            api_url="https://api.example.com",
            spec_source="/path/to/spec.yaml",
            contract_drift=[
                ContractDriftIssue(
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
            ],
            validation_drift=[
                ValidationDriftIssue(
                    endpoint_id="POST /users",
                    test_id="test_002",
                    test_type="INVALID",
                    violated_constraint="required field",
                    input_data={},
                    actual_status_code=200,
                    expected_status_code_range="400-499",
                    message="Invalid input accepted",
                )
            ],
            behavioral_drift=[
                BehavioralDriftIssue(
                    endpoint_id="GET /users/{id}",
                    test_ids=["test_003"],
                    anomaly_type="inconsistent_response",
                    description="Inconsistent behavior",
                    evidence={},
                )
            ],
        )

        endpoints = report.get_all_affected_endpoints()

        assert len(endpoints) == 3
        assert "GET /users" in endpoints
        assert "POST /users" in endpoints
        assert "GET /users/{id}" in endpoints

    def test_calculate_summary(self):
        """Test summary calculation."""
        report = DriftReport(
            api_url="https://api.example.com",
            spec_source="/path/to/spec.yaml",
            total_tests_executed=100,
            tests_passed=80,
            tests_failed=20,
            contract_drift=[
                ContractDriftIssue(
                    endpoint_id="GET /users",
                    test_id="test_001",
                    location="response_body",
                    field_path="data",
                    violation_type="MISSING_REQUIRED_FIELD",
                    expected="object",
                    actual=None,
                    message="Missing field",
                    status_code=200,
                    severity=DriftSeverity.CRITICAL,
                ),
                ContractDriftIssue(
                    endpoint_id="GET /posts",
                    test_id="test_002",
                    location="response_body",
                    field_path="title",
                    violation_type="TYPE_MISMATCH",
                    expected="string",
                    actual="integer",
                    message="Type mismatch",
                    status_code=200,
                    severity=DriftSeverity.HIGH,
                ),
            ],
            validation_drift=[
                ValidationDriftIssue(
                    endpoint_id="POST /users",
                    test_id="test_003",
                    test_type="INVALID",
                    violated_constraint="email format",
                    input_data={"email": "invalid"},
                    actual_status_code=200,
                    expected_status_code_range="400-499",
                    message="Invalid input accepted",
                    severity=DriftSeverity.MEDIUM,
                )
            ],
        )

        report.calculate_summary()

        assert report.summary.total_issues == 3
        assert report.summary.critical_count == 1
        assert report.summary.high_count == 1
        assert report.summary.medium_count == 1
        assert report.summary.low_count == 0
        assert len(report.summary.affected_endpoints) == 3
        assert report.summary.by_type["contract"] == 2
        assert report.summary.by_type["validation"] == 1
        assert report.summary.by_type["behavioral"] == 0

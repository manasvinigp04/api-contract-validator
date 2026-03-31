"""
Drift Detection Models

Data models for representing detected drift across multiple dimensions.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field


class DriftSeverity(str, Enum):
    """Severity levels for drift issues."""

    CRITICAL = "critical"  # Breaking changes, major contract violations
    HIGH = "high"  # Significant issues that should be addressed
    MEDIUM = "medium"  # Notable drift but not immediately breaking
    LOW = "low"  # Minor inconsistencies
    INFO = "info"  # Informational observations


class ContractDriftIssue(BaseModel):
    """
    Represents a contract drift issue where actual API behavior
    deviates from the expected contract specification.
    """

    endpoint_id: str
    test_id: str
    location: str  # "response_body", "response_headers"
    field_path: str
    violation_type: str  # From ViolationType enum
    expected: Any
    actual: Any
    message: str
    severity: DriftSeverity = DriftSeverity.HIGH
    status_code: int

    class Config:
        frozen = False


class ValidationDriftIssue(BaseModel):
    """
    Represents validation drift where the API incorrectly accepts
    invalid inputs that should have been rejected.
    """

    endpoint_id: str
    test_id: str
    test_type: str  # "INVALID" or "BOUNDARY"
    violated_constraint: str  # Description of what constraint was violated
    input_data: Dict[str, Any]
    actual_status_code: int
    expected_status_code_range: str  # e.g., "400-499"
    message: str
    severity: DriftSeverity = DriftSeverity.HIGH

    class Config:
        frozen = False


class BehavioralDriftIssue(BaseModel):
    """
    Represents behavioral drift where API exhibits inconsistent
    or unexpected behavior patterns.
    """

    endpoint_id: str
    test_ids: List[str]  # Multiple related tests
    anomaly_type: str  # "inconsistent_response", "unexpected_null", "extra_fields", etc.
    description: str
    evidence: Dict[str, Any]  # Supporting data showing the anomaly
    severity: DriftSeverity = DriftSeverity.MEDIUM

    class Config:
        frozen = False


class DriftSummary(BaseModel):
    """Summary statistics for detected drift."""

    total_issues: int = 0
    by_severity: Dict[str, int] = Field(default_factory=dict)
    by_type: Dict[str, int] = Field(default_factory=dict)  # contract, validation, behavioral
    affected_endpoints: List[str] = Field(default_factory=list)
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0

    class Config:
        frozen = False


class DriftReport(BaseModel):
    """
    Comprehensive drift detection report containing all detected
    drift across multiple dimensions.
    """

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    api_url: str
    spec_source: str  # Path to OpenAPI spec or PRD
    spec_version: Optional[str] = None

    # Drift issues by type
    contract_drift: List[ContractDriftIssue] = Field(default_factory=list)
    validation_drift: List[ValidationDriftIssue] = Field(default_factory=list)
    behavioral_drift: List[BehavioralDriftIssue] = Field(default_factory=list)

    # Summary statistics
    summary: DriftSummary = Field(default_factory=DriftSummary)

    # Test execution context
    total_tests_executed: int = 0
    tests_passed: int = 0
    tests_failed: int = 0

    class Config:
        frozen = False

    def has_critical_issues(self) -> bool:
        """Check if there are any critical issues."""
        return self.summary.critical_count > 0

    def has_issues(self) -> bool:
        """Check if any drift was detected."""
        return self.summary.total_issues > 0

    def get_issues_by_endpoint(self, endpoint_id: str) -> Dict[str, List[Any]]:
        """Get all drift issues for a specific endpoint."""
        return {
            "contract": [d for d in self.contract_drift if d.endpoint_id == endpoint_id],
            "validation": [d for d in self.validation_drift if d.endpoint_id == endpoint_id],
            "behavioral": [d for d in self.behavioral_drift if d.endpoint_id == endpoint_id],
        }

    def get_all_affected_endpoints(self) -> Set[str]:
        """Get set of all endpoints with drift issues."""
        endpoints = set()
        endpoints.update(d.endpoint_id for d in self.contract_drift)
        endpoints.update(d.endpoint_id for d in self.validation_drift)
        endpoints.update(d.endpoint_id for d in self.behavioral_drift)
        return endpoints

    def calculate_summary(self) -> None:
        """Calculate and update summary statistics."""
        all_issues: List[Any] = []
        all_issues.extend(self.contract_drift)
        all_issues.extend(self.validation_drift)
        all_issues.extend(self.behavioral_drift)

        self.summary.total_issues = len(all_issues)
        self.summary.affected_endpoints = sorted(list(self.get_all_affected_endpoints()))

        # Count by severity
        severity_counts: Dict[str, int] = {}
        for issue in all_issues:
            sev = issue.severity.value if hasattr(issue.severity, 'value') else issue.severity
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        self.summary.by_severity = severity_counts
        self.summary.critical_count = severity_counts.get("critical", 0)
        self.summary.high_count = severity_counts.get("high", 0)
        self.summary.medium_count = severity_counts.get("medium", 0)
        self.summary.low_count = severity_counts.get("low", 0)

        # Count by type
        self.summary.by_type = {
            "contract": len(self.contract_drift),
            "validation": len(self.validation_drift),
            "behavioral": len(self.behavioral_drift),
        }


# Progressive drift models (for optional Phase 6 enhancement)

class DriftSnapshot(BaseModel):
    """Snapshot of drift state at a point in time."""

    timestamp: datetime
    drift_report: DriftReport
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None

    class Config:
        frozen = False


class ProgressiveDriftTrend(BaseModel):
    """Trend analysis across multiple drift snapshots."""

    metric_name: str  # e.g., "total_issues", "critical_count"
    values: List[float] = Field(default_factory=list)
    timestamps: List[datetime] = Field(default_factory=list)
    trend_direction: str = "stable"  # "improving", "degrading", "stable"
    change_percentage: float = 0.0

    class Config:
        frozen = False

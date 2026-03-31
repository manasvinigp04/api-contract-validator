"""
Reporting Models

Data models for structured report generation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReportSummary(BaseModel):
    """Executive summary section of report."""

    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    pass_rate: float = 0.0

    total_drift_issues: int = 0
    critical_issues: int = 0
    high_severity_issues: int = 0
    medium_severity_issues: int = 0
    low_severity_issues: int = 0

    affected_endpoints_count: int = 0
    contract_drift_count: int = 0
    validation_drift_count: int = 0
    behavioral_drift_count: int = 0

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    api_url: str = ""
    spec_source: str = ""

    class Config:
        frozen = False


class EndpointDriftSummary(BaseModel):
    """Drift summary for a single endpoint."""

    endpoint_id: str
    total_issues: int = 0
    contract_issues: int = 0
    validation_issues: int = 0
    behavioral_issues: int = 0
    highest_severity: str = "low"
    issues: List[Dict[str, Any]] = Field(default_factory=list)

    class Config:
        frozen = False


class EndpointReport(BaseModel):
    """Detailed report for a single endpoint."""

    endpoint_id: str
    method: str
    path: str
    drift_summary: EndpointDriftSummary
    root_cause: Optional[str] = None
    remediations: List[str] = Field(default_factory=list)

    class Config:
        frozen = False


class DriftBreakdown(BaseModel):
    """Categorized breakdown of drift issues."""

    contract_drift: List[Dict[str, Any]] = Field(default_factory=list)
    validation_drift: List[Dict[str, Any]] = Field(default_factory=list)
    behavioral_drift: List[Dict[str, Any]] = Field(default_factory=list)

    class Config:
        frozen = False


class ReportMetadata(BaseModel):
    """Metadata about the report itself."""

    generated_at: datetime = Field(default_factory=datetime.utcnow)
    generator_version: str = "0.1.0"
    report_format: str = "unknown"
    config_summary: Optional[Dict[str, Any]] = None

    class Config:
        frozen = False

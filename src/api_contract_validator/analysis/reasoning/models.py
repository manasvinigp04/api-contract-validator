"""
AI Analysis Models

Data models for AI-assisted drift analysis results.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class AnalysisConfidence(str, Enum):
    """Confidence level for AI analysis."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RootCauseAnalysis(BaseModel):
    """
    AI-generated root cause hypothesis for drift issues.
    """

    issue_id: str  # References drift issue
    endpoint_id: str
    hypothesis: str  # Main explanation of why drift occurred
    contributing_factors: List[str] = Field(default_factory=list)
    confidence: AnalysisConfidence = AnalysisConfidence.MEDIUM
    evidence_references: List[str] = Field(default_factory=list)  # References to test IDs

    class Config:
        frozen = False


class RemediationSuggestion(BaseModel):
    """
    AI-generated suggestion for fixing drift issues.
    """

    issue_id: str  # References drift issue
    endpoint_id: str
    title: str  # Short description of the fix
    description: str  # Detailed explanation
    code_example: Optional[str] = None  # Example code fix
    implementation_steps: List[str] = Field(default_factory=list)
    estimated_effort: str = "unknown"  # "low", "medium", "high"
    priority: str = "medium"  # "critical", "high", "medium", "low"

    class Config:
        frozen = False


class IssueCorrelation(BaseModel):
    """
    Identifies relationships between multiple drift issues.
    """

    issue_ids: List[str] = Field(default_factory=list)
    endpoints: List[str] = Field(default_factory=list)
    correlation_type: str  # "shared_root_cause", "cascading_failure", "pattern"
    description: str
    impact_summary: str  # How these issues relate and compound

    class Config:
        frozen = False


class AnalysisResult(BaseModel):
    """
    Complete AI-assisted analysis of drift report.
    """

    root_causes: List[RootCauseAnalysis] = Field(default_factory=list)
    remediations: List[RemediationSuggestion] = Field(default_factory=list)
    correlations: List[IssueCorrelation] = Field(default_factory=list)

    # Overall insights
    executive_summary: Optional[str] = None
    systemic_issues: List[str] = Field(default_factory=list)  # Patterns across all drift
    quick_wins: List[str] = Field(default_factory=list)  # Easy fixes with high impact

    # Analysis metadata
    model_used: str = "unknown"
    analysis_timestamp: Optional[str] = None

    class Config:
        frozen = False

    def has_insights(self) -> bool:
        """Check if analysis contains any insights."""
        return bool(
            self.root_causes
            or self.remediations
            or self.correlations
            or self.systemic_issues
            or self.quick_wins
        )

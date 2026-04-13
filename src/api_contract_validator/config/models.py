"""
Configuration Models

Pydantic models for configuration management.
"""

from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ExecutionConfig(BaseModel):
    """Configuration for test execution."""

    parallel_workers: int = Field(default=10, ge=1, le=100)
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    retry_attempts: int = Field(default=3, ge=0, le=10)
    retry_delay_seconds: float = Field(default=1.0, ge=0.1, le=10.0)
    verify_ssl: bool = True
    follow_redirects: bool = True


class TestGenerationConfig(BaseModel):
    """Configuration for test case generation."""

    generate_valid: bool = True
    generate_invalid: bool = True
    generate_boundary: bool = True
    max_tests_per_endpoint: int = Field(default=50, ge=1)
    enable_prioritization: bool = True
    prioritization_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "critical_endpoints": 1.5,
            "recently_modified": 1.3,
            "high_complexity": 1.2,
            "user_reported_issues": 1.4,
        }
    )


class DriftDetectionConfig(BaseModel):
    """Configuration for drift detection."""

    detect_contract_drift: bool = True
    detect_validation_drift: bool = True
    detect_behavioral_drift: bool = True
    detect_progressive_drift: bool = False
    progressive_drift_history_size: int = Field(default=10, ge=2, le=100)


class AIAnalysisConfig(BaseModel):
    """Configuration for AI-assisted analysis."""

    enabled: bool = True
    provider: str = "anthropic"
    model: str = "claude-3-5-sonnet-20241022"
    api_key: Optional[str] = None
    max_tokens: int = Field(default=4000, ge=100, le=10000)
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    enable_root_cause_analysis: bool = True
    enable_remediation_suggestions: bool = True
    enable_correlation_analysis: bool = True


class ReportingConfig(BaseModel):
    """Configuration for report generation."""

    output_directory: Path = Field(default=Path("./output"))
    generate_markdown: bool = True
    generate_json: bool = True
    generate_cli_summary: bool = True
    generate_claude_integration: bool = True  # NEW: Generate Claude Code files
    markdown_template: Optional[Path] = None
    include_timestamp: bool = True
    include_config_summary: bool = True


class StorageConfig(BaseModel):
    """Configuration for optional drift snapshot storage."""

    enabled: bool = False
    storage_type: str = "tinydb"  # "tinydb" or "sqlite"
    database_path: Path = Field(default=Path("./snapshots/drift.db"))
    max_snapshots: int = Field(default=100, ge=10)
    retention_days: int = Field(default=30, ge=1)


class LoggingConfig(BaseModel):
    """Configuration for logging."""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[Path] = None
    console_output: bool = True

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Level must be one of {valid_levels}")
        return v_upper


class Config(BaseModel):
    """
    Main configuration model for the API Contract Validator.
    """

    # General settings
    project_name: str = "API Contract Validator"
    verbose: int = Field(default=0, ge=0, le=3)

    # Component configurations
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    test_generation: TestGenerationConfig = Field(default_factory=TestGenerationConfig)
    drift_detection: DriftDetectionConfig = Field(default_factory=DriftDetectionConfig)
    ai_analysis: AIAnalysisConfig = Field(default_factory=AIAnalysisConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # Environment-specific overrides
    environment: str = "development"  # "development", "ci", "production"

    class Config:
        frozen = False
        validate_assignment = True


class ValidationTarget(BaseModel):
    """
    Represents a target API for validation.
    """

    api_url: HttpUrl
    spec_path: Path
    headers: Dict[str, str] = Field(default_factory=dict)
    auth_token: Optional[str] = None

    @field_validator("spec_path")
    @classmethod
    def validate_spec_path(cls, v: Path) -> Path:
        if not v.exists():
            raise ValueError(f"Specification file not found: {v}")
        return v

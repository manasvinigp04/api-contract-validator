"""
JSON Report Generator

Generates structured JSON reports for CI/CD integration.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from api_contract_validator.analysis.drift.models import DriftReport
from api_contract_validator.analysis.reasoning.models import AnalysisResult
from api_contract_validator.config.logging import get_logger
from api_contract_validator.config.models import Config

logger = get_logger("api_contract_validator.reporter")


class JSONReportGenerator:
    """
    Generates structured JSON reports for CI/CD and automation.
    """

    def __init__(self, config: Config):
        """
        Initialize JSON report generator.

        Args:
            config: Application configuration
        """
        self.config = config

    def generate(
        self,
        drift_report: DriftReport,
        analysis_result: Optional[AnalysisResult] = None,
    ) -> str:
        """
        Generate JSON report.

        Args:
            drift_report: Drift detection results
            analysis_result: Optional AI analysis results

        Returns:
            JSON report content as string
        """
        logger.info("Generating JSON report")

        # Build report structure
        report = {
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "generator_version": "0.1.0",
                "format": "json",
                "spec_source": drift_report.spec_source,
                "spec_version": drift_report.spec_version,
                "api_url": drift_report.api_url,
            },
            "execution_summary": {
                "total_tests": drift_report.total_tests_executed,
                "passed": drift_report.tests_passed,
                "failed": drift_report.tests_failed,
                "pass_rate": round(
                    (drift_report.tests_passed / drift_report.total_tests_executed * 100)
                    if drift_report.total_tests_executed > 0
                    else 0.0,
                    2,
                ),
            },
            "drift_summary": {
                "total_issues": drift_report.summary.total_issues,
                "by_severity": drift_report.summary.by_severity,
                "by_type": drift_report.summary.by_type,
                "affected_endpoints": drift_report.summary.affected_endpoints,
                "has_critical": drift_report.has_critical_issues(),
            },
            "drift_details": {
                "contract_drift": [self._serialize_contract_issue(i) for i in drift_report.contract_drift],
                "validation_drift": [
                    self._serialize_validation_issue(i) for i in drift_report.validation_drift
                ],
                "behavioral_drift": [
                    self._serialize_behavioral_issue(i) for i in drift_report.behavioral_drift
                ],
            },
        }

        # Add AI analysis if available
        if analysis_result and analysis_result.has_insights():
            report["ai_analysis"] = {
                "model_used": analysis_result.model_used,
                "timestamp": analysis_result.analysis_timestamp,
                "executive_summary": analysis_result.executive_summary,
                "root_causes": [self._serialize_root_cause(rc) for rc in analysis_result.root_causes],
                "remediations": [self._serialize_remediation(r) for r in analysis_result.remediations],
                "correlations": [self._serialize_correlation(c) for c in analysis_result.correlations],
                "systemic_issues": analysis_result.systemic_issues,
                "quick_wins": analysis_result.quick_wins,
            }

        # Add configuration summary
        report["configuration"] = {
            "execution": {
                "parallel_workers": self.config.execution.parallel_workers,
                "timeout_seconds": self.config.execution.timeout_seconds,
            },
            "drift_detection": {
                "contract_drift": self.config.drift_detection.detect_contract_drift,
                "validation_drift": self.config.drift_detection.detect_validation_drift,
                "behavioral_drift": self.config.drift_detection.detect_behavioral_drift,
            },
            "ai_analysis": {
                "enabled": self.config.ai_analysis.enabled,
                "model": self.config.ai_analysis.model,
            },
        }

        json_content = json.dumps(report, indent=2, default=str)
        logger.info("JSON report generated successfully")
        return json_content

    def save(
        self,
        drift_report: DriftReport,
        analysis_result: Optional[AnalysisResult] = None,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """
        Generate and save JSON report to file.

        Args:
            drift_report: Drift detection results
            analysis_result: Optional AI analysis results
            output_dir: Output directory (uses config default if not provided)

        Returns:
            Path to saved report file
        """
        output_directory = output_dir or self.config.reporting.output_directory
        output_directory = Path(output_directory)
        output_directory.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"drift_report_{timestamp}.json"
        filepath = output_directory / filename

        # Generate and save report
        json_content = self.generate(drift_report, analysis_result)
        filepath.write_text(json_content, encoding="utf-8")

        logger.info(f"JSON report saved to: {filepath}")
        return filepath

    # Serialization helpers

    def _serialize_contract_issue(self, issue) -> Dict[str, Any]:
        """Serialize contract drift issue."""
        return {
            "endpoint_id": issue.endpoint_id,
            "test_id": issue.test_id,
            "location": issue.location,
            "field_path": issue.field_path,
            "violation_type": issue.violation_type,
            "expected": str(issue.expected)[:200],
            "actual": str(issue.actual)[:200],
            "message": issue.message,
            "severity": issue.severity.value,
            "status_code": issue.status_code,
        }

    def _serialize_validation_issue(self, issue) -> Dict[str, Any]:
        """Serialize validation drift issue."""
        return {
            "endpoint_id": issue.endpoint_id,
            "test_id": issue.test_id,
            "test_type": issue.test_type,
            "violated_constraint": issue.violated_constraint,
            "actual_status_code": issue.actual_status_code,
            "expected_status_code_range": issue.expected_status_code_range,
            "message": issue.message,
            "severity": issue.severity.value,
        }

    def _serialize_behavioral_issue(self, issue) -> Dict[str, Any]:
        """Serialize behavioral drift issue."""
        return {
            "endpoint_id": issue.endpoint_id,
            "test_ids": issue.test_ids,
            "anomaly_type": issue.anomaly_type,
            "description": issue.description,
            "evidence": issue.evidence,
            "severity": issue.severity.value,
        }

    def _serialize_root_cause(self, root_cause: RootCauseAnalysis) -> Dict[str, Any]:
        """Serialize root cause analysis."""
        return {
            "issue_id": root_cause.issue_id,
            "endpoint_id": root_cause.endpoint_id,
            "hypothesis": root_cause.hypothesis,
            "contributing_factors": root_cause.contributing_factors,
            "confidence": root_cause.confidence.value,
        }

    def _serialize_remediation(self, remediation: RemediationSuggestion) -> Dict[str, Any]:
        """Serialize remediation suggestion."""
        return {
            "issue_id": remediation.issue_id,
            "endpoint_id": remediation.endpoint_id,
            "title": remediation.title,
            "description": remediation.description,
            "code_example": remediation.code_example,
            "steps": remediation.implementation_steps,
            "effort": remediation.estimated_effort,
            "priority": remediation.priority,
        }

    def _serialize_correlation(self, correlation: IssueCorrelation) -> Dict[str, Any]:
        """Serialize issue correlation."""
        return {
            "issue_ids": correlation.issue_ids,
            "endpoints": correlation.endpoints,
            "type": correlation.correlation_type,
            "description": correlation.description,
            "impact": correlation.impact_summary,
        }

"""
Markdown Report Generator

Generates comprehensive Markdown reports for drift analysis.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from api_contract_validator.analysis.drift.models import DriftReport
from api_contract_validator.analysis.reasoning.models import AnalysisResult
from api_contract_validator.config.logging import get_logger
from api_contract_validator.config.models import Config
from api_contract_validator.reporting.models import (
    EndpointDriftSummary,
    EndpointReport,
    ReportSummary,
)

logger = get_logger("api_contract_validator.reporter")


class MarkdownReportGenerator:
    """
    Generates comprehensive Markdown reports using Jinja2 templates.
    """

    def __init__(self, config: Config):
        """
        Initialize Markdown report generator.

        Args:
            config: Application configuration
        """
        self.config = config

        # Setup Jinja2 environment
        template_dir = Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(
        self,
        drift_report: DriftReport,
        analysis_result: Optional[AnalysisResult] = None,
    ) -> str:
        """
        Generate Markdown report.

        Args:
            drift_report: Drift detection results
            analysis_result: Optional AI analysis results

        Returns:
            Markdown report content as string
        """
        logger.info("Generating Markdown report")

        # Build report context
        context = self._build_report_context(drift_report, analysis_result)

        # Load and render template
        template = self.env.get_template("report.md.jinja2")
        markdown_content = template.render(**context)

        logger.info("Markdown report generated successfully")
        return markdown_content

    def save(
        self,
        drift_report: DriftReport,
        analysis_result: Optional[AnalysisResult] = None,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """
        Generate and save Markdown report to file.

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
        filename = f"drift_report_{timestamp}.md"
        filepath = output_directory / filename

        # Generate and save report
        markdown_content = self.generate(drift_report, analysis_result)
        filepath.write_text(markdown_content, encoding="utf-8")

        logger.info(f"Markdown report saved to: {filepath}")
        return filepath

    def _build_report_context(
        self,
        drift_report: DriftReport,
        analysis_result: Optional[AnalysisResult],
    ) -> Dict[str, Any]:
        """Build template context from drift report and analysis."""
        # Build summary
        summary = ReportSummary(
            total_tests=drift_report.total_tests_executed,
            passed_tests=drift_report.tests_passed,
            failed_tests=drift_report.tests_failed,
            pass_rate=round(
                (drift_report.tests_passed / drift_report.total_tests_executed * 100)
                if drift_report.total_tests_executed > 0
                else 0.0,
                2,
            ),
            total_drift_issues=drift_report.summary.total_issues,
            critical_issues=drift_report.summary.critical_count,
            high_severity_issues=drift_report.summary.high_count,
            medium_severity_issues=drift_report.summary.medium_count,
            low_severity_issues=drift_report.summary.low_count,
            affected_endpoints_count=len(drift_report.summary.affected_endpoints),
            contract_drift_count=len(drift_report.contract_drift),
            validation_drift_count=len(drift_report.validation_drift),
            behavioral_drift_count=len(drift_report.behavioral_drift),
            timestamp=drift_report.timestamp,
            api_url=drift_report.api_url,
            spec_source=drift_report.spec_source,
        )

        # Build endpoint reports
        endpoint_reports = self._build_endpoint_reports(drift_report, analysis_result)

        # Prepare AI insights
        ai_insights = analysis_result is not None and analysis_result.has_insights()

        # Get top issues for recommendations
        top_critical = [i for i in drift_report.contract_drift if i.severity.value == "critical"][:5]
        top_high = [
            i
            for i in (drift_report.contract_drift + drift_report.validation_drift)
            if i.severity.value == "high"
        ][:5]

        context = {
            # Summary data
            "timestamp": drift_report.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "api_url": drift_report.api_url,
            "spec_source": drift_report.spec_source,
            "executive_summary": analysis_result.executive_summary
            if analysis_result
            else self._generate_default_summary(drift_report),
            # Test results
            "total_tests": drift_report.total_tests_executed,
            "passed_tests": drift_report.tests_passed,
            "failed_tests": drift_report.tests_failed,
            "pass_rate": summary.pass_rate,
            # Drift counts
            "total_drift_issues": drift_report.summary.total_issues,
            "critical_issues": drift_report.summary.critical_count,
            "high_severity_issues": drift_report.summary.high_count,
            "medium_severity_issues": drift_report.summary.medium_count,
            "low_severity_issues": drift_report.summary.low_count,
            "contract_drift_count": len(drift_report.contract_drift),
            "validation_drift_count": len(drift_report.validation_drift),
            "behavioral_drift_count": len(drift_report.behavioral_drift),
            "affected_endpoints_count": len(drift_report.summary.affected_endpoints),
            # Detailed drift lists
            "contract_drift": self._serialize_contract_drift(drift_report.contract_drift),
            "validation_drift": self._serialize_validation_drift(drift_report.validation_drift),
            "behavioral_drift": self._serialize_behavioral_drift(drift_report.behavioral_drift),
            # Endpoint reports
            "endpoint_reports": endpoint_reports,
            # AI insights
            "ai_insights": ai_insights,
            "systemic_issues": analysis_result.systemic_issues if analysis_result else [],
            "quick_wins": analysis_result.quick_wins if analysis_result else [],
            "correlations": analysis_result.correlations if analysis_result else [],
            # Top issues for recommendations
            "top_critical_issues": top_critical,
            "top_high_issues": top_high,
            # Config
            "config": self.config,
            "report_timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "generator_version": "0.1.0",
        }

        return context

    def _build_endpoint_reports(
        self, drift_report: DriftReport, analysis_result: Optional[AnalysisResult]
    ) -> List[EndpointReport]:
        """Build detailed reports for each affected endpoint."""
        endpoint_reports = []

        for endpoint_id in drift_report.summary.affected_endpoints:
            endpoint_issues = drift_report.get_issues_by_endpoint(endpoint_id)

            # Calculate endpoint-specific summary
            contract_count = len(endpoint_issues["contract"])
            validation_count = len(endpoint_issues["validation"])
            behavioral_count = len(endpoint_issues["behavioral"])
            total_count = contract_count + validation_count + behavioral_count

            # Determine highest severity
            all_issues = (
                endpoint_issues["contract"]
                + endpoint_issues["validation"]
                + endpoint_issues["behavioral"]
            )
            severities = [i.severity.value for i in all_issues]
            highest = "low"
            if "critical" in severities:
                highest = "critical"
            elif "high" in severities:
                highest = "high"
            elif "medium" in severities:
                highest = "medium"

            # Build endpoint summary
            drift_summary = EndpointDriftSummary(
                endpoint_id=endpoint_id,
                total_issues=total_count,
                contract_issues=contract_count,
                validation_issues=validation_count,
                behavioral_issues=behavioral_count,
                highest_severity=highest,
                issues=[self._issue_to_dict(i) for i in all_issues[:10]],
            )

            # Extract method and path
            method, path = endpoint_id.split(":", 1) if ":" in endpoint_id else ("GET", endpoint_id)

            # Find root cause from analysis
            root_cause = None
            remediations = []
            if analysis_result:
                for rc in analysis_result.root_causes:
                    if rc.endpoint_id == endpoint_id:
                        root_cause = rc.hypothesis
                        break

                remediations = [
                    r.title
                    for r in analysis_result.remediations
                    if r.endpoint_id == endpoint_id
                ][:3]

            endpoint_report = EndpointReport(
                endpoint_id=endpoint_id,
                method=method,
                path=path,
                drift_summary=drift_summary,
                root_cause=root_cause,
                remediations=remediations,
            )
            endpoint_reports.append(endpoint_report)

        return endpoint_reports

    def _generate_default_summary(self, drift_report: DriftReport) -> str:
        """Generate default executive summary when AI analysis is disabled."""
        if not drift_report.has_issues():
            return "API implementation conforms to contract specifications. No drift detected."

        critical = drift_report.summary.critical_count
        high = drift_report.summary.high_count
        endpoints = len(drift_report.summary.affected_endpoints)

        return (
            f"Detected {drift_report.summary.total_issues} drift issues across {endpoints} endpoints. "
            f"{critical} critical and {high} high-severity issues require immediate attention."
        )

    def _issue_to_dict(self, issue) -> Dict[str, Any]:
        """Convert drift issue to dictionary."""
        return {
            "severity": issue.severity.value if hasattr(issue.severity, "value") else issue.severity,
            "message": issue.message if hasattr(issue, "message") else issue.description,
            "field_path": issue.field_path if hasattr(issue, "field_path") else "N/A",
            "expected": str(issue.expected)[:100] if hasattr(issue, "expected") else "N/A",
            "actual": str(issue.actual)[:100] if hasattr(issue, "actual") else "N/A",
        }

    def _serialize_contract_drift(self, issues: List) -> List[Dict[str, Any]]:
        """Serialize contract drift issues for template."""
        return [
            {
                "endpoint_id": i.endpoint_id,
                "field_path": i.field_path,
                "violation_type": i.violation_type,
                "expected": str(i.expected)[:50],
                "actual": str(i.actual)[:50],
                "severity": i.severity.value,
            }
            for i in issues
        ]

    def _serialize_validation_drift(self, issues: List) -> List[Dict[str, Any]]:
        """Serialize validation drift issues for template."""
        return [
            {
                "endpoint_id": i.endpoint_id,
                "violated_constraint": i.violated_constraint,
                "expected_status_code_range": i.expected_status_code_range,
                "actual_status_code": i.actual_status_code,
                "severity": i.severity.value,
            }
            for i in issues
        ]

    def _serialize_behavioral_drift(self, issues: List) -> List[Dict[str, Any]]:
        """Serialize behavioral drift issues for template."""
        return [
            {
                "endpoint_id": i.endpoint_id,
                "anomaly_type": i.anomaly_type,
                "description": i.description[:200],
                "severity": i.severity.value,
            }
            for i in issues
        ]

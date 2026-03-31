"""
Report Generator

Main orchestrator for all report generation formats.
"""

from pathlib import Path
from typing import Dict, Optional

from rich.console import Console

from api_contract_validator.analysis.drift.models import DriftReport
from api_contract_validator.analysis.reasoning.models import AnalysisResult
from api_contract_validator.config.exceptions import ReportingError
from api_contract_validator.config.logging import get_logger
from api_contract_validator.config.models import Config
from api_contract_validator.reporting.cli.formatter import CLIFormatter
from api_contract_validator.reporting.json.generator import JSONReportGenerator
from api_contract_validator.reporting.markdown.generator import MarkdownReportGenerator

logger = get_logger("api_contract_validator.reporter")


class ReportGenerator:
    """
    Coordinates generation of reports in multiple formats.
    """

    def __init__(self, config: Config, console: Optional[Console] = None):
        """
        Initialize report generator.

        Args:
            config: Application configuration
            console: Optional Rich Console instance
        """
        self.config = config
        self.console = console or Console()

        # Initialize format-specific generators
        self.markdown_generator = MarkdownReportGenerator(config)
        self.json_generator = JSONReportGenerator(config)
        self.cli_formatter = CLIFormatter(self.console)

    def generate_reports(
        self,
        drift_report: DriftReport,
        analysis_result: Optional[AnalysisResult] = None,
        output_format: str = "all",
        output_dir: Optional[Path] = None,
    ) -> Dict[str, Path]:
        """
        Generate reports in specified formats.

        Args:
            drift_report: Drift detection results
            analysis_result: Optional AI analysis results
            output_format: Format to generate ("markdown", "json", "cli", "all")
            output_dir: Output directory (uses config default if not provided)

        Returns:
            Dictionary mapping format name to output file path

        Raises:
            ReportingError: If report generation fails
        """
        logger.info(f"Generating reports in format: {output_format}")

        report_paths: Dict[str, Path] = {}

        try:
            # Determine which formats to generate
            generate_markdown = output_format in ["markdown", "all"] and self.config.reporting.generate_markdown
            generate_json = output_format in ["json", "all"] and self.config.reporting.generate_json
            generate_cli = output_format in ["cli", "all"] and self.config.reporting.generate_cli_summary

            # Generate Markdown report
            if generate_markdown:
                logger.info("Generating Markdown report")
                md_path = self.markdown_generator.save(drift_report, analysis_result, output_dir)
                report_paths["markdown"] = md_path

            # Generate JSON report
            if generate_json:
                logger.info("Generating JSON report")
                json_path = self.json_generator.save(drift_report, analysis_result, output_dir)
                report_paths["json"] = json_path

            # Display CLI summary
            if generate_cli:
                logger.info("Displaying CLI summary")
                self.cli_formatter.format_and_display(drift_report, analysis_result)
                # CLI output doesn't have a file path
                report_paths["cli"] = Path("<console>")

            logger.info(f"Report generation complete: {len(report_paths)} formats generated")
            return report_paths

        except Exception as e:
            error_msg = f"Report generation failed: {str(e)}"
            logger.error(error_msg)
            raise ReportingError(error_msg) from e

    def generate_markdown(
        self,
        drift_report: DriftReport,
        analysis_result: Optional[AnalysisResult] = None,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """
        Generate only Markdown report.

        Args:
            drift_report: Drift detection results
            analysis_result: Optional AI analysis results
            output_dir: Output directory

        Returns:
            Path to generated Markdown file
        """
        return self.markdown_generator.save(drift_report, analysis_result, output_dir)

    def generate_json(
        self,
        drift_report: DriftReport,
        analysis_result: Optional[AnalysisResult] = None,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """
        Generate only JSON report.

        Args:
            drift_report: Drift detection results
            analysis_result: Optional AI analysis results
            output_dir: Output directory

        Returns:
            Path to generated JSON file
        """
        return self.json_generator.save(drift_report, analysis_result, output_dir)

    def display_cli_summary(
        self,
        drift_report: DriftReport,
        analysis_result: Optional[AnalysisResult] = None,
    ) -> None:
        """
        Display only CLI summary.

        Args:
            drift_report: Drift detection results
            analysis_result: Optional AI analysis results
        """
        self.cli_formatter.format_and_display(drift_report, analysis_result)

"""
Unit tests for report generator.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from api_contract_validator.reporting.generator import ReportGenerator
from api_contract_validator.analysis.drift.models import DriftReport, ContractDriftIssue, DriftSeverity
from api_contract_validator.analysis.reasoning.models import AnalysisResult
from api_contract_validator.config.models import Config, ReportingConfig


class TestReportGenerator:
    """Test ReportGenerator class."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        reporting_config = ReportingConfig(
            generate_markdown=True,
            generate_json=True,
            generate_cli_summary=True,
            output_directory=Path("/tmp/reports"),
        )
        config = Mock(spec=Config)
        config.reporting = reporting_config
        return config

    @pytest.fixture
    def drift_report(self):
        """Create sample drift report."""
        issue = ContractDriftIssue(
            endpoint_id="GET /users",
            test_id="test_001",
            location="response_body",
            field_path="data.email",
            violation_type="MISSING_REQUIRED_FIELD",
            expected="string",
            actual=None,
            message="Required field missing",
            status_code=200,
            severity=DriftSeverity.HIGH,
        )

        report = DriftReport(
            api_url="https://api.example.com",
            spec_source="/path/to/spec.yaml",
            contract_drift=[issue],
        )
        report.calculate_summary()
        return report

    @pytest.fixture
    def analysis_result(self):
        """Create sample analysis result."""
        return AnalysisResult(
            executive_summary="API has drift issues",
            model_used="claude-3-5-sonnet-20241022",
            analysis_timestamp="2024-01-01T00:00:00",
        )

    def test_generator_initialization(self, config):
        """Test generator initializes correctly."""
        generator = ReportGenerator(config)

        assert generator.config == config
        assert generator.console is not None
        assert generator.markdown_generator is not None
        assert generator.json_generator is not None
        assert generator.cli_formatter is not None

    @patch("api_contract_validator.reporting.generator.MarkdownReportGenerator")
    @patch("api_contract_validator.reporting.generator.JSONReportGenerator")
    @patch("api_contract_validator.reporting.generator.CLIFormatter")
    def test_generate_reports_all_formats(
        self,
        mock_cli_formatter,
        mock_json_gen,
        mock_md_gen,
        config,
        drift_report,
        analysis_result,
    ):
        """Test generating all report formats."""
        # Setup mocks
        mock_md_instance = MagicMock()
        mock_md_instance.save.return_value = Path("/tmp/report.md")
        mock_md_gen.return_value = mock_md_instance

        mock_json_instance = MagicMock()
        mock_json_instance.save.return_value = Path("/tmp/report.json")
        mock_json_gen.return_value = mock_json_instance

        mock_cli_instance = MagicMock()
        mock_cli_formatter.return_value = mock_cli_instance

        generator = ReportGenerator(config)
        report_paths = generator.generate_reports(
            drift_report, analysis_result, output_format="all"
        )

        # Verify all formats were generated
        assert "markdown" in report_paths
        assert "json" in report_paths
        assert "cli" in report_paths

        mock_md_instance.save.assert_called_once()
        mock_json_instance.save.assert_called_once()
        mock_cli_instance.format_and_display.assert_called_once()

    @patch("api_contract_validator.reporting.generator.MarkdownReportGenerator")
    def test_generate_markdown_only(self, mock_md_gen, config, drift_report):
        """Test generating only Markdown report."""
        mock_md_instance = MagicMock()
        mock_md_instance.save.return_value = Path("/tmp/report.md")
        mock_md_gen.return_value = mock_md_instance

        generator = ReportGenerator(config)
        path = generator.generate_markdown(drift_report)

        assert path == Path("/tmp/report.md")
        mock_md_instance.save.assert_called_once()

    @patch("api_contract_validator.reporting.generator.JSONReportGenerator")
    def test_generate_json_only(self, mock_json_gen, config, drift_report):
        """Test generating only JSON report."""
        mock_json_instance = MagicMock()
        mock_json_instance.save.return_value = Path("/tmp/report.json")
        mock_json_gen.return_value = mock_json_instance

        generator = ReportGenerator(config)
        path = generator.generate_json(drift_report)

        assert path == Path("/tmp/report.json")
        mock_json_instance.save.assert_called_once()

    @patch("api_contract_validator.reporting.generator.CLIFormatter")
    def test_display_cli_summary(self, mock_cli_formatter, config, drift_report):
        """Test displaying CLI summary."""
        mock_cli_instance = MagicMock()
        mock_cli_formatter.return_value = mock_cli_instance

        generator = ReportGenerator(config)
        generator.display_cli_summary(drift_report)

        mock_cli_instance.format_and_display.assert_called_once()

    @patch("api_contract_validator.reporting.generator.MarkdownReportGenerator")
    @patch("api_contract_validator.reporting.generator.JSONReportGenerator")
    def test_generate_reports_markdown_format(
        self,
        mock_json_gen,
        mock_md_gen,
        config,
        drift_report,
    ):
        """Test generating only markdown format when specified."""
        mock_md_instance = MagicMock()
        mock_md_instance.save.return_value = Path("/tmp/report.md")
        mock_md_gen.return_value = mock_md_instance

        mock_json_instance = MagicMock()
        mock_json_gen.return_value = mock_json_instance

        generator = ReportGenerator(config)
        report_paths = generator.generate_reports(drift_report, output_format="markdown")

        assert "markdown" in report_paths
        assert "json" not in report_paths
        mock_md_instance.save.assert_called_once()
        mock_json_instance.save.assert_not_called()

    def test_generate_reports_respects_config_flags(self):
        """Test that report generation respects config flags."""
        # Config with markdown disabled
        reporting_config = ReportingConfig(
            generate_markdown=False,
            generate_json=True,
            generate_cli_summary=True,
        )
        config = Mock(spec=Config)
        config.reporting = reporting_config

        with patch("api_contract_validator.reporting.generator.MarkdownReportGenerator") as mock_md_gen, \
             patch("api_contract_validator.reporting.generator.JSONReportGenerator") as mock_json_gen, \
             patch("api_contract_validator.reporting.generator.CLIFormatter") as mock_cli_formatter:

            mock_md_instance = MagicMock()
            mock_md_gen.return_value = mock_md_instance

            mock_json_instance = MagicMock()
            mock_json_instance.save.return_value = Path("/tmp/report.json")
            mock_json_gen.return_value = mock_json_instance

            mock_cli_instance = MagicMock()
            mock_cli_formatter.return_value = mock_cli_instance

            drift_report = DriftReport(
                api_url="https://api.example.com",
                spec_source="/path/to/spec.yaml",
            )

            generator = ReportGenerator(config)
            report_paths = generator.generate_reports(drift_report, output_format="all")

            # Markdown should not be generated
            assert "markdown" not in report_paths
            assert "json" in report_paths
            mock_md_instance.save.assert_not_called()
            mock_json_instance.save.assert_called_once()

    @patch("api_contract_validator.reporting.generator.MarkdownReportGenerator")
    def test_generate_reports_error_handling(self, mock_md_gen, config, drift_report):
        """Test error handling in report generation."""
        mock_md_instance = MagicMock()
        mock_md_instance.save.side_effect = Exception("Write failed")
        mock_md_gen.return_value = mock_md_instance

        generator = ReportGenerator(config)

        with pytest.raises(Exception) as exc_info:
            generator.generate_reports(drift_report, output_format="markdown")

        assert "Report generation failed" in str(exc_info.value) or "Write failed" in str(exc_info.value)

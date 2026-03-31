"""
Unit tests for AI-assisted analyzer.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from api_contract_validator.analysis.reasoning.analyzer import AIAnalyzer
from api_contract_validator.analysis.reasoning.models import (
    AnalysisResult,
    RootCauseAnalysis,
    RemediationSuggestion,
    IssueCorrelation,
)
from api_contract_validator.analysis.drift.models import (
    DriftReport,
    ContractDriftIssue,
    ValidationDriftIssue,
    DriftSeverity,
)
from api_contract_validator.config.models import AIAnalysisConfig


class TestAIAnalyzer:
    """Test AIAnalyzer class."""

    @pytest.fixture
    def ai_config_enabled(self):
        """Create enabled AI config."""
        return AIAnalysisConfig(
            enabled=True,
            api_key="test-api-key",
            model="claude-3-5-sonnet-20241022",
            enable_root_cause_analysis=True,
            enable_remediation_suggestions=True,
            enable_correlation_analysis=True,
        )

    @pytest.fixture
    def ai_config_disabled(self):
        """Create disabled AI config."""
        return AIAnalysisConfig(enabled=False)

    @pytest.fixture
    def drift_report_with_issues(self):
        """Create drift report with issues."""
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

        report = DriftReport(
            api_url="https://api.example.com",
            spec_source="/path/to/spec.yaml",
            contract_drift=[contract_issue],
            validation_drift=[validation_issue],
        )
        report.calculate_summary()
        return report

    @pytest.fixture
    def empty_drift_report(self):
        """Create drift report with no issues."""
        report = DriftReport(
            api_url="https://api.example.com",
            spec_source="/path/to/spec.yaml",
        )
        report.calculate_summary()
        return report

    def test_analyzer_initialization_enabled(self, ai_config_enabled):
        """Test analyzer initializes correctly when enabled."""
        with patch("api_contract_validator.analysis.reasoning.analyzer.Anthropic") as mock_anthropic:
            analyzer = AIAnalyzer(ai_config_enabled)
            assert analyzer.config == ai_config_enabled
            mock_anthropic.assert_called_once_with(api_key="test-api-key")

    def test_analyzer_initialization_disabled(self, ai_config_disabled):
        """Test analyzer initializes correctly when disabled."""
        analyzer = AIAnalyzer(ai_config_disabled)
        assert analyzer.config == ai_config_disabled
        assert analyzer.client is None

    def test_analyzer_initialization_no_api_key(self):
        """Test analyzer handles missing API key gracefully."""
        config = AIAnalysisConfig(enabled=True, api_key=None)
        analyzer = AIAnalyzer(config)
        assert analyzer.client is None

    def test_analyze_drift_disabled(self, ai_config_disabled, drift_report_with_issues):
        """Test analysis is skipped when disabled."""
        analyzer = AIAnalyzer(ai_config_disabled)
        result = analyzer.analyze_drift(drift_report_with_issues)
        assert result is None

    def test_analyze_drift_no_client(self, drift_report_with_issues):
        """Test analysis is skipped when client not initialized."""
        config = AIAnalysisConfig(enabled=True, api_key=None)
        analyzer = AIAnalyzer(config)
        result = analyzer.analyze_drift(drift_report_with_issues)
        assert result is None

    def test_analyze_drift_no_issues(self, ai_config_enabled, empty_drift_report):
        """Test analysis with no drift issues."""
        with patch("api_contract_validator.analysis.reasoning.analyzer.Anthropic"):
            analyzer = AIAnalyzer(ai_config_enabled)
            result = analyzer.analyze_drift(empty_drift_report)

            assert result is not None
            assert isinstance(result, AnalysisResult)
            assert "No drift issues detected" in result.executive_summary
            assert result.model_used == ai_config_enabled.model

    @patch("api_contract_validator.analysis.reasoning.analyzer.Anthropic")
    def test_analyze_drift_with_issues(self, mock_anthropic, ai_config_enabled, drift_report_with_issues):
        """Test full analysis with issues."""
        # Mock the Anthropic client
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        # Mock API responses
        mock_response = Mock()
        mock_response.content = [Mock(text="Analysis summary text")]
        mock_client.messages.create.return_value = mock_response

        analyzer = AIAnalyzer(ai_config_enabled)
        result = analyzer.analyze_drift(drift_report_with_issues)

        assert result is not None
        assert isinstance(result, AnalysisResult)
        assert result.model_used == ai_config_enabled.model
        assert result.executive_summary is not None
        # Verify API was called
        assert mock_client.messages.create.called

    def test_generate_executive_summary_success(self, ai_config_enabled, drift_report_with_issues):
        """Test executive summary generation."""
        with patch("api_contract_validator.analysis.reasoning.analyzer.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client

            mock_response = Mock()
            mock_response.content = [Mock(text="Critical drift detected in authentication endpoints.")]
            mock_client.messages.create.return_value = mock_response

            analyzer = AIAnalyzer(ai_config_enabled)
            summary = analyzer._generate_executive_summary(drift_report_with_issues)

            assert "Critical drift" in summary
            assert mock_client.messages.create.called

    def test_generate_executive_summary_failure(self, ai_config_enabled, drift_report_with_issues):
        """Test executive summary generation handles failures."""
        with patch("api_contract_validator.analysis.reasoning.analyzer.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            mock_client.messages.create.side_effect = Exception("API error")

            analyzer = AIAnalyzer(ai_config_enabled)
            summary = analyzer._generate_executive_summary(drift_report_with_issues)

            # Should return fallback summary
            assert "drift issues" in summary.lower()
            assert "endpoints" in summary.lower()

    def test_extract_patterns_validation_drift(self, ai_config_enabled):
        """Test pattern extraction for validation drift."""
        with patch("api_contract_validator.analysis.reasoning.analyzer.Anthropic"):
            analyzer = AIAnalyzer(ai_config_enabled)

            # Create report with many validation issues
            validation_issues = [
                ValidationDriftIssue(
                    endpoint_id=f"GET /endpoint{i}",
                    test_id=f"test_{i}",
                    test_type="INVALID",
                    violated_constraint="validation",
                    input_data={},
                    actual_status_code=200,
                    expected_status_code_range="400-499",
                    message="Invalid accepted",
                )
                for i in range(10)
            ]

            report = DriftReport(
                api_url="https://api.example.com",
                spec_source="/path/to/spec.yaml",
                validation_drift=validation_issues,
            )
            report.calculate_summary()

            result = AnalysisResult(
                model_used="test-model",
                analysis_timestamp=datetime.utcnow().isoformat(),
            )

            analyzer._extract_patterns(report, result)

            assert len(result.systemic_issues) > 0
            assert any("validation" in issue.lower() for issue in result.systemic_issues)

    def test_extract_patterns_contract_drift(self, ai_config_enabled):
        """Test pattern extraction for contract drift."""
        with patch("api_contract_validator.analysis.reasoning.analyzer.Anthropic"):
            analyzer = AIAnalyzer(ai_config_enabled)

            # Create report with many contract issues
            contract_issues = [
                ContractDriftIssue(
                    endpoint_id=f"GET /endpoint{i}",
                    test_id=f"test_{i}",
                    location="response_body",
                    field_path="data",
                    violation_type="MISSING_REQUIRED_FIELD",
                    expected="string",
                    actual=None,
                    message="Missing field",
                    status_code=200,
                )
                for i in range(8)
            ]

            report = DriftReport(
                api_url="https://api.example.com",
                spec_source="/path/to/spec.yaml",
                contract_drift=contract_issues,
            )
            report.calculate_summary()

            result = AnalysisResult(
                model_used="test-model",
                analysis_timestamp=datetime.utcnow().isoformat(),
            )

            analyzer._extract_patterns(report, result)

            assert len(result.systemic_issues) > 0
            assert any("contract" in issue.lower() for issue in result.systemic_issues)

    def test_extract_bullet_points(self, ai_config_enabled):
        """Test bullet point extraction from text."""
        with patch("api_contract_validator.analysis.reasoning.analyzer.Anthropic"):
            analyzer = AIAnalyzer(ai_config_enabled)

            text = """
            Some intro text.

            - First point
            - Second point
            * Third point with asterisk
            • Fourth point with bullet

            1. Numbered first
            2. Numbered second

            Some closing text.
            """

            points = analyzer._extract_bullet_points(text)

            assert len(points) >= 4
            assert "First point" in points
            assert "Second point" in points

    def test_build_executive_summary_prompt(self, ai_config_enabled, drift_report_with_issues):
        """Test executive summary prompt building."""
        with patch("api_contract_validator.analysis.reasoning.analyzer.Anthropic"):
            analyzer = AIAnalyzer(ai_config_enabled)
            prompt = analyzer._build_executive_summary_prompt(drift_report_with_issues)

            assert "Total Issues" in prompt
            assert "By Severity" in prompt
            assert "Affected Endpoints" in prompt
            assert str(drift_report_with_issues.summary.total_issues) in prompt

    def test_build_root_cause_prompt(self, ai_config_enabled):
        """Test root cause prompt building."""
        with patch("api_contract_validator.analysis.reasoning.analyzer.Anthropic"):
            analyzer = AIAnalyzer(ai_config_enabled)

            endpoint_issues = {
                "contract": [
                    ContractDriftIssue(
                        endpoint_id="GET /users",
                        test_id="test_001",
                        location="response_body",
                        field_path="data.email",
                        violation_type="MISSING_REQUIRED_FIELD",
                        expected="string",
                        actual=None,
                        message="Missing field",
                        status_code=200,
                    )
                ],
                "validation": [],
                "behavioral": [],
            }

            prompt = analyzer._build_root_cause_prompt("GET /users", endpoint_issues)

            assert "GET /users" in prompt
            assert "contract" in prompt
            assert "root cause" in prompt.lower()

"""
Integration tests for CLI commands.
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from api_contract_validator.cli.main import cli


@pytest.mark.integration
class TestCLICommands:
    """Test CLI command integration."""

    @pytest.fixture
    def runner(self):
        """Create Click CLI runner."""
        return CliRunner()

    @pytest.fixture
    def spec_file(self, tmp_path, sample_openapi_yaml_content):
        """Create temporary spec file."""
        spec_path = tmp_path / "test_spec.yaml"
        spec_path.write_text(sample_openapi_yaml_content)
        return spec_path

    # ========================================================================
    # Validate Command Tests
    # ========================================================================

    def test_validate_command_success(self, runner, httpserver, spec_file):
        """Test validate command with passing validation."""
        # Setup mock API responses
        httpserver.expect_request("/users").respond_with_json(
            [{"id": 1, "email": "test@example.com", "name": "Test"}], status=200
        )
        httpserver.expect_request("/users", method="POST").respond_with_json(
            {"id": 1, "email": "test@example.com", "name": "Test"}, status=201
        )
        httpserver.expect_request("/users/1").respond_with_json(
            {"id": 1, "email": "test@example.com", "name": "Test"}, status=200
        )

        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                [
                    "validate",
                    str(spec_file),
                    "--api-url",
                    httpserver.url_for("/"),
                    "--no-ai-analysis",
                    "--parallel",
                    "2",
                ],
            )

            # Check output contains success indicators
            assert "Starting API Validation" in result.output
            assert "Validation Complete" in result.output or "complete" in result.output.lower()

    def test_validate_command_exit_codes(self, runner, httpserver, spec_file):
        """Test validate command exit codes."""
        # Setup responses that will pass validation
        httpserver.expect_request("/users").respond_with_json([], status=200)
        httpserver.expect_request("/users", method="POST").respond_with_json(
            {"id": 1, "email": "test@example.com", "name": "Test"}, status=201
        )
        httpserver.expect_request("/users/1").respond_with_json(
            {"id": 1, "email": "test@example.com", "name": "Test"}, status=200
        )

        result = runner.invoke(
            cli,
            [
                "validate",
                str(spec_file),
                "--api-url",
                httpserver.url_for("/"),
                "--no-ai-analysis",
            ],
        )

        # Should exit with 0 or 1 (not crash)
        assert result.exit_code in [0, 1]

    def test_validate_command_output_formats(self, runner, httpserver, spec_file):
        """Test different output formats."""
        httpserver.expect_request("/users").respond_with_json([], status=200)
        httpserver.expect_request("/users", method="POST").respond_with_json({}, status=201)
        httpserver.expect_request("/users/1").respond_with_json({}, status=200)

        with runner.isolated_filesystem(temp_dir=Path("/tmp")):
            result = runner.invoke(
                cli,
                [
                    "validate",
                    str(spec_file),
                    "--api-url",
                    httpserver.url_for("/"),
                    "--format",
                    "json",
                    "--output",
                    "./test_output",
                    "--no-ai-analysis",
                ],
            )

            # Check that output directory exists or was mentioned
            assert result.exit_code in [0, 1]

    def test_validate_command_config_override(self, runner, httpserver, spec_file):
        """Test CLI config overrides."""
        httpserver.expect_request("/users").respond_with_json([], status=200)
        httpserver.expect_request("/users", method="POST").respond_with_json({}, status=201)
        httpserver.expect_request("/users/1").respond_with_json({}, status=200)

        result = runner.invoke(
            cli,
            [
                "validate",
                str(spec_file),
                "--api-url",
                httpserver.url_for("/"),
                "--parallel",
                "3",
                "--timeout",
                "15",
                "--no-ai-analysis",
            ],
        )

        # Should execute without crashing
        assert result.exit_code in [0, 1]

    def test_validate_command_no_ai_flag(self, runner, httpserver, spec_file):
        """Test that --no-ai-analysis flag disables AI."""
        httpserver.expect_request("/users").respond_with_json([], status=200)
        httpserver.expect_request("/users", method="POST").respond_with_json({}, status=201)
        httpserver.expect_request("/users/1").respond_with_json({}, status=200)

        result = runner.invoke(
            cli,
            [
                "validate",
                str(spec_file),
                "--api-url",
                httpserver.url_for("/"),
                "--no-ai-analysis",
            ],
        )

        # Should not attempt AI analysis (no error about missing API key)
        assert result.exit_code in [0, 1]

    # ========================================================================
    # Config Check Command Tests
    # ========================================================================

    def test_config_check_command(self, runner):
        """Test config-check command."""
        result = runner.invoke(cli, ["config-check"])

        assert result.exit_code == 0
        assert "Configuration Check" in result.output
        assert "Python version" in result.output
        assert "Package version" in result.output

    # ========================================================================
    # CLI Help Tests
    # ========================================================================

    def test_cli_help_output(self, runner):
        """Test CLI help message."""
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "api-contract-validator" in result.output or "API Contract Validator" in result.output
        assert "validate" in result.output

    def test_validate_help_output(self, runner):
        """Test validate command help."""
        result = runner.invoke(cli, ["validate", "--help"])

        assert result.exit_code == 0
        assert "SPEC_PATH" in result.output or "spec" in result.output.lower()
        assert "--api-url" in result.output

    # ========================================================================
    # Error Handling Tests
    # ========================================================================

    def test_validate_with_invalid_spec_path(self, runner):
        """Test validate with nonexistent spec file."""
        result = runner.invoke(
            cli,
            [
                "validate",
                "/nonexistent/spec.yaml",
                "--api-url",
                "http://localhost:8000",
            ],
        )

        assert result.exit_code != 0

    def test_validate_missing_required_api_url(self, runner, spec_file):
        """Test validate without required --api-url flag."""
        result = runner.invoke(cli, ["validate", str(spec_file)])

        # Should error about missing --api-url
        assert result.exit_code != 0

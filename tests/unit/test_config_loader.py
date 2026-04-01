"""
Unit tests for config loader.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from api_contract_validator.config.loader import ConfigLoader, get_config, reset_config, set_config
from api_contract_validator.config.models import Config


@pytest.mark.unit
class TestConfigLoader:
    """Test ConfigLoader class."""

    def test_load_default_config(self):
        """Test loading default configuration."""
        config = ConfigLoader.load_default()

        assert isinstance(config, Config)
        assert config.execution.parallel_workers == 10
        assert config.test_generation.generate_valid is True
        assert config.ai_analysis.enabled is True

    def test_load_yaml_config_file(self, tmp_path):
        """Test loading configuration from YAML file."""
        config_data = {
            "execution": {"parallel_workers": 20, "timeout_seconds": 60},
            "ai_analysis": {"enabled": False},
        }

        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = ConfigLoader.load_from_file(config_file)

        assert config.execution.parallel_workers == 20
        assert config.execution.timeout_seconds == 60
        assert config.ai_analysis.enabled is False

    def test_load_with_overrides(self, tmp_path):
        """Test that CLI overrides take precedence."""
        config_data = {"execution": {"parallel_workers": 5}}
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        cli_overrides = {"execution": {"parallel_workers": 15}}

        config = ConfigLoader.load(config_path=config_file, cli_overrides=cli_overrides)

        # CLI override should win
        assert config.execution.parallel_workers == 15

    def test_config_validation(self, tmp_path):
        """Test that invalid config values raise errors."""
        config_data = {
            "execution": {"parallel_workers": 500}  # Exceeds max of 100
        }

        config_file = tmp_path / "invalid_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        with pytest.raises(ValueError) as exc_info:
            ConfigLoader.load_from_file(config_file)

        assert "Invalid" in str(exc_info.value) or "validation" in str(exc_info.value).lower()

    def test_merge_partial_config(self, tmp_path):
        """Test that partial YAML config merges with defaults."""
        # Only override one setting
        config_data = {"execution": {"parallel_workers": 25}}

        config_file = tmp_path / "partial_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = ConfigLoader.load(config_path=config_file)

        # Overridden value
        assert config.execution.parallel_workers == 25
        # Default values should still be present
        assert config.execution.timeout_seconds == 30  # default
        assert config.ai_analysis.enabled is True  # default

    def test_environment_variable_override(self, tmp_path):
        """Test that environment variables override config."""
        with patch.dict(
            os.environ,
            {
                "ACV_EXECUTION_PARALLEL_WORKERS": "35",
                "ANTHROPIC_API_KEY": "test-key-from-env",
                "ACV_AI_ANALYSIS_ENABLED": "false",
            },
        ):
            config = ConfigLoader.load()

            assert config.execution.parallel_workers == 35
            assert config.ai_analysis.api_key == "test-key-from-env"
            assert config.ai_analysis.enabled is False

    def test_invalid_yaml_raises_error(self, tmp_path):
        """Test that malformed YAML raises error."""
        config_file = tmp_path / "bad.yaml"
        config_file.write_text("invalid: yaml: content:\n  broken")

        with pytest.raises(ValueError) as exc_info:
            ConfigLoader.load_from_file(config_file)

        assert "YAML" in str(exc_info.value)

    def test_missing_file_raises_error(self):
        """Test that nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            ConfigLoader.load_from_file(Path("/nonexistent/config.yaml"))

    def test_global_config_management(self):
        """Test global config get/set/reset functions."""
        reset_config()

        # Get default config
        config1 = get_config()
        assert isinstance(config1, Config)

        # Set custom config
        custom_config = Config(execution={"parallel_workers": 99})
        set_config(custom_config)

        config2 = get_config()
        assert config2.execution.parallel_workers == 99

        # Reset
        reset_config()
        config3 = get_config()
        assert config3.execution.parallel_workers == 10  # back to default

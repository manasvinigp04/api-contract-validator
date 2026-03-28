"""
Configuration Loader

Loads and manages configuration from YAML files, environment variables, and CLI options.
"""

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import ValidationError

from api_contract_validator.config.models import Config


class ConfigLoader:
    """
    Handles loading and merging configuration from multiple sources:
    1. Default configuration
    2. YAML configuration file
    3. Environment variables
    4. CLI options
    """

    @staticmethod
    def load_from_file(config_path: Path) -> Config:
        """Load configuration from a YAML file."""
        try:
            with open(config_path, "r") as f:
                config_dict = yaml.safe_load(f) or {}
            return Config(**config_dict)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}")
        except ValidationError as e:
            raise ValueError(f"Invalid configuration: {e}")

    @staticmethod
    def load_default() -> Config:
        """Load default configuration."""
        return Config()

    @staticmethod
    def load_from_env() -> dict:
        """
        Load configuration overrides from environment variables.

        Environment variables follow the pattern:
        ACV_<SECTION>_<KEY> = value

        Examples:
        - ACV_EXECUTION_PARALLEL_WORKERS=20
        - ACV_AI_ANALYSIS_ENABLED=false
        - ACV_REPORTING_OUTPUT_DIRECTORY=/tmp/reports
        """
        env_config = {}

        # Execution config
        if parallel := os.getenv("ACV_EXECUTION_PARALLEL_WORKERS"):
            env_config.setdefault("execution", {})["parallel_workers"] = int(parallel)
        if timeout := os.getenv("ACV_EXECUTION_TIMEOUT_SECONDS"):
            env_config.setdefault("execution", {})["timeout_seconds"] = int(timeout)

        # AI Analysis config
        if api_key := os.getenv("ANTHROPIC_API_KEY"):
            env_config.setdefault("ai_analysis", {})["api_key"] = api_key
        if enabled := os.getenv("ACV_AI_ANALYSIS_ENABLED"):
            env_config.setdefault("ai_analysis", {})["enabled"] = enabled.lower() == "true"
        if model := os.getenv("ACV_AI_ANALYSIS_MODEL"):
            env_config.setdefault("ai_analysis", {})["model"] = model

        # Reporting config
        if output_dir := os.getenv("ACV_REPORTING_OUTPUT_DIRECTORY"):
            env_config.setdefault("reporting", {})["output_directory"] = output_dir

        # Logging config
        if log_level := os.getenv("ACV_LOG_LEVEL"):
            env_config.setdefault("logging", {})["level"] = log_level

        # Environment
        if environment := os.getenv("ACV_ENVIRONMENT"):
            env_config["environment"] = environment

        return env_config

    @staticmethod
    def merge_configs(*config_dicts: dict) -> dict:
        """Merge multiple configuration dictionaries, with later ones taking precedence."""
        merged = {}
        for config_dict in config_dicts:
            for key, value in config_dict.items():
                if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
                    merged[key] = ConfigLoader.merge_configs(merged[key], value)
                else:
                    merged[key] = value
        return merged

    @classmethod
    def load(
        cls,
        config_path: Optional[Path] = None,
        cli_overrides: Optional[dict] = None,
    ) -> Config:
        """
        Load configuration from all sources with proper precedence:
        1. Default configuration (lowest priority)
        2. YAML file configuration
        3. Environment variables
        4. CLI options (highest priority)
        """
        # Start with defaults
        default_config = cls.load_default()
        config_dict = default_config.model_dump()

        # Load from file if provided
        if config_path:
            try:
                file_config = cls.load_from_file(config_path)
                config_dict = cls.merge_configs(config_dict, file_config.model_dump())
            except Exception as e:
                raise ValueError(f"Failed to load configuration file: {e}")

        # Apply environment variables
        env_config = cls.load_from_env()
        if env_config:
            config_dict = cls.merge_configs(config_dict, env_config)

        # Apply CLI overrides
        if cli_overrides:
            config_dict = cls.merge_configs(config_dict, cli_overrides)

        # Create final Config object
        try:
            return Config(**config_dict)
        except ValidationError as e:
            raise ValueError(f"Invalid merged configuration: {e}")


# Global configuration instance
_global_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _global_config
    if _global_config is None:
        _global_config = ConfigLoader.load_default()
    return _global_config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _global_config
    _global_config = config


def reset_config() -> None:
    """Reset the global configuration to defaults."""
    global _global_config
    _global_config = None

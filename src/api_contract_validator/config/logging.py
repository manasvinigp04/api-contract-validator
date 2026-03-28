"""
Logging Configuration

Centralized logging setup for the API Contract Validator.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from rich.logging import RichHandler

from api_contract_validator.config.models import LoggingConfig


class LoggerSetup:
    """Handles logging configuration and setup."""

    _configured = False

    @classmethod
    def setup(cls, config: Optional[LoggingConfig] = None) -> None:
        """
        Configure logging based on the provided configuration.

        Args:
            config: LoggingConfig instance. If None, uses default configuration.
        """
        if cls._configured:
            return

        if config is None:
            config = LoggingConfig()

        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(config.level)

        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Console handler with Rich formatting
        if config.console_output:
            console_handler = RichHandler(
                rich_tracebacks=True,
                markup=True,
                show_time=True,
                show_path=False,
            )
            console_handler.setLevel(config.level)
            console_formatter = logging.Formatter(
                "%(message)s",
                datefmt="[%X]",
            )
            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)

        # File handler
        if config.file_path:
            file_path = Path(config.file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(file_path)
            file_handler.setLevel(config.level)
            file_formatter = logging.Formatter(config.format)
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)

        cls._configured = True

    @classmethod
    def reset(cls) -> None:
        """Reset logging configuration."""
        cls._configured = False
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Convenience loggers for different modules
cli_logger = get_logger("api_contract_validator.cli")
parser_logger = get_logger("api_contract_validator.parser")
validator_logger = get_logger("api_contract_validator.validator")
generator_logger = get_logger("api_contract_validator.generator")
executor_logger = get_logger("api_contract_validator.executor")
analyzer_logger = get_logger("api_contract_validator.analyzer")
reporter_logger = get_logger("api_contract_validator.reporter")

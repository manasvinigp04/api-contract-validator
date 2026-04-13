"""
Claude Code Integration Generator

Generates CLAUDE.md and .claude/skills/ files to help users
fix drift issues using Claude Code CLI.
"""

from api_contract_validator.reporting.claude_integration.generator import (
    ClaudeIntegrationGenerator,
)

__all__ = ["ClaudeIntegrationGenerator"]

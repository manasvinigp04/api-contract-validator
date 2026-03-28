"""
CLI Main Entry Point

This module provides the main CLI interface for the API Contract Validator.
"""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel

from api_contract_validator import __version__

console = Console()


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="api-contract-validator")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to configuration file (YAML)",
)
@click.option("--verbose", "-v", count=True, help="Increase verbosity (can be repeated)")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-error output")
@click.pass_context
def cli(ctx: click.Context, config: Optional[Path], verbose: int, quiet: bool) -> None:
    """
    API Contract Validator - Multi-dimensional API contract validation system

    Validates API implementations against OpenAPI specifications and PRD documents,
    detects contract, validation, and behavioral drift, and generates actionable reports.
    """
    # Store config in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet

    # If no subcommand is provided, show welcome message
    if ctx.invoked_subcommand is None:
        console.print(
            Panel(
                "[bold cyan]API Contract Validator[/bold cyan]\n\n"
                f"Version: {__version__}\n\n"
                "A sophisticated API contract validation system with:\n"
                "  • Multi-fidelity input support (OpenAPI + PRD)\n"
                "  • Intelligent test generation\n"
                "  • Multi-dimensional drift detection\n"
                "  • AI-assisted analysis\n"
                "  • Comprehensive reporting\n\n"
                "Use [bold]--help[/bold] to see available commands.",
                title="Welcome",
                border_style="cyan",
            )
        )


@cli.command()
@click.argument("spec_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--api-url",
    "-u",
    required=True,
    help="Base URL of the API to validate",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output directory for reports (default: ./output)",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["markdown", "json", "both"], case_sensitive=False),
    default="both",
    help="Output format for reports",
)
@click.option(
    "--parallel",
    "-p",
    type=int,
    default=10,
    help="Number of parallel test executions",
)
@click.option(
    "--timeout",
    "-t",
    type=int,
    default=30,
    help="Request timeout in seconds",
)
@click.option(
    "--no-ai-analysis",
    is_flag=True,
    help="Disable AI-assisted analysis (use rule-based only)",
)
@click.pass_context
def validate(
    ctx: click.Context,
    spec_path: Path,
    api_url: str,
    output: Optional[Path],
    format: str,
    parallel: int,
    timeout: int,
    no_ai_analysis: bool,
) -> None:
    """
    Validate API against specification

    SPEC_PATH: Path to OpenAPI specification (YAML/JSON) or PRD document
    """
    console.print(f"[bold green]Validating API:[/bold green] {api_url}")
    console.print(f"[bold blue]Specification:[/bold blue] {spec_path}")

    # TODO: Implement validation logic
    console.print("\n[yellow]⚠ Implementation in progress...[/yellow]")
    console.print("This command will:")
    console.print("  1. Parse the specification")
    console.print("  2. Generate test cases")
    console.print("  3. Execute tests against the API")
    console.print("  4. Detect drift")
    console.print("  5. Generate reports")


@cli.command()
@click.argument("spec_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file for generated tests",
)
@click.option(
    "--prioritize/--no-prioritize",
    default=True,
    help="Apply risk-based prioritization",
)
@click.pass_context
def generate_tests(
    ctx: click.Context, spec_path: Path, output: Optional[Path], prioritize: bool
) -> None:
    """
    Generate test cases from specification

    SPEC_PATH: Path to OpenAPI specification or PRD document
    """
    console.print(f"[bold blue]Generating tests from:[/bold blue] {spec_path}")

    # TODO: Implement test generation logic
    console.print("\n[yellow]⚠ Implementation in progress...[/yellow]")


@cli.command()
@click.argument("spec_path", type=click.Path(exists=True, path_type=Path))
@click.pass_context
def parse(ctx: click.Context, spec_path: Path) -> None:
    """
    Parse and validate specification file

    SPEC_PATH: Path to OpenAPI specification or PRD document
    """
    console.print(f"[bold blue]Parsing specification:[/bold blue] {spec_path}")

    # TODO: Implement parsing logic
    console.print("\n[yellow]⚠ Implementation in progress...[/yellow]")


@cli.command()
@click.option(
    "--ai-key",
    help="Anthropic API key for AI-assisted analysis",
)
@click.pass_context
def config_check(ctx: click.Context, ai_key: Optional[str]) -> None:
    """
    Check configuration and dependencies
    """
    console.print("[bold cyan]Configuration Check[/bold cyan]\n")

    # Check Python version
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    console.print(f"✓ Python version: {py_version}")

    # Check package version
    console.print(f"✓ Package version: {__version__}")

    # Check for AI API key
    import os

    ai_key = ai_key or os.getenv("ANTHROPIC_API_KEY")
    if ai_key:
        console.print("✓ Anthropic API key configured")
    else:
        console.print("[yellow]⚠ Anthropic API key not found (AI analysis will be disabled)[/yellow]")

    # Check spaCy model
    try:
        import spacy

        try:
            nlp = spacy.load("en_core_web_sm")
            console.print("✓ spaCy model (en_core_web_sm) loaded")
        except OSError:
            console.print(
                "[yellow]⚠ spaCy model not found. Run: python -m spacy download en_core_web_sm[/yellow]"
            )
    except ImportError:
        console.print("[red]✗ spaCy not installed[/red]")

    console.print("\n[green]Configuration check complete![/green]")


def main() -> None:
    """Main entry point for the CLI."""
    try:
        cli(obj={})
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

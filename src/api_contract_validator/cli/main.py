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
    type=click.Choice(["markdown", "json", "cli", "all"], case_sensitive=False),
    default="all",
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
    from api_contract_validator.analysis.drift.detector import DriftDetector
    from api_contract_validator.analysis.reasoning.analyzer import AIAnalyzer
    from api_contract_validator.config.exceptions import ACVException
    from api_contract_validator.config.loader import ConfigLoader, set_config
    from api_contract_validator.config.logging import LoggerSetup, get_logger
    from api_contract_validator.execution.collector.result_collector import ResultCollector
    from api_contract_validator.execution.runner.executor import TestExecutor
    from api_contract_validator.generation.test_generator import MasterTestGenerator
    from api_contract_validator.input.openapi.parser import OpenAPIParser
    from api_contract_validator.reporting.generator import ReportGenerator
    from api_contract_validator.schema.contract.constraint_extractor import ConstraintExtractor

    cli_logger = get_logger("api_contract_validator.cli")

    try:
        console.print(f"\n[bold green]Starting API Validation[/bold green]")
        console.print(f"API URL: {api_url}")
        console.print(f"Specification: {spec_path}\n")

        # Step 1: Load configuration
        console.print("[cyan]⚙  Loading configuration...[/cyan]")
        config_overrides = {
            "execution": {"parallel_workers": parallel, "timeout_seconds": timeout},
            "ai_analysis": {"enabled": not no_ai_analysis},
        }
        if output:
            config_overrides["reporting"] = {"output_directory": str(output)}

        config = ConfigLoader.load(ctx.obj.get("config_path"), config_overrides)
        set_config(config)
        LoggerSetup.setup(config.logging)
        cli_logger.info("Configuration loaded")

        # Step 2: Parse specification
        console.print("[cyan]📄 Parsing OpenAPI specification...[/cyan]")
        parser = OpenAPIParser()
        unified_spec = parser.parse_file(spec_path)
        console.print(f"   ✓ Parsed {len(unified_spec.endpoints)} endpoints")

        # Step 3: Extract contract rules
        console.print("[cyan]📋 Extracting contract rules...[/cyan]")
        extractor = ConstraintExtractor()
        api_contract = extractor.extract_contract(unified_spec)
        total_contracts = len(api_contract.endpoint_contracts)
        console.print(f"   ✓ Extracted contracts for {total_contracts} endpoints")

        # Step 4: Generate test cases
        console.print("[cyan]🧪 Generating test cases...[/cyan]")
        generator = MasterTestGenerator(config.test_generation)
        test_suite = generator.generate_test_suite(unified_spec)
        console.print(f"   ✓ Generated {len(test_suite.test_cases)} test cases")

        # Step 5: Execute tests
        console.print(f"[cyan]🚀 Executing tests (parallel={parallel})...[/cyan]")
        executor = TestExecutor(api_url, config.execution)
        test_results = executor.execute_tests_sync(test_suite.test_cases)

        collector = ResultCollector()
        collector.add_results(test_results)
        execution_summary = collector.get_summary()

        console.print(
            f"   ✓ Executed {execution_summary.total} tests: "
            f"[green]{execution_summary.passed} passed[/green], "
            f"[red]{execution_summary.failed} failed[/red]"
        )

        # Step 6: Detect drift
        console.print("[cyan]🔍 Detecting drift...[/cyan]")
        drift_detector = DriftDetector(api_contract, config.drift_detection)
        drift_report = drift_detector.detect_drift(execution_summary)
        drift_report.api_url = api_url  # Set API URL

        console.print(f"   ✓ Detected {drift_report.summary.total_issues} drift issues")
        if drift_report.has_critical_issues():
            console.print(f"   [red]⚠  {drift_report.summary.critical_count} critical issues![/red]")

        # Step 7: AI-assisted analysis
        analysis_result = None
        if config.ai_analysis.enabled and not no_ai_analysis:
            console.print("[cyan]🧠 Running AI-assisted analysis...[/cyan]")
            try:
                ai_analyzer = AIAnalyzer(config.ai_analysis)
                analysis_result = ai_analyzer.analyze_drift(drift_report)
                if analysis_result and analysis_result.has_insights():
                    console.print("   ✓ AI analysis complete")
                else:
                    console.print("   [yellow]⚠ AI analysis returned no insights[/yellow]")
            except Exception as e:
                console.print(f"   [yellow]⚠ AI analysis failed: {e}[/yellow]")
                cli_logger.warning(f"AI analysis failed: {e}")

        # Step 8: Generate reports
        console.print("[cyan]📊 Generating reports...[/cyan]")
        report_generator = ReportGenerator(config, console)
        report_paths = report_generator.generate_reports(
            drift_report=drift_report,
            analysis_result=analysis_result,
            output_format=format,
            output_dir=output,
        )

        # Display report locations
        console.print("\n[bold green]✓ Validation Complete![/bold green]\n")
        for format_name, path in report_paths.items():
            if path != Path("<console>"):
                console.print(f"  📄 {format_name.title()} report: [cyan]{path}[/cyan]")

        # Exit with appropriate code
        if drift_report.has_critical_issues():
            console.print("\n[red]❌ Critical drift issues detected - build should fail[/red]")
            sys.exit(1)
        elif drift_report.has_issues():
            console.print("\n[yellow]⚠  Drift issues detected - review recommended[/yellow]")
            sys.exit(0)
        else:
            console.print("\n[green]✅ No drift detected - API conforms to contract[/green]")
            sys.exit(0)

    except ACVException as e:
        console.print(f"\n[red]❌ Validation failed:[/red] {e}")
        cli_logger.error(f"Validation failed: {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ Unexpected error:[/red] {e}")
        cli_logger.exception("Unexpected error during validation")
        sys.exit(1)


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

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
@click.argument("spec_path", type=click.Path(exists=True, path_type=Path), required=False)
@click.option(
    "--api-url",
    "-u",
    help="Base URL of the API to validate",
)
@click.option(
    "--env",
    "-e",
    help="Environment to use (local, dev, staging, prod) - reads from acv_config.yaml",
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
    help="Number of parallel test executions",
)
@click.option(
    "--timeout",
    "-t",
    type=int,
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
    spec_path: Optional[Path],
    api_url: Optional[str],
    env: Optional[str],
    output: Optional[Path],
    format: str,
    parallel: Optional[int],
    timeout: Optional[int],
    no_ai_analysis: bool,
) -> None:
    """
    Validate API against specification

    If SPEC_PATH is not provided, ACV will look for 'acv_config.yaml' in the current directory
    and use the spec path defined there.

    Examples:
        acv validate api/specs/openapi.yaml --api-url http://localhost:8000
        acv validate --env dev  # Uses acv_config.yaml
        acv validate  # Autodiscover from acv_config.yaml
    """
    import yaml
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
        # Step 0: Auto-discover configuration from acv_config.yaml if needed
        acv_config_path = Path("acv_config.yaml")
        acv_config = None

        if acv_config_path.exists():
            console.print(f"[cyan]📋 Found acv_config.yaml[/cyan]")
            with open(acv_config_path) as f:
                acv_config = yaml.safe_load(f)

        # Resolve spec_path from config if not provided
        if not spec_path:
            if acv_config and "project" in acv_config and "spec" in acv_config["project"]:
                spec_path = Path(acv_config["project"]["spec"]["path"])
                console.print(f"[cyan]📄 Using spec from config: {spec_path}[/cyan]")
            else:
                console.print("[red]❌ No spec path provided and no acv_config.yaml found[/red]")
                console.print("Usage: acv validate <spec_path> --api-url <url>")
                console.print("   or: Create acv_config.yaml in your project root")
                sys.exit(1)

        # Resolve API URL from config/environment if not provided
        if not api_url:
            if acv_config and "api" in acv_config:
                if env and "environments" in acv_config["api"] and env in acv_config["api"]["environments"]:
                    api_url = acv_config["api"]["environments"][env]
                    console.print(f"[cyan]🌍 Using {env} environment: {api_url}[/cyan]")
                elif "base_url" in acv_config["api"]:
                    api_url = acv_config["api"]["base_url"]
                    console.print(f"[cyan]🌐 Using base URL from config: {api_url}[/cyan]")

        if not api_url:
            console.print("[red]❌ No API URL provided[/red]")
            console.print("Usage: acv validate --api-url <url>")
            console.print("   or: Define api.base_url in acv_config.yaml")
            sys.exit(1)

        console.print(f"\n[bold green]Starting API Validation[/bold green]")
        console.print(f"API URL: {api_url}")
        console.print(f"Specification: {spec_path}\n")

        # Step 1: Load configuration
        console.print("[cyan]⚙  Loading configuration...[/cyan]")

        # Build config overrides from CLI args and acv_config.yaml
        config_overrides = {}

        # Merge acv_config settings
        if acv_config:
            if "execution" in acv_config:
                config_overrides["execution"] = acv_config["execution"]
            if "test_generation" in acv_config:
                config_overrides["test_generation"] = acv_config["test_generation"]
            if "drift_detection" in acv_config:
                config_overrides["drift_detection"] = acv_config["drift_detection"]
            if "ai_analysis" in acv_config:
                config_overrides["ai_analysis"] = acv_config["ai_analysis"]
            if "reporting" in acv_config:
                config_overrides["reporting"] = acv_config["reporting"]
            if "logging" in acv_config:
                config_overrides["logging"] = acv_config["logging"]

        # CLI args override config file
        if parallel is not None:
            if "execution" not in config_overrides:
                config_overrides["execution"] = {}
            config_overrides["execution"]["parallel_workers"] = parallel

        if timeout is not None:
            if "execution" not in config_overrides:
                config_overrides["execution"] = {}
            config_overrides["execution"]["timeout_seconds"] = timeout

        if no_ai_analysis:
            if "ai_analysis" not in config_overrides:
                config_overrides["ai_analysis"] = {}
            config_overrides["ai_analysis"]["enabled"] = False

        if output:
            if "reporting" not in config_overrides:
                config_overrides["reporting"] = {}
            config_overrides["reporting"]["output_directory"] = str(output)
        elif acv_config and "project" in acv_config and "output" in acv_config["project"]:
            # Use output.reports from acv_config if specified
            if "reporting" not in config_overrides:
                config_overrides["reporting"] = {}
            config_overrides["reporting"]["output_directory"] = acv_config["project"]["output"].get("reports", "./output")

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
        extractor = ConstraintExtractor(unified_spec)
        api_contract = extractor.extract_contract()
        total_contracts = len(api_contract.endpoint_contracts)
        console.print(f"   ✓ Extracted contracts for {total_contracts} endpoints")

        # Step 4: Generate test cases
        console.print("[cyan]🧪 Generating test cases...[/cyan]")
        generator = MasterTestGenerator(config.test_generation)
        test_suite = generator.generate_test_suite(unified_spec)
        console.print(f"   ✓ Generated {len(test_suite.test_cases)} test cases")

        # Inject default headers from config into all test cases
        if acv_config and "api" in acv_config and "headers" in acv_config["api"]:
            default_headers = acv_config["api"]["headers"]
            console.print(f"[cyan]🔑 Injecting {len(default_headers)} default headers into all tests...[/cyan]")
            for test_case in test_suite.test_cases:
                # Merge default headers (test-specific headers override defaults)
                test_case.headers = {**default_headers, **test_case.headers}
            console.print(f"   ✓ Headers: {', '.join(default_headers.keys())}")

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
            spec_path=spec_path,  # Pass spec_path for Claude integration
        )

        # Display report locations
        console.print("\n[bold green]✓ Validation Complete![/bold green]\n")

        # Separate report types
        standard_reports = {}
        claude_files = {}

        for format_name, path in report_paths.items():
            if format_name in ["claude_md", "fix_validation_skill", "fix_contract_skill", "apply_remediations_skill"]:
                claude_files[format_name] = path
            else:
                standard_reports[format_name] = path

        # Display standard reports
        if standard_reports:
            console.print("[bold]📊 Reports Generated:[/bold]")
            for format_name, path in standard_reports.items():
                if path != Path("<console>"):
                    console.print(f"  • {format_name.title()}: [cyan]{path}[/cyan]")

        # Display Claude integration files
        if claude_files:
            console.print("\n[bold]🤖 Claude Code Integration (.acv/):[/bold]")
            for format_name, path in claude_files.items():
                file_description = {
                    "claude_md": "Project guidance",
                    "fix_validation_skill": "Fix validation drift",
                    "fix_contract_skill": "Fix contract drift",
                    "apply_remediations_skill": "Apply AI remediations",
                }.get(format_name, "Claude file")
                console.print(f"  • {file_description}: [cyan]{path}[/cyan]")

            console.print("\n[dim]💡 Files in .acv/ folder to avoid conflicts[/dim]")
            console.print("[dim]   Use: claude \"fix the validation drift issues\"[/dim]")

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
    help="Output file for generated tests (default: generated_tests.json)",
)
@click.option(
    "--prioritize/--no-prioritize",
    default=True,
    help="Apply risk-based prioritization",
)
@click.option(
    "--max-tests",
    "-m",
    type=int,
    default=50,
    help="Maximum tests per endpoint",
)
@click.pass_context
def generate_tests(
    ctx: click.Context, spec_path: Path, output: Optional[Path], prioritize: bool, max_tests: int
) -> None:
    """
    Generate test cases from specification

    SPEC_PATH: Path to OpenAPI specification or PRD document
    """
    import json

    from api_contract_validator.config.exceptions import ACVException
    from api_contract_validator.config.models import TestGenerationConfig
    from api_contract_validator.generation.test_generator import MasterTestGenerator
    from api_contract_validator.input.openapi.parser import OpenAPIParser

    try:
        console.print(f"[cyan]🧪 Generating tests from:[/cyan] {spec_path}\n")

        # Step 1: Parse specification
        console.print("[cyan]📄 Parsing specification...[/cyan]")
        parser = OpenAPIParser()
        spec = parser.parse_file(spec_path)
        console.print(f"   ✓ Parsed {len(spec.endpoints)} endpoints")

        # Step 2: Generate tests
        console.print("[cyan]🔧 Generating test cases...[/cyan]")
        gen_config = TestGenerationConfig(
            enable_prioritization=prioritize,
            max_tests_per_endpoint=max_tests,
        )
        generator = MasterTestGenerator(gen_config)
        test_suite = generator.generate_test_suite(spec)

        console.print(f"   ✓ Generated {len(test_suite.test_cases)} test cases")

        # Display distribution
        console.print("\n[bold]Test Distribution:[/bold]")
        console.print(f"  • Valid tests:    {len(test_suite.get_valid_tests())}")
        console.print(f"  • Invalid tests:  {len(test_suite.get_invalid_tests())}")
        console.print(f"  • Boundary tests: {len(test_suite.get_boundary_tests())}")

        if prioritize:
            high_priority = len(test_suite.get_high_priority_tests())
            console.print(f"  • High priority:  {high_priority}")

        # Step 3: Write output
        output_path = output or Path("generated_tests.json")
        console.print(f"\n[cyan]💾 Writing test suite...[/cyan]")

        test_suite_dict = test_suite.model_dump(mode="json")
        with open(output_path, "w") as f:
            json.dump(test_suite_dict, f, indent=2)

        console.print(f"   ✓ Test suite written to: [cyan]{output_path}[/cyan]")

        # Summary
        console.print(f"\n[bold green]✓ Test Generation Complete![/bold green]")
        console.print(f"   Total tests: {len(test_suite.test_cases)}")
        console.print(f"   Output file: {output_path}")

    except ACVException as e:
        console.print(f"\n[red]❌ Test generation failed:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ Unexpected error:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.argument("spec_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "tree", "json"], case_sensitive=False),
    default="table",
    help="Output format (table, tree, or json)",
)
@click.pass_context
def parse(ctx: click.Context, spec_path: Path, format: str) -> None:
    """
    Parse and display specification structure

    SPEC_PATH: Path to OpenAPI specification or PRD document
    """
    from rich.table import Table
    from rich.tree import Tree

    from api_contract_validator.config.exceptions import ACVException
    from api_contract_validator.input.openapi.parser import OpenAPIParser

    try:
        console.print(f"[cyan]📄 Parsing specification:[/cyan] {spec_path}")

        # Parse specification
        parser = OpenAPIParser()
        spec = parser.parse_file(spec_path)

        console.print(f"[green]✓ Successfully parsed specification[/green]\n")

        # Display metadata
        console.print(f"[bold]API:[/bold] {spec.metadata.title}")
        console.print(f"[bold]Version:[/bold] {spec.metadata.version}")
        if spec.metadata.description:
            console.print(f"[dim]{spec.metadata.description}[/dim]")
        if spec.metadata.base_url:
            console.print(f"[bold]Base URL:[/bold] {spec.metadata.base_url}")
        console.print()

        # Display endpoints based on format
        if format == "table":
            table = Table(title=f"Endpoints ({len(spec.endpoints)} total)", show_header=True)
            table.add_column("Method", style="cyan", width=8)
            table.add_column("Path", style="green")
            table.add_column("Operation ID", style="dim")
            table.add_column("Request", justify="center", width=8)
            table.add_column("Responses", width=15)

            for endpoint in spec.endpoints:
                has_body = "✓" if endpoint.request_body else "-"
                status_codes = ", ".join(str(r.status_code) for r in endpoint.responses)

                table.add_row(
                    endpoint.method.value,
                    endpoint.path,
                    endpoint.operation_id or "-",
                    has_body,
                    status_codes,
                )

            console.print(table)

        elif format == "tree":
            tree = Tree(f"[bold]{spec.metadata.title} v{spec.metadata.version}[/bold]")

            for endpoint in spec.endpoints:
                endpoint_label = f"[cyan]{endpoint.method.value}[/cyan] {endpoint.path}"
                if endpoint.operation_id:
                    endpoint_label += f" [dim]({endpoint.operation_id})[/dim]"

                endpoint_node = tree.add(endpoint_label)

                # Show parameters
                if endpoint.parameters:
                    params_node = endpoint_node.add(f"📌 Parameters ({len(endpoint.parameters)})")
                    for param in endpoint.parameters[:5]:  # Limit to first 5
                        req = "required" if param.constraints.required else "optional"
                        params_node.add(f"{param.name} ({param.location}): {param.type.value} [{req}]")

                # Show request body
                if endpoint.request_body:
                    body_node = endpoint_node.add("📥 Request Body")
                    for field_name, field_def in list(endpoint.request_body.schema.items())[:5]:
                        req = "required" if field_def.constraints.required else "optional"
                        body_node.add(f"{field_name}: {field_def.type.value} [{req}]")

                # Show responses
                if endpoint.responses:
                    resp_node = endpoint_node.add(f"📤 Responses ({len(endpoint.responses)})")
                    for response in endpoint.responses:
                        status_style = "green" if 200 <= response.status_code < 300 else "yellow"
                        resp_node.add(f"[{status_style}]{response.status_code}[/{status_style}] - {len(response.schema)} fields")

            console.print(tree)

        elif format == "json":
            import json

            output = spec.model_dump(mode="json")
            console.print_json(json.dumps(output, indent=2))

        # Summary
        console.print()
        console.print(f"[green]✓ {len(spec.endpoints)} endpoints parsed successfully[/green]")
        if spec.schemas:
            console.print(f"[green]✓ {len(spec.schemas)} schemas found[/green]")

    except ACVException as e:
        console.print(f"\n[red]❌ Parse failed:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ Unexpected error:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.option(
    "--spec-path",
    "-s",
    type=click.Path(path_type=Path),
    help="Path to OpenAPI specification (relative to project root)",
)
@click.option(
    "--api-url",
    "-u",
    help="Base URL of your API",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing acv_config.yaml",
)
@click.pass_context
def init(
    ctx: click.Context,
    spec_path: Optional[Path],
    api_url: Optional[str],
    force: bool,
) -> None:
    """
    Initialize ACV in your project by creating acv_config.yaml

    Creates a configuration file tailored to your project structure.
    """
    import yaml

    config_path = Path("acv_config.yaml")

    # Check if config already exists
    if config_path.exists() and not force:
        console.print("[yellow]⚠ acv_config.yaml already exists![/yellow]")
        console.print("Use --force to overwrite, or edit the existing file.")
        sys.exit(1)

    console.print("[bold cyan]🚀 Initializing ACV in your project[/bold cyan]\n")

    # Interactive prompts if not provided
    if not spec_path:
        spec_path_input = console.input(
            "[cyan]Path to OpenAPI spec (file or directory):[/cyan] [dim](e.g., openapi/api.yaml or openapi/)[/dim] "
        )
        spec_path = Path(spec_path_input) if spec_path_input else Path("openapi")

    if not api_url:
        api_url = console.input("[cyan]API base URL:[/cyan] [dim](e.g., http://localhost:8000)[/dim] ")
        api_url = api_url if api_url else "http://localhost:8000"

    # Try to detect security requirements from spec
    detected_headers = {}
    security_info = []

    console.print("\n[cyan]🔍 Analyzing OpenAPI spec for security requirements...[/cyan]")

    try:
        from api_contract_validator.input.openapi.parser import OpenAPIParser
        parser = OpenAPIParser()

        # Handle both file and directory paths
        spec_file = spec_path
        if spec_path.is_dir():
            yaml_files = list(spec_path.glob("*.yaml")) + list(spec_path.glob("*.yml"))
            if yaml_files:
                spec_file = yaml_files[0]
                console.print(f"   [dim]Found {len(yaml_files)} specs, analyzing {spec_file.name}[/dim]")

        if spec_file.exists():
            parsed_spec = parser.parse_file(spec_file)

            # Detect security schemes
            if parsed_spec.security_schemes:
                console.print(f"   [green]✓ Found {len(parsed_spec.security_schemes)} security scheme(s)[/green]")
                for scheme in parsed_spec.security_schemes:
                    security_info.append(f"     • {scheme.name}: {scheme.type}")

                    if scheme.type == "apiKey":
                        detected_headers[scheme.name] = "YOUR_API_KEY_HERE"
                    elif scheme.type in ["http", "bearer"]:
                        detected_headers["Authorization"] = "Bearer YOUR_TOKEN_HERE"
                    elif scheme.type == "oauth2":
                        detected_headers["Authorization"] = "Bearer YOUR_OAUTH_TOKEN_HERE"

                console.print("\n".join(security_info))
            else:
                console.print("   [dim]No security schemes defined in spec[/dim]")

            # Check for custom headers in spec (x-headers or parameters)
            for endpoint in parsed_spec.endpoints[:10]:  # Check first 10 endpoints
                for param in endpoint.parameters:
                    if param.location == "header" and param.name not in detected_headers:
                        default_val = "YOUR_VALUE_HERE"
                        if "tenant" in param.name.lower():
                            default_val = "default-tenant-id"
                        elif "resource" in param.name.lower():
                            default_val = "default"
                        detected_headers[param.name] = default_val

            if detected_headers:
                console.print(f"   [green]✓ Detected {len(detected_headers)} required header(s)[/green]")

    except Exception as e:
        console.print(f"   [dim]Could not analyze spec: {e}[/dim]")

    # Ask if user wants to add custom headers
    console.print("\n[cyan]🔑 HTTP Headers Configuration[/cyan]")

    if detected_headers:
        console.print("[dim]Detected headers from OpenAPI spec:[/dim]")
        for header, value in detected_headers.items():
            console.print(f"  • {header}: {value}")

        use_detected = console.input("\n[cyan]Use detected headers?[/cyan] [dim](y/n, default: y)[/dim] ")
        if use_detected.lower() not in ["n", "no"]:
            headers = detected_headers
        else:
            headers = {}
    else:
        add_headers = console.input(
            "[cyan]Does your API require custom headers?[/cyan] [dim](y/n, default: n)[/dim] "
        )
        headers = {}

        if add_headers.lower() in ["y", "yes"]:
            console.print("\n[dim]Enter headers (leave blank to finish):[/dim]")
            while True:
                header_name = console.input("  [cyan]Header name:[/cyan] ")
                if not header_name:
                    break
                header_value = console.input(f"  [cyan]Default value for {header_name}:[/cyan] ")
                headers[header_name] = header_value or "YOUR_VALUE_HERE"

    # Create configuration
    config = {
        "project": {
            "root": ".",
            "spec": {
                "path": str(spec_path),
                "format": "openapi"
            },
            "endpoints": {
                "directory": "src",
                "patterns": ["**/*.py", "**/*.js", "**/*.ts"]
            },
            "tests": {
                "directory": "tests",
                "patterns": ["test_*.py", "*_test.py", "**/*.test.js"]
            },
            "output": {
                "tests": "tests/generated",
                "reports": "reports/acv"
            }
        },
        "api": {
            "base_url": api_url,
            **({} if not headers else {"headers": headers}),  # Add headers if detected/configured
            "environments": {
                "local": "http://localhost:8000",
                "dev": "https://dev-api.example.com",
                "staging": "https://staging-api.example.com",
                "prod": "https://api.example.com"
            }
        },
        "execution": {
            "parallel_workers": 10,
            "timeout_seconds": 30,
            "retry_attempts": 3
        },
        "test_generation": {
            "generate_valid": True,
            "generate_invalid": True,
            "generate_boundary": True,
            "max_tests_per_endpoint": 50,
            "enable_prioritization": True
        },
        "drift_detection": {
            "detect_contract_drift": True,
            "detect_validation_drift": True,
            "detect_behavioral_drift": True
        },
        "ai_analysis": {
            "enabled": True,
            "model": "claude-3-5-sonnet-20241022"
        },
        "reporting": {
            "formats": ["markdown", "json"],
            "generate_claude_integration": True  # Generate .acv/ folder with Claude skills
        },
        "logging": {
            "level": "INFO",
            "format": "detailed"
        }
    }

    # Write config file with helpful comments
    console.print("\n[cyan]📝 Writing configuration...[/cyan]")

    with open(config_path, "w") as f:
        f.write("# API Contract Validator Configuration\n")
        f.write("# Generated by: acv init\n")
        f.write(f"# Spec: {spec_path}\n")
        f.write(f"# API: {api_url}\n\n")

        if headers:
            f.write("# ⚠️  SECURITY NOTE:\n")
            f.write("#   - Replace placeholder values (YOUR_*) with actual credentials\n")
            f.write("#   - Do NOT commit real secrets to version control\n")
            f.write("#   - Consider using environment variables: ${ENV_VAR_NAME}\n")
            f.write("#   - Add this file to .gitignore if it contains secrets\n\n")

        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        # Add inline comments for headers section
        if headers:
            f.write("\n# Headers Configuration:\n")
            f.write("# All headers in 'api.headers' are automatically included in every test request.\n")
            f.write("# Common patterns:\n")
            f.write("#   Authorization: Bearer ${AUTH_TOKEN}  (use env vars for secrets)\n")
            f.write("#   Content-Type: application/json       (usually needed for POST/PUT)\n")
            f.write("#   X-API-Key: ${API_KEY}                (for API key auth)\n")
            f.write("#   X-Tenant-ID: ${TENANT_ID}            (for multi-tenant APIs)\n\n")

    console.print(f"\n[green]✅ Created acv_config.yaml[/green]")

    if headers:
        console.print("\n[yellow]⚠️  IMPORTANT: Update placeholder header values![/yellow]")
        console.print("[dim]Replace 'YOUR_*' values with actual credentials before running tests.[/dim]")

    console.print("\n[bold]Configuration Summary:[/bold]")
    console.print(f"  • Spec: {spec_path}")
    console.print(f"  • API: {api_url}")
    if headers:
        console.print(f"  • Headers: {len(headers)} configured")
    console.print(f"  • Reports: reports/acv")
    console.print(f"  • Claude Integration: .acv/ folder")

    console.print("\n[bold]Next steps:[/bold]")
    console.print("  1. Review and customize acv_config.yaml")
    if headers:
        console.print("  2. [yellow]Replace placeholder header values (YOUR_*)[/yellow]")
        console.print("  3. Ensure your OpenAPI spec exists")
        console.print("  4. Start your API server")
        console.print(f"  5. Run: [cyan]acv validate[/cyan]")
    else:
        console.print("  2. Ensure your OpenAPI spec exists")
        console.print("  3. Start your API server")
        console.print(f"  4. Run: [cyan]acv validate[/cyan]")

    console.print("\n[dim]Tips:[/dim]")
    console.print("[dim]  • Use 'acv validate --env dev' to test different environments[/dim]")
    console.print("[dim]  • Add acv_config.yaml to .gitignore if it contains secrets[/dim]")
    console.print("[dim]  • View generated Claude guidance in .acv/CLAUDE.md after validation[/dim]")


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

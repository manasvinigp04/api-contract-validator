"""
CLI Formatter

Formats drift reports for console output using Rich library.
"""

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from api_contract_validator.analysis.drift.models import DriftReport
from api_contract_validator.analysis.reasoning.models import AnalysisResult
from api_contract_validator.config.logging import get_logger

logger = get_logger("api_contract_validator.reporter")


class CLIFormatter:
    """
    Formats drift analysis results for CLI output.
    """

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize CLI formatter.

        Args:
            console: Rich Console instance (creates new if not provided)
        """
        self.console = console or Console()

    def format_and_display(
        self,
        drift_report: DriftReport,
        analysis_result: Optional[AnalysisResult] = None,
    ) -> None:
        """
        Format and display drift report to console.

        Args:
            drift_report: Drift detection results
            analysis_result: Optional AI analysis results
        """
        logger.info("Formatting CLI output")

        # Display header
        self._display_header(drift_report)

        # Display test execution summary
        self._display_test_summary(drift_report)

        # Display drift summary
        self._display_drift_summary(drift_report)

        # Display top issues
        if drift_report.has_issues():
            self._display_top_issues(drift_report)

        # Display AI insights if available
        if analysis_result and analysis_result.has_insights():
            self._display_ai_insights(analysis_result)

        # Display conclusion
        self._display_conclusion(drift_report)

    def _display_header(self, drift_report: DriftReport) -> None:
        """Display report header."""
        self.console.print()
        self.console.print(
            Panel(
                f"[bold cyan]API Contract Validation Report[/bold cyan]\n\n"
                f"[dim]API:[/dim] {drift_report.api_url}\n"
                f"[dim]Spec:[/dim] {drift_report.spec_source}\n"
                f"[dim]Generated:[/dim] {drift_report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
                title="📊 Report",
                border_style="cyan",
            )
        )
        self.console.print()

    def _display_test_summary(self, drift_report: DriftReport) -> None:
        """Display test execution summary."""
        pass_rate = (
            (drift_report.tests_passed / drift_report.total_tests_executed * 100)
            if drift_report.total_tests_executed > 0
            else 0.0
        )

        table = Table(title="Test Execution Summary", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Tests", str(drift_report.total_tests_executed))
        table.add_row("Passed", f"[green]{drift_report.tests_passed}[/green] ✓")
        table.add_row("Failed", f"[red]{drift_report.tests_failed}[/red] ✗")
        table.add_row("Pass Rate", f"{pass_rate:.1f}%")

        self.console.print(table)
        self.console.print()

    def _display_drift_summary(self, drift_report: DriftReport) -> None:
        """Display drift detection summary."""
        table = Table(title="Drift Detection Summary", show_header=True, header_style="bold yellow")
        table.add_column("Category", style="cyan")
        table.add_column("Count", justify="right")

        # Total and severity
        table.add_row("[bold]Total Drift Issues[/bold]", f"[bold]{drift_report.summary.total_issues}[/bold]")
        table.add_row("Critical", f"[red]{drift_report.summary.critical_count}[/red] 🔴")
        table.add_row("High", f"[orange1]{drift_report.summary.high_count}[/orange1] 🟠")
        table.add_row("Medium", f"[yellow]{drift_report.summary.medium_count}[/yellow] 🟡")
        table.add_row("Low", f"[white]{drift_report.summary.low_count}[/white] ⚪")

        table.add_row("", "")  # Separator

        # By type
        table.add_row("Contract Drift", str(len(drift_report.contract_drift)))
        table.add_row("Validation Drift", str(len(drift_report.validation_drift)))
        table.add_row("Behavioral Drift", str(len(drift_report.behavioral_drift)))

        table.add_row("", "")  # Separator
        table.add_row("Affected Endpoints", str(len(drift_report.summary.affected_endpoints)))

        self.console.print(table)
        self.console.print()

    def _display_top_issues(self, drift_report: DriftReport) -> None:
        """Display top critical issues."""
        # Get critical and high severity issues
        critical_issues = [
            i for i in (drift_report.contract_drift + drift_report.validation_drift)
            if i.severity.value == "critical"
        ]
        high_issues = [
            i for i in (drift_report.contract_drift + drift_report.validation_drift)
            if i.severity.value == "high"
        ]

        if not critical_issues and not high_issues:
            return

        table = Table(
            title="🚨 Top Priority Issues",
            show_header=True,
            header_style="bold red",
        )
        table.add_column("Severity", style="bold")
        table.add_column("Endpoint", style="cyan")
        table.add_column("Issue", style="white")

        # Show up to 10 top issues
        top_issues = (critical_issues + high_issues)[:10]
        for issue in top_issues:
            severity_style = "red" if issue.severity.value == "critical" else "orange1"
            severity_icon = "🔴" if issue.severity.value == "critical" else "🟠"

            message = issue.message[:80] + "..." if len(issue.message) > 80 else issue.message

            table.add_row(
                f"[{severity_style}]{issue.severity.value.upper()}[/{severity_style}] {severity_icon}",
                issue.endpoint_id,
                message,
            )

        self.console.print(table)
        self.console.print()

    def _display_ai_insights(self, analysis_result: AnalysisResult) -> None:
        """Display AI-generated insights."""
        self.console.print(
            Panel(
                f"[bold cyan]AI-Assisted Analysis[/bold cyan]\n\n{analysis_result.executive_summary or 'No summary available'}",
                title="🧠 Insights",
                border_style="cyan",
            )
        )
        self.console.print()

        # Show systemic issues if any
        if analysis_result.systemic_issues:
            self.console.print("[bold yellow]Systemic Issues:[/bold yellow]")
            for issue in analysis_result.systemic_issues[:3]:
                self.console.print(f"  • {issue}")
            self.console.print()

        # Show quick wins if any
        if analysis_result.quick_wins:
            self.console.print("[bold green]Quick Wins:[/bold green]")
            for win in analysis_result.quick_wins[:3]:
                self.console.print(f"  • {win}")
            self.console.print()

    def _display_conclusion(self, drift_report: DriftReport) -> None:
        """Display conclusion and next steps."""
        if not drift_report.has_issues():
            self.console.print(
                Panel(
                    "[bold green]✅ All tests passed with no drift detected![/bold green]\n\n"
                    "API implementation conforms to contract specifications.",
                    title="Conclusion",
                    border_style="green",
                )
            )
        elif drift_report.has_critical_issues():
            self.console.print(
                Panel(
                    "[bold red]⚠️  Critical issues detected![/bold red]\n\n"
                    f"{drift_report.summary.critical_count} critical drift issues require immediate attention.\n"
                    "Review the detailed report for remediation steps.",
                    title="Conclusion",
                    border_style="red",
                )
            )
        else:
            self.console.print(
                Panel(
                    "[bold yellow]⚠️  Drift detected[/bold yellow]\n\n"
                    f"{drift_report.summary.total_issues} drift issues found across {len(drift_report.summary.affected_endpoints)} endpoints.\n"
                    "Review the detailed report for analysis and recommendations.",
                    title="Conclusion",
                    border_style="yellow",
                )
            )
        self.console.print()

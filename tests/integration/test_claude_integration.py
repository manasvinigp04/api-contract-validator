#!/usr/bin/env python3
"""
Test the Claude Integration Generator
"""
import json
from pathlib import Path

from api_contract_validator.analysis.drift.models import (
    DriftReport,
    DriftSeverity,
    DriftSummary,
    ValidationDriftIssue,
)
from api_contract_validator.config.models import Config
from api_contract_validator.reporting.claude_integration.generator import (
    ClaudeIntegrationGenerator,
)

# Load existing drift report
report_path = Path("examples/outputs/reports/drift_report_20260413_055839.json")
report_data = json.loads(report_path.read_text())

# Create drift report object
validation_issues = []
for issue_data in report_data["drift_details"]["validation_drift"]:
    validation_issues.append(
        ValidationDriftIssue(
            endpoint_id=issue_data["endpoint_id"],
            test_id=issue_data["test_id"],
            test_type=issue_data["test_type"],
            violated_constraint=issue_data["violated_constraint"],
            input_data=issue_data.get("input_data", {}),
            actual_status_code=issue_data["actual_status_code"],
            expected_status_code_range=issue_data["expected_status_code_range"],
            message=issue_data["message"],
            severity=issue_data["severity"],
        )
    )

drift_summary = DriftSummary(
    total_issues=report_data["drift_summary"]["total_issues"],
    by_severity=report_data["drift_summary"]["by_severity"],
    by_type=report_data["drift_summary"]["by_type"],
    affected_endpoints=report_data["drift_summary"]["affected_endpoints"],
)

drift_report = DriftReport(
    summary=drift_summary,
    validation_drift=validation_issues,
    contract_drift=[],
    behavioral_drift=[],
    api_url="http://localhost:8000",
    spec_source="examples/openapi/sample_users_api.yaml",
)

# Create config
config = Config()

# Generate Claude integration files
generator = ClaudeIntegrationGenerator(config)
spec_path = Path("examples/openapi/sample_users_api.yaml")

print("🤖 Generating Claude Code integration files...")
generated_files = generator.generate(
    drift_report=drift_report,
    analysis_result=None,
    spec_path=spec_path,
)

print(f"\n✅ Generated {len(generated_files)} files:")
for name, path in generated_files.items():
    print(f"   • {name}: {path}")
    print(f"     Size: {path.stat().st_size} bytes")

print("\n📁 Files created at repo root (where .git is)")
print(f"   Repo root detected: {generator._find_repo_root(spec_path)}")

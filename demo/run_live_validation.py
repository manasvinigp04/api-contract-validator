#!/usr/bin/env python3
"""
Run ACV validation against live mock APIs
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import requests

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from api_contract_validator.input.openapi.parser import OpenAPIParser
from api_contract_validator.generation.test_generator import MasterTestGenerator
from api_contract_validator.execution.runner.executor import TestExecutor
from api_contract_validator.config.models import ACVConfig

def validate_api(spec_path: Path, api_url: str, output_dir: Path):
    """Run validation against live API"""

    print(f"\n{'='*60}")
    print(f"Validating: {spec_path.name}")
    print(f"API URL: {api_url}")
    print(f"{'='*60}\n")

    try:
        # Check if API is reachable
        print(f"🔍 Checking API availability...")
        try:
            response = requests.get(api_url.rstrip('/') + '/products', timeout=5)
            print(f"✓ API is reachable (Status: {response.status_code})")
        except Exception as e:
            print(f"❌ Cannot reach API: {e}")
            return False

        # Parse specification
        print(f"\n📖 Parsing OpenAPI specification...")
        parser = OpenAPIParser()
        spec = parser.parse_file(spec_path)
        print(f"✓ Parsed {len(spec.endpoints)} endpoints")

        # Generate test cases
        print(f"\n🧪 Generating test cases...")
        config = ACVConfig()
        config.test_generation.generate_valid = True
        config.test_generation.generate_invalid = True
        config.test_generation.generate_boundary = True
        config.test_generation.max_tests_per_endpoint = 10

        generator = MasterTestGenerator(config)
        test_suite = generator.generate_test_suite(spec)

        valid_count = sum(1 for tc in test_suite.test_cases if tc.test_type == "VALID")
        invalid_count = sum(1 for tc in test_suite.test_cases if tc.test_type == "INVALID")
        boundary_count = sum(1 for tc in test_suite.test_cases if tc.test_type == "BOUNDARY")

        print(f"✓ Generated {len(test_suite.test_cases)} test cases")
        print(f"  - Valid: {valid_count}")
        print(f"  - Invalid: {invalid_count}")
        print(f"  - Boundary: {boundary_count}")

        # Execute tests
        print(f"\n🚀 Executing tests against {api_url}...")
        executor = TestExecutor(api_url)
        results = executor.execute_tests_sync(test_suite.test_cases[:50])  # Limit for demo

        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed)

        print(f"✓ Executed {len(results)} tests")
        print(f"  - Passed: {passed}")
        print(f"  - Failed: {failed}")

        # Analyze results for drift
        print(f"\n🔍 Analyzing for drift...")

        contract_drift = []
        validation_drift = []

        for result in results:
            if not result.passed:
                if result.test_case.test_type == "VALID":
                    # Valid test failed = contract drift
                    contract_drift.append({
                        "endpoint": f"{result.test_case.endpoint.method} {result.test_case.endpoint.path}",
                        "issue": result.failure_reason or "Response doesn't match spec",
                        "expected_status": result.test_case.expected_response_status,
                        "actual_status": result.response_status_code if hasattr(result, 'response_status_code') else None
                    })
                elif result.test_case.test_type == "INVALID":
                    # Invalid test passed = validation drift
                    validation_drift.append({
                        "endpoint": f"{result.test_case.endpoint.method} {result.test_case.endpoint.path}",
                        "issue": "API accepted invalid input",
                        "test_description": result.test_case.description
                    })

        print(f"\n📊 Drift Summary:")
        print(f"  - Contract Drift: {len(contract_drift)} issues")
        print(f"  - Validation Drift: {len(validation_drift)} issues")

        # Generate report
        output_dir.mkdir(parents=True, exist_ok=True)

        report_file = output_dir / f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        with open(report_file, 'w') as f:
            f.write(f"# API Validation Report\n\n")
            f.write(f"**API:** {spec.info.get('title', 'N/A')}\n")
            f.write(f"**URL:** {api_url}\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write(f"---\n\n")

            f.write(f"## Test Execution Summary\n\n")
            f.write(f"- **Total Tests:** {len(results)}\n")
            f.write(f"- **Passed:** {passed}\n")
            f.write(f"- **Failed:** {failed}\n")
            f.write(f"- **Pass Rate:** {passed/len(results)*100:.1f}%\n\n")

            f.write(f"### Test Case Breakdown\n\n")
            f.write(f"| Type | Generated | Executed |\n")
            f.write(f"|------|-----------|----------|\n")
            f.write(f"| Valid | {valid_count} | {sum(1 for r in results if r.test_case.test_type == 'VALID')} |\n")
            f.write(f"| Invalid | {invalid_count} | {sum(1 for r in results if r.test_case.test_type == 'INVALID')} |\n")
            f.write(f"| Boundary | {boundary_count} | {sum(1 for r in results if r.test_case.test_type == 'BOUNDARY')} |\n\n")

            f.write(f"---\n\n")

            f.write(f"## Drift Detection Results\n\n")

            if contract_drift:
                f.write(f"### 📋 Contract Drift ({len(contract_drift)} issues)\n\n")
                f.write(f"API responses don't match OpenAPI specification:\n\n")
                for i, issue in enumerate(contract_drift[:10], 1):
                    f.write(f"#### Issue {i}: {issue['endpoint']}\n\n")
                    f.write(f"- **Problem:** {issue['issue']}\n")
                    f.write(f"- **Expected Status:** {issue['expected_status']}\n")
                    if issue['actual_status']:
                        f.write(f"- **Actual Status:** {issue['actual_status']}\n")
                    f.write(f"\n")
            else:
                f.write(f"### ✅ Contract Drift\n\nNo contract drift issues detected.\n\n")

            if validation_drift:
                f.write(f"### ⚠️ Validation Drift ({len(validation_drift)} issues)\n\n")
                f.write(f"API accepts invalid inputs that should be rejected:\n\n")
                for i, issue in enumerate(validation_drift[:10], 1):
                    f.write(f"#### Issue {i}: {issue['endpoint']}\n\n")
                    f.write(f"- **Problem:** {issue['issue']}\n")
                    f.write(f"- **Test:** {issue['test_description']}\n")
                    f.write(f"\n")
            else:
                f.write(f"### ✅ Validation Drift\n\nNo validation drift issues detected.\n\n")

            f.write(f"---\n\n")
            f.write(f"## Recommendations\n\n")

            if contract_drift:
                f.write(f"### Fix Contract Drift\n\n")
                f.write(f"1. Review response schemas in OpenAPI spec\n")
                f.write(f"2. Ensure API returns all required fields\n")
                f.write(f"3. Check for type mismatches (string vs number)\n")
                f.write(f"4. Remove extra fields not in spec\n\n")

            if validation_drift:
                f.write(f"### Fix Validation Drift\n\n")
                f.write(f"1. Add input validation middleware\n")
                f.write(f"2. Validate request schemas before processing\n")
                f.write(f"3. Return 400/422 for invalid inputs\n")
                f.write(f"4. Use framework validation (e.g., Pydantic for FastAPI)\n\n")

            f.write(f"---\n\n")
            f.write(f"*Generated by API Contract Validator*\n")

        print(f"\n📄 Report saved: {report_file}")

        # Save JSON summary
        summary_file = output_dir / f"validation_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, 'w') as f:
            json.dump({
                "api": api_url,
                "spec": str(spec_path.name),
                "timestamp": datetime.now().isoformat(),
                "test_summary": {
                    "total": len(results),
                    "passed": passed,
                    "failed": failed,
                    "pass_rate": passed/len(results)*100
                },
                "drift_summary": {
                    "contract_drift": len(contract_drift),
                    "validation_drift": len(validation_drift)
                }
            }, f, indent=2)

        print(f"💾 JSON summary: {summary_file}")

        print(f"\n✅ Validation complete!\n")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run validation on demo APIs"""

    demo_dir = Path(__file__).parent
    specs_dir = demo_dir / "specs"
    outputs_dir = demo_dir / "outputs"

    print("\n" + "="*60)
    print("API Contract Validator - Live Validation")
    print("="*60)

    # Validate E-Commerce API
    ecommerce_spec = specs_dir / "e-commerce-api.yaml"
    ecommerce_output = outputs_dir / "ecommerce"

    print("\n🛒 E-Commerce API Validation")
    print("="*60)

    if ecommerce_spec.exists():
        success1 = validate_api(
            ecommerce_spec,
            "http://localhost:8080/v2",
            ecommerce_output
        )
    else:
        print(f"❌ Spec not found: {ecommerce_spec}")
        success1 = False

    print("\n" + "="*60)
    print("VALIDATION COMPLETE")
    print("="*60)

    if success1:
        print(f"\n✅ E-Commerce API validated successfully")
        print(f"   Reports: {ecommerce_output}/")

    print(f"\n📂 View reports:")
    print(f"   cat {ecommerce_output}/validation_report_*.md")
    print()

    return success1


if __name__ == "__main__":
    sys.exit(0 if main() else 1)

#!/usr/bin/env python3
"""
Demo Validation Script - Direct ACV Testing
Tests the OpenAPI specs without requiring mock servers

This script validates the OpenAPI specifications themselves and generates
comprehensive test cases to demonstrate ACV capabilities.
"""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from api_contract_validator.input.openapi.parser import OpenAPIParser
from api_contract_validator.generation.test_generator import MasterTestGenerator
from api_contract_validator.config.models import ACVConfig

def validate_spec(spec_path: Path, output_dir: Path):
    """Validate an OpenAPI spec and generate test cases"""

    print(f"\n{'='*60}")
    print(f"Validating: {spec_path.name}")
    print(f"{'='*60}\n")

    try:
        # Parse specification
        print("📖 Parsing OpenAPI specification...")
        parser = OpenAPIParser()
        spec = parser.parse_file(spec_path)

        print(f"✓ Parsed successfully")
        print(f"  - Endpoints: {len(spec.endpoints)}")
        print(f"  - Schemas: {len(spec.schemas)}")

        # List endpoints
        print(f"\n📋 Endpoints:")
        for endpoint in spec.endpoints[:10]:  # Show first 10
            print(f"  - {endpoint.method:6} {endpoint.path}")
        if len(spec.endpoints) > 10:
            print(f"  ... and {len(spec.endpoints) - 10} more")

        # Generate test cases
        print(f"\n🧪 Generating test cases...")

        config = ACVConfig()
        config.test_generation.generate_valid = True
        config.test_generation.generate_invalid = True
        config.test_generation.generate_boundary = True
        config.test_generation.max_tests_per_endpoint = 20

        generator = MasterTestGenerator(config)
        test_suite = generator.generate_test_suite(spec)

        print(f"✓ Generated {len(test_suite.test_cases)} test cases")

        # Count by type
        valid_count = sum(1 for tc in test_suite.test_cases if tc.test_type == "VALID")
        invalid_count = sum(1 for tc in test_suite.test_cases if tc.test_type == "INVALID")
        boundary_count = sum(1 for tc in test_suite.test_cases if tc.test_type == "BOUNDARY")

        print(f"  - Valid: {valid_count}")
        print(f"  - Invalid: {invalid_count}")
        print(f"  - Boundary: {boundary_count}")

        # Save test cases
        output_dir.mkdir(parents=True, exist_ok=True)

        test_cases_file = output_dir / "generated_test_cases.json"
        test_cases_data = []

        for tc in test_suite.test_cases[:50]:  # Save first 50 for demo
            test_cases_data.append({
                "endpoint": f"{tc.endpoint.method} {tc.endpoint.path}",
                "test_type": tc.test_type,
                "expected_status": tc.expected_response_status,
                "payload": tc.request_body,
                "description": tc.description
            })

        with open(test_cases_file, 'w') as f:
            json.dump(test_cases_data, f, indent=2)

        print(f"\n💾 Saved test cases to: {test_cases_file}")

        # Generate summary report
        summary_file = output_dir / "validation_summary.md"
        with open(summary_file, 'w') as f:
            f.write(f"# Validation Summary: {spec_path.name}\n\n")
            f.write(f"**Generated:** {Path(summary_file).stat().st_mtime}\n\n")
            f.write(f"## Specification Overview\n\n")
            f.write(f"- **Endpoints:** {len(spec.endpoints)}\n")
            f.write(f"- **Schemas:** {len(spec.schemas)}\n")
            f.write(f"- **Test Cases Generated:** {len(test_suite.test_cases)}\n\n")

            f.write(f"### Test Case Breakdown\n\n")
            f.write(f"| Type | Count |\n")
            f.write(f"|------|-------|\n")
            f.write(f"| Valid | {valid_count} |\n")
            f.write(f"| Invalid | {invalid_count} |\n")
            f.write(f"| Boundary | {boundary_count} |\n\n")

            f.write(f"### Endpoints\n\n")
            for endpoint in spec.endpoints:
                f.write(f"- **{endpoint.method}** `{endpoint.path}`\n")
                if endpoint.summary:
                    f.write(f"  - {endpoint.summary}\n")

            f.write(f"\n### Sample Test Cases\n\n")
            for i, tc in enumerate(test_suite.test_cases[:10], 1):
                f.write(f"#### Test {i}: {tc.test_type}\n\n")
                f.write(f"- **Endpoint:** {tc.endpoint.method} {tc.endpoint.path}\n")
                f.write(f"- **Expected Status:** {tc.expected_response_status}\n")
                f.write(f"- **Description:** {tc.description}\n")
                if tc.request_body:
                    f.write(f"- **Payload:**\n```json\n{json.dumps(tc.request_body, indent=2)}\n```\n")
                f.write(f"\n")

            f.write(f"\n## Next Steps\n\n")
            f.write(f"To run validation against a live API:\n\n")
            f.write(f"```bash\n")
            f.write(f"acv validate {spec_path} --api-url http://localhost:PORT\n")
            f.write(f"```\n\n")

        print(f"📄 Saved summary report to: {summary_file}")

        print(f"\n✅ Validation complete for {spec_path.name}")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run validation on demo specs"""

    demo_dir = Path(__file__).parent
    specs_dir = demo_dir / "specs"
    outputs_dir = demo_dir / "outputs"

    print("\n" + "="*60)
    print("API Contract Validator - Demo Validation")
    print("="*60)

    # Validate E-Commerce API
    ecommerce_spec = specs_dir / "e-commerce-api.yaml"
    ecommerce_output = outputs_dir / "ecommerce"

    if ecommerce_spec.exists():
        success1 = validate_spec(ecommerce_spec, ecommerce_output)
    else:
        print(f"❌ Spec not found: {ecommerce_spec}")
        success1 = False

    # Validate Healthcare API
    healthcare_spec = specs_dir / "healthcare-api.yaml"
    healthcare_output = outputs_dir / "healthcare"

    if healthcare_spec.exists():
        success2 = validate_spec(healthcare_spec, healthcare_output)
    else:
        print(f"❌ Spec not found: {healthcare_spec}")
        success2 = False

    # Final summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)

    if success1:
        print(f"✅ E-Commerce API: Success")
        print(f"   Reports: {ecommerce_output}")
    else:
        print(f"❌ E-Commerce API: Failed")

    if success2:
        print(f"✅ Healthcare API: Success")
        print(f"   Reports: {healthcare_output}")
    else:
        print(f"❌ Healthcare API: Failed")

    print("\n" + "="*60)
    print("\nView reports:")
    print(f"  cat {ecommerce_output}/validation_summary.md")
    print(f"  cat {healthcare_output}/validation_summary.md")
    print()

    return success1 and success2


if __name__ == "__main__":
    sys.exit(0 if main() else 1)

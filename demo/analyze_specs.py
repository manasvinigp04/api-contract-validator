#!/usr/bin/env python3
"""
Simple Demo Validation - Spec Analysis Only
Analyzes OpenAPI specs and generates reports without test execution
"""

import sys
import json
import yaml
from pathlib import Path
from datetime import datetime

def analyze_spec(spec_path: Path, output_dir: Path):
    """Analyze OpenAPI spec and generate summary"""

    print(f"\n{'='*60}")
    print(f"Analyzing: {spec_path.name}")
    print(f"{'='*60}\n")

    try:
        # Load spec
        with open(spec_path) as f:
            spec = yaml.safe_load(f)

        # Extract information
        info = spec.get('info', {})
        paths = spec.get('paths', {})
        components = spec.get('components', {})
        schemas = components.get('schemas', {})

        # Count endpoints
        endpoint_count = 0
        endpoints_by_method = {}

        for path, methods in paths.items():
            for method in ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']:
                if method in methods:
                    endpoint_count += 1
                    endpoints_by_method[method.upper()] = endpoints_by_method.get(method.upper(), 0) + 1

        print(f"✓ Specification loaded successfully")
        print(f"  - Title: {info.get('title', 'N/A')}")
        print(f"  - Version: {info.get('version', 'N/A')}")
        print(f"  - Endpoints: {endpoint_count}")
        print(f"  - Schemas: {len(schemas)}")

        print(f"\n📋 Endpoints by method:")
        for method in sorted(endpoints_by_method.keys()):
            print(f"  - {method:6}: {endpoints_by_method[method]}")

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate detailed report
        report_file = output_dir / "spec_analysis.md"

        with open(report_file, 'w') as f:
            f.write(f"# API Specification Analysis\n\n")
            f.write(f"**API:** {info.get('title', 'N/A')}\n\n")
            f.write(f"**Version:** {info.get('version', 'N/A')}\n\n")
            f.write(f"**Description:** {info.get('description', 'N/A')}\n\n")
            f.write(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write(f"---\n\n")

            f.write(f"## Overview\n\n")
            f.write(f"- **Total Endpoints:** {endpoint_count}\n")
            f.write(f"- **Schemas Defined:** {len(schemas)}\n")
            f.write(f"- **Spec File:** `{spec_path.name}`\n\n")

            f.write(f"### Endpoints by HTTP Method\n\n")
            f.write(f"| Method | Count |\n")
            f.write(f"|--------|-------|\n")
            for method in sorted(endpoints_by_method.keys()):
                f.write(f"| {method} | {endpoints_by_method[method]} |\n")
            f.write(f"\n")

            f.write(f"## API Endpoints\n\n")

            for path, methods in sorted(paths.items()):
                f.write(f"### `{path}`\n\n")

                for method in ['get', 'post', 'put', 'patch', 'delete']:
                    if method in methods:
                        endpoint = methods[method]
                        f.write(f"#### {method.upper()}\n\n")

                        if 'summary' in endpoint:
                            f.write(f"**Summary:** {endpoint['summary']}\n\n")

                        if 'description' in endpoint:
                            f.write(f"**Description:** {endpoint['description']}\n\n")

                        # Parameters
                        if 'parameters' in endpoint:
                            f.write(f"**Parameters:**\n")
                            for param in endpoint['parameters']:
                                required = " (required)" if param.get('required') else ""
                                param_schema = param.get('schema', {})
                                param_type = param_schema.get('type', 'unknown')
                                f.write(f"- `{param['name']}` ({param['in']}) - {param_type}{required}\n")
                            f.write(f"\n")

                        # Request body
                        if 'requestBody' in endpoint:
                            f.write(f"**Request Body:** Required\n\n")

                        # Responses
                        if 'responses' in endpoint:
                            f.write(f"**Responses:**\n")
                            for status, response in endpoint['responses'].items():
                                f.write(f"- `{status}`: {response.get('description', 'N/A')}\n")
                            f.write(f"\n")

                        f.write(f"---\n\n")

            f.write(f"## Data Schemas\n\n")

            for schema_name, schema_def in sorted(schemas.items()):
                f.write(f"### {schema_name}\n\n")

                if 'description' in schema_def:
                    f.write(f"{schema_def['description']}\n\n")

                if 'properties' in schema_def:
                    required_fields = schema_def.get('required', [])
                    f.write(f"**Properties:**\n\n")

                    for prop_name, prop_def in sorted(schema_def['properties'].items()):
                        is_required = " ✓" if prop_name in required_fields else ""
                        prop_type = prop_def.get('type', 'object')

                        constraints = []
                        if 'minLength' in prop_def:
                            constraints.append(f"min: {prop_def['minLength']}")
                        if 'maxLength' in prop_def:
                            constraints.append(f"max: {prop_def['maxLength']}")
                        if 'minimum' in prop_def:
                            constraints.append(f"min: {prop_def['minimum']}")
                        if 'maximum' in prop_def:
                            constraints.append(f"max: {prop_def['maximum']}")
                        if 'pattern' in prop_def:
                            constraints.append(f"pattern: `{prop_def['pattern']}`")
                        if 'enum' in prop_def:
                            constraints.append(f"enum: {', '.join(map(str, prop_def['enum']))}")

                        constraint_str = f" ({', '.join(constraints)})" if constraints else ""

                        f.write(f"- `{prop_name}`: {prop_type}{constraint_str}{is_required}\n")

                    f.write(f"\n")

            f.write(f"## Test Scenarios (Manual)\n\n")
            f.write(f"Based on this specification, you should test:\n\n")
            f.write(f"### Contract Validation\n")
            f.write(f"- ✅ All endpoints return correct status codes\n")
            f.write(f"- ✅ Response schemas match specification\n")
            f.write(f"- ✅ Required fields are present\n")
            f.write(f"- ✅ Field types match (string, integer, boolean)\n\n")

            f.write(f"### Input Validation\n")
            f.write(f"- ✅ Invalid input rejected with 400/422\n")
            f.write(f"- ✅ Missing required fields rejected\n")
            f.write(f"- ✅ Type validation enforced\n")
            f.write(f"- ✅ Constraint validation (min/max, pattern, enum)\n\n")

            f.write(f"### Edge Cases\n")
            f.write(f"- ✅ Boundary values (min/max lengths, ranges)\n")
            f.write(f"- ✅ Empty arrays and null values\n")
            f.write(f"- ✅ Very long strings\n")
            f.write(f"- ✅ Special characters\n\n")

            f.write(f"---\n\n")
            f.write(f"*To run automated validation with ACV:*\n\n")
            f.write(f"```bash\n")
            f.write(f"acv validate {spec_path} --api-url http://localhost:PORT\n")
            f.write(f"```\n")

        print(f"📄 Generated analysis report: {report_file}")

        # Save spec info as JSON
        info_file = output_dir / "spec_info.json"
        with open(info_file, 'w') as f:
            json.dump({
                "spec_file": str(spec_path.name),
                "title": info.get('title'),
                "version": info.get('version'),
                "endpoint_count": endpoint_count,
                "schema_count": len(schemas),
                "endpoints_by_method": endpoints_by_method,
                "analyzed_at": datetime.now().isoformat()
            }, f, indent=2)

        print(f"💾 Saved spec info: {info_file}")

        print(f"\n✅ Analysis complete for {spec_path.name}\n")

        return True

    except Exception as e:
        print(f"\n❌ Error analyzing {spec_path.name}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run analysis on demo specs"""

    demo_dir = Path(__file__).parent
    specs_dir = demo_dir / "specs"
    outputs_dir = demo_dir / "outputs"

    print("\n" + "="*60)
    print("API Contract Validator - Demo Spec Analysis")
    print("="*60)

    results = {}

    # Analyze E-Commerce API
    ecommerce_spec = specs_dir / "e-commerce-api.yaml"
    ecommerce_output = outputs_dir / "ecommerce"

    if ecommerce_spec.exists():
        results['ecommerce'] = analyze_spec(ecommerce_spec, ecommerce_output)
    else:
        print(f"❌ Spec not found: {ecommerce_spec}")
        results['ecommerce'] = False

    # Analyze Healthcare API
    healthcare_spec = specs_dir / "healthcare-api.yaml"
    healthcare_output = outputs_dir / "healthcare"

    if healthcare_spec.exists():
        results['healthcare'] = analyze_spec(healthcare_spec, healthcare_output)
    else:
        print(f"❌ Spec not found: {healthcare_spec}")
        results['healthcare'] = False

    # Final summary
    print("=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    print()

    if results.get('ecommerce'):
        print(f"✅ E-Commerce API")
        print(f"   📄 Report: {ecommerce_output}/spec_analysis.md")
        print(f"   💾 Info: {ecommerce_output}/spec_info.json")
    else:
        print(f"❌ E-Commerce API: Failed")

    print()

    if results.get('healthcare'):
        print(f"✅ Healthcare API")
        print(f"   📄 Report: {healthcare_output}/spec_analysis.md")
        print(f"   💾 Info: {healthcare_output}/spec_info.json")
    else:
        print(f"❌ Healthcare API: Failed")

    print()
    print("=" * 60)
    print("\nNext steps:")
    print("1. Start mock API servers")
    print("2. Run: acv validate demo/specs/e-commerce-api.yaml --api-url http://localhost:8080/v2")
    print("3. View drift reports in demo/outputs/")
    print()

    return all(results.values())


if __name__ == "__main__":
    sys.exit(0 if main() else 1)

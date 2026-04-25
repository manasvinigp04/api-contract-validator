#!/usr/bin/env python3
"""
Simple Live Validation - Manual Test Execution
Tests actual API responses against OpenAPI spec
"""

import sys
import json
import requests
from pathlib import Path
from datetime import datetime
import yaml

def test_endpoint(base_url, method, path, expected_status=200):
    """Test a single endpoint"""
    url = f"{base_url.rstrip('/')}{path}"

    try:
        if method == 'GET':
            response = requests.get(url, timeout=10)
        elif method == 'POST':
            # Simple test data
            if 'products' in path:
                data = {
                    "name": "Test Product",
                    "sku": "SKU-TEST01",
                    "price": 99.99,
                    "category": "electronics"
                }
            elif 'cart' in path:
                data = {
                    "productId": "PROD0001",
                    "quantity": 1
                }
            else:
                data = {}
            response = requests.post(url, json=data, timeout=10)
        else:
            return None

        return {
            "method": method,
            "path": path,
            "status": response.status_code,
            "expected": expected_status,
            "passed": response.status_code == expected_status,
            "response": response.json() if response.headers.get('content-type', '').startswith('application/json') else None
        }

    except Exception as e:
        return {
            "method": method,
            "path": path,
            "error": str(e),
            "passed": False
        }


def validate_api_simple(spec_path: Path, api_url: str, output_dir: Path):
    """Simple validation against live API"""

    print(f"\n{'='*60}")
    print(f"Simple Validation: {spec_path.name}")
    print(f"API URL: {api_url}")
    print(f"{'='*60}\n")

    # Load spec
    with open(spec_path) as f:
        spec = yaml.safe_load(f)

    info = spec.get('info', {})
    paths = spec.get('paths', {})

    print(f"✓ Loaded spec: {info.get('title')}")
    print(f"✓ Found {len(paths)} endpoint paths\n")

    # Test endpoints
    print(f"🚀 Testing endpoints...\n")

    results = []

    # Test GET endpoints
    for path, methods in paths.items():
        if 'get' in methods:
            result = test_endpoint(api_url, 'GET', path, 200)
            if result:
                results.append(result)
                status_icon = "✅" if result['passed'] else "❌"
                print(f"{status_icon} GET {path} - {result.get('status', 'ERROR')}")

   # Test a few POST endpoints
    for path in ['/products', '/cart']:
        if path in paths and 'post' in paths[path]:
            result = test_endpoint(api_url, 'POST', path, 201)
            if result:
                results.append(result)
                status_icon = "✅" if result['passed'] else "❌"
                print(f"{status_icon} POST {path} - {result.get('status', 'ERROR')}")

    passed = sum(1 for r in results if r.get('passed'))
    failed = len(results) - passed

    print(f"\n📊 Test Results:")
    print(f"  - Total: {len(results)}")
    print(f"  - Passed: {passed}")
    print(f"  - Failed: {failed}")

    # Analyze responses for drift
    print(f"\n🔍 Analyzing responses for drift...\n")

    drift_issues = []

    for result in results:
        if result.get('response'):
            response = result['response']

            # Check for common drift patterns
            if isinstance(response, dict):
                # Check for internal fields
                if 'internal_id' in response or 'debug_info' in response:
                    drift_issues.append({
                        "type": "contract_drift",
                        "endpoint": f"{result['method']} {result['path']}",
                        "issue": "Response contains internal fields",
                        "fields": [k for k in response.keys() if 'internal' in k or 'debug' in k]
                    })

                # Check for type mismatches in known fields
                if 'data' in response and isinstance(response['data'], list):
                    for item in response['data']:
                        if 'price' in item and isinstance(item['price'], str):
                            drift_issues.append({
                                "type": "contract_drift",
                                "endpoint": f"{result['method']} {result['path']}",
                                "issue": "Type mismatch: price should be number, got string",
                                "example": item['price']
                            })
                            break  # Report once per endpoint

            # Check status code issues
            if not result.get('passed'):
                drift_issues.append({
                    "type": "contract_drift",
                    "endpoint": f"{result['method']} {result['path']}",
                    "issue": f"Wrong status code: expected {result.get('expected')}, got {result.get('status')}",
                })

    print(f"📋 Drift Issues Found: {len(drift_issues)}\n")

    for i, issue in enumerate(drift_issues, 1):
        print(f"{i}. [{issue['type']}] {issue['endpoint']}")
        print(f"   {issue['issue']}")
        if 'fields' in issue:
            print(f"   Fields: {', '.join(issue['fields'])}")
        if 'example' in issue:
            print(f"   Example: {issue['example']}")
        print()

    # Generate report
    output_dir.mkdir(parents=True, exist_ok=True)

    report_file = output_dir / f"live_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

    with open(report_file, 'w') as f:
        f.write(f"# Live API Validation Report\n\n")
        f.write(f"**API:** {info.get('title')}\n")
        f.write(f"**Version:** {info.get('version')}\n")
        f.write(f"**URL:** {api_url}\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write(f"---\n\n")

        f.write(f"## Test Execution Summary\n\n")
        f.write(f"- **Endpoints Tested:** {len(results)}\n")
        f.write(f"- **Passed:** {passed}\n")
        f.write(f"- **Failed:** {failed}\n")
        f.write(f"- **Pass Rate:** {passed/len(results)*100:.1f}%\n\n")

        f.write(f"---\n\n")

        f.write(f"## Drift Issues ({len(drift_issues)} found)\n\n")

        if drift_issues:
            for i, issue in enumerate(drift_issues, 1):
                f.write(f"### Issue {i}: {issue['endpoint']}\n\n")
                f.write(f"**Type:** `{issue['type']}`\n\n")
                f.write(f"**Problem:** {issue['issue']}\n\n")

                if 'fields' in issue:
                    f.write(f"**Fields:** {', '.join(f'`{f}`' for f in issue['fields'])}\n\n")

                if 'example' in issue:
                    f.write(f"**Example Value:** `{issue['example']}`\n\n")

                f.write(f"---\n\n")
        else:
            f.write(f"✅ No drift issues detected!\n\n")

        f.write(f"## Sample Responses\n\n")

        for result in results[:5]:
            if result.get('response'):
                f.write(f"### {result['method']} {result['path']}\n\n")
                f.write(f"**Status:** {result.get('status')}\n\n")
                f.write(f"```json\n")
                f.write(json.dumps(result['response'], indent=2))
                f.write(f"\n```\n\n")

        f.write(f"---\n\n")
        f.write(f"*Generated by API Contract Validator (Simple Mode)*\n")

    print(f"📄 Report saved: {report_file}\n")

    return True


def main():
    """Run simple validation"""

    demo_dir = Path(__file__).parent
    specs_dir = demo_dir / "specs"
    outputs_dir = demo_dir / "outputs"

    print("\n" + "="*60)
    print("API Contract Validator - Live Validation (Simple Mode)")
    print("="*60)

    # Validate E-Commerce API
    ecommerce_spec = specs_dir / "e-commerce-api.yaml"
    ecommerce_output = outputs_dir / "ecommerce"

    success = validate_api_simple(
        ecommerce_spec,
        "http://localhost:8080/v2",
        ecommerce_output
    )

    print("="*60)
    print("VALIDATION COMPLETE")
    print("="*60)

    if success:
        print(f"\n✅ Validation complete")
        print(f"📂 Reports: {ecommerce_output}/\n")

    return success


if __name__ == "__main__":
    sys.exit(0 if main() else 1)

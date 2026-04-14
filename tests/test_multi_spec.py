#!/usr/bin/env python3
"""Test multi-spec parsing"""
from pathlib import Path
from api_contract_validator.input.openapi.parser import OpenAPIParser

# Test with your actual repo
spec_dir = Path("/Users/I764709/rage-proxy-inference/src/spec")

if spec_dir.exists():
    print(f"📁 Testing multi-spec parsing on: {spec_dir}")
    print(f"   Found: {len(list(spec_dir.glob('*.yaml')))} YAML files\n")

    parser = OpenAPIParser()

    try:
        merged_spec = parser.parse_file(spec_dir)

        print(f"✅ SUCCESS!")
        print(f"   Merged API Title: {merged_spec.metadata.title}")
        print(f"   Total Endpoints: {len(merged_spec.endpoints)}")
        print(f"   Total Schemas: {len(merged_spec.schemas)}")
        print(f"\n📋 Endpoints by Method:")

        from collections import Counter
        methods = Counter(e.method.value for e in merged_spec.endpoints)
        for method, count in methods.most_common():
            print(f"   {method}: {count}")

        print(f"\n🔗 Sample Endpoints:")
        for endpoint in merged_spec.endpoints[:10]:
            print(f"   {endpoint.method.value:6} {endpoint.path}")

        if len(merged_spec.endpoints) > 10:
            print(f"   ... and {len(merged_spec.endpoints) - 10} more")

    except Exception as e:
        print(f"❌ FAILED: {e}")
else:
    print(f"❌ Directory not found: {spec_dir}")

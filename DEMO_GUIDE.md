# API Contract Validator - Demo Guide

This guide shows you how to demo all the key features of the API Contract Validator.

## Prerequisites

```bash
# Ensure you're in the project directory and virtual environment is activated
cd /Users/I764709/api-contract-validator
source .venv/bin/activate

# Verify installation
acv --version
```

---

## Demo Option 1: Quick CLI Demo (Recommended for First Time)

This demos the validator against a mock API to show drift detection in action.

### Step 1: Start the Mock API

Open a **new terminal window** and run:

```bash
cd /Users/I764709/api-contract-validator
source .venv/bin/activate
python examples/mock_apis/users_api.py
```

This starts a Flask server at `http://localhost:8000` with intentionally weak validation to demonstrate drift detection.

### Step 2: Parse the OpenAPI Specification

In your **main terminal**, parse the spec to see the API structure:

```bash
acv parse examples/openapi/sample_users_api.yaml
```

**What you'll see:**
- API metadata (title, version)
- List of 3 endpoints (GET /users, POST /users, GET /users/{userId})
- Parameters and response codes

Try different formats:
```bash
acv parse examples/openapi/sample_users_api.yaml --format tree
acv parse examples/openapi/sample_users_api.yaml --format json
```

### Step 3: Generate Test Cases

Generate intelligent test cases without running them:

```bash
acv generate-tests examples/openapi/sample_users_api.yaml -o tests/demo_tests.json
```

**What you'll see:**
- Valid tests (happy paths)
- Invalid tests (missing fields, wrong types)
- Boundary tests (min/max values, edge cases)
- Risk-based prioritization

View the generated tests:
```bash
cat tests/demo_tests.json | jq '.test_cases[0]'  # View first test
```

### Step 4: Run Full Validation (The Main Feature!)

Now validate the running API against the specification:

```bash
acv validate examples/openapi/sample_users_api.yaml \
  --api-url http://localhost:8000 \
  --parallel 5 \
  --output ./demo-output
```

**What happens:**
1. ✅ Parses OpenAPI spec
2. ✅ Extracts contract rules
3. ✅ Generates ~17 test cases
4. ✅ Executes tests in parallel (5 workers)
5. ✅ Detects drift issues
6. ✅ Runs AI analysis (if `ANTHROPIC_API_KEY` is set)
7. ✅ Generates detailed reports

**Expected Output:**
```
✓ Executed 17 tests: 2 passed, 15 failed
✓ Detected 5 drift issues
⚠ 5 validation drift issues (boundary tests accepted when they should fail)
```

### Step 5: Review the Reports

Check the generated reports:

```bash
# View Markdown report
cat demo-output/drift_report_*.md

# View JSON report
cat demo-output/drift_report_*.json | jq '.summary'
```

**What the report shows:**
- Test execution statistics
- Drift issues by type (Contract, Validation, Behavioral)
- Severity levels (Critical, High, Medium, Low)
- Endpoint-specific analysis
- AI-powered recommendations (if enabled)

---

## Demo Option 2: REST API Server Demo

This shows how to use the validator as a web service.

### Step 1: Start the Validator API Server

```bash
uvicorn api_contract_validator.api.server:app --reload --port 9000
```

Server starts at: `http://localhost:9000`

### Step 2: Open Interactive API Docs

Open your browser to:
```
http://localhost:9000/docs
```

You'll see a Swagger UI with all available endpoints.

### Step 3: Test the Endpoints

**Health Check:**
```bash
curl http://localhost:9000/health | jq '.'
```

**Parse Specification:**
```bash
curl -X POST http://localhost:9000/parse \
  -F "spec_file=@examples/openapi/sample_users_api.yaml" | jq '.'
```

**Generate Tests:**
```bash
curl -X POST http://localhost:9000/generate-tests \
  -F "spec_file=@examples/openapi/sample_users_api.yaml" \
  -F 'request_data={"prioritize": true, "max_tests_per_endpoint": 20}' | jq '.total_tests'
```

**Run Validation (Async):**
```bash
# Start validation job (returns job_id)
JOB_ID=$(curl -s -X POST http://localhost:9000/validate \
  -F "spec_file=@examples/openapi/sample_users_api.yaml" \
  -F 'validation_request={"api_url": "http://localhost:8000", "parallel_workers": 10, "enable_ai_analysis": false}' | jq -r '.job_id')

echo "Job ID: $JOB_ID"

# Check status (repeat until completed)
curl http://localhost:9000/status/$JOB_ID | jq '.'

# Download report when completed
curl http://localhost:9000/report/$JOB_ID/json -o validation_report.json
curl http://localhost:9000/report/$JOB_ID/markdown -o validation_report.md
```

---

## Demo Option 3: Python Library Demo

Use the validator programmatically in Python.

### Create a demo script:

```python
# demo_library.py
from pathlib import Path
from api_contract_validator.input.openapi.parser import OpenAPIParser
from api_contract_validator.generation.test_generator import MasterTestGenerator
from api_contract_validator.execution.runner.executor import TestExecutor
from api_contract_validator.execution.collector.result_collector import ResultCollector
from api_contract_validator.schema.contract.constraint_extractor import ConstraintExtractor
from api_contract_validator.analysis.drift.detector import DriftDetector
from api_contract_validator.config.models import ExecutionConfig, DriftDetectionConfig

# 1. Parse specification
print("📄 Parsing specification...")
parser = OpenAPIParser()
spec = parser.parse_file(Path("examples/openapi/sample_users_api.yaml"))
print(f"   Found {len(spec.endpoints)} endpoints")

# 2. Extract contract
print("📋 Extracting contracts...")
extractor = ConstraintExtractor(spec)
contract = extractor.extract_contract()

# 3. Generate tests
print("🧪 Generating tests...")
generator = MasterTestGenerator()
test_suite = generator.generate_test_suite(spec)
print(f"   Generated {len(test_suite.test_cases)} test cases")

# 4. Execute tests
print("🚀 Executing tests...")
config = ExecutionConfig(parallel_workers=5, timeout_seconds=30)
executor = TestExecutor("http://localhost:8000", config)
results = executor.execute_tests_sync(test_suite.test_cases)

# 5. Collect results
collector = ResultCollector()
collector.add_results(results)
summary = collector.get_summary()
print(f"   ✓ {summary.passed} passed, ✗ {summary.failed} failed")

# 6. Detect drift
print("🔍 Detecting drift...")
drift_config = DriftDetectionConfig()
detector = DriftDetector(contract, drift_config)
drift_report = detector.detect_drift(summary)
print(f"   Found {drift_report.summary.total_issues} drift issues")

# Display results
print(f"\n📊 Results:")
print(f"   Contract Drift: {drift_report.summary.contract_drift_count}")
print(f"   Validation Drift: {drift_report.summary.validation_drift_count}")
print(f"   Behavioral Drift: {drift_report.summary.behavioral_drift_count}")
```

Run it:
```bash
python demo_library.py
```

---

## Demo Option 4: CI/CD Integration Demo

Show how to use in a GitHub Actions workflow:

```yaml
# .github/workflows/api-validation.yml
name: API Contract Validation

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install validator
        run: pip install api-contract-validator
      
      - name: Start mock API
        run: |
          python examples/mock_apis/users_api.py &
          sleep 5
      
      - name: Validate API
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          acv validate examples/openapi/sample_users_api.yaml \
            --api-url http://localhost:8000 \
            --format json \
            --output ./reports
      
      - name: Upload reports
        uses: actions/upload-artifact@v3
        with:
          name: validation-reports
          path: ./reports/
```

---

## Advanced Demo Features

### Enable AI Analysis

Set your Anthropic API key:
```bash
export ANTHROPIC_API_KEY="your-api-key"

acv validate examples/openapi/sample_users_api.yaml \
  --api-url http://localhost:8000 \
  --output ./reports
```

The AI analyzer will provide:
- Root cause analysis
- Remediation suggestions
- Impact assessments

### Custom Configuration

Create `config.yaml`:
```yaml
execution:
  parallel_workers: 20
  timeout_seconds: 60
  retry_attempts: 3

test_generation:
  generate_valid: true
  generate_invalid: true
  generate_boundary: true
  max_tests_per_endpoint: 100
  enable_prioritization: true

drift_detection:
  detect_contract_drift: true
  detect_validation_drift: true
  detect_behavioral_drift: true

ai_analysis:
  enabled: true
  model: "claude-3-5-sonnet-20241022"

reporting:
  output_directory: "./reports"
```

Run with config:
```bash
acv validate examples/openapi/sample_users_api.yaml \
  --api-url http://localhost:8000 \
  --config config.yaml
```

---

## Key Demo Talking Points

1. **Multi-dimensional Drift Detection**: Shows 3 types of drift (contract, validation, behavioral)
2. **Intelligent Test Generation**: Automatically creates valid, invalid, and boundary tests
3. **Parallel Execution**: Runs tests concurrently for speed
4. **AI-Powered Analysis**: Uses Claude API for root cause analysis
5. **Multiple Usage Modes**: CLI, REST API, or Python library
6. **Rich Reporting**: Markdown, JSON, and CLI formats
7. **CI/CD Ready**: Easy integration with GitHub Actions, GitLab CI, etc.

---

## Troubleshooting

**Mock API not responding:**
```bash
# Check if it's running
curl http://localhost:8000/users

# Restart it
pkill -f users_api.py
python examples/mock_apis/users_api.py
```

**CLI command not found:**
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall if needed
pip install -e .
```

**AI analysis not working:**
```bash
# Check if API key is set
echo $ANTHROPIC_API_KEY

# Disable AI if needed
acv validate ... --no-ai-analysis
```

---

## Clean Up

After demo:
```bash
# Stop mock API
pkill -f users_api.py

# Stop validator API (if running)
pkill -f uvicorn

# Remove demo outputs
rm -rf demo-output/ tests/demo_tests.json
```

---

## Next Steps

- Check `INTEGRATION_GUIDE.md` for detailed integration instructions
- Review `docs/USAGE_EXAMPLES.md` for more usage patterns
- See `docs/CI_CD_INTEGRATION.md` for CI/CD setup

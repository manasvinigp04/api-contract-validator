# Quick Start: Using ACV in Another Project

This guide shows you how to use this API Contract Validator repository as a **reusable library** in your other projects.

## Overview

This repository (`api-contract-validator`) contains the **ACV implementation**. Install it in any project to validate APIs against OpenAPI specifications with:
- Intelligent test generation (valid/invalid/boundary cases)
- Parallel test execution
- Multi-dimensional drift detection (contract/validation/behavioral)
- AI-powered analysis
- Rich reporting (Markdown/JSON/CLI)

## Step 1: Install ACV (Editable Mode)

In your project directory:

```bash
pip install -e /Users/I764709/api-contract-validator
```

✅ **Why `-e` flag?** Changes you make to ACV code are immediately available in your project—no reinstall needed!

## Step 2: Initialize ACV

```bash
acv init
```

This creates `acv_config.yaml` with interactive prompts. Example:

```
Path to OpenAPI spec: api/openapi.yaml
API base URL: http://localhost:8000
```

Or non-interactively:

```bash
acv init --spec-path api/openapi.yaml --api-url http://localhost:8000
```

## Step 3: Customize `acv_config.yaml`

Edit the generated file to match your project:

```yaml
project:
  spec:
    path: "api/openapi.yaml"  # Your OpenAPI spec
  output:
    reports: "reports/acv"    # Where to save reports

api:
  base_url: "http://localhost:8000"
  environments:
    local: "http://localhost:8000"
    dev: "https://dev-api.yourcompany.com"
    staging: "https://staging-api.yourcompany.com"

execution:
  parallel_workers: 10
  timeout_seconds: 30
```

## Step 4: Run ACV

```bash
# Start your API first
uvicorn your_app:app --reload  # or your start command

# In another terminal
acv validate
```

That's it! ACV will:
1. ✅ Read your OpenAPI spec
2. ✅ Generate smart test cases
3. ✅ Execute tests in parallel
4. ✅ Detect drift issues
5. ✅ Generate reports in `reports/acv/`

## Common Commands

```bash
# Validate against different environments
acv validate --env dev
acv validate --env staging

# Parse spec only (no validation)
acv parse

# Generate tests without running them
acv generate-tests

# Override parallel workers
acv validate --parallel 20

# Disable AI analysis
acv validate --no-ai-analysis

# Use custom config file
acv validate --config my-config.yaml
```

## Testing ACV Changes

1. **Make changes in ACV repo:**
   ```bash
   cd /Users/I764709/api-contract-validator
   # Edit files, add features
   ```

2. **Test immediately in your project:**
   ```bash
   cd /path/to/your-project
   acv validate  # Uses latest ACV code automatically!
   ```

3. **No reinstall needed!** The `-e` flag makes it work instantly.

## Project Structure Example

```
your-project/
├── acv_config.yaml          # Created by 'acv init'
├── requirements.txt         # Add: -e /path/to/api-contract-validator
├── api/
│   └── openapi.yaml        # Your API spec
├── src/
│   └── api/                # Your API code
│       ├── main.py
│       └── routes/
└── reports/
    └── acv/                # ACV reports (auto-created)
        ├── drift_report_*.md
        └── drift_report_*.json
```

## Environment Variables

Optional but recommended:

```bash
# For AI-powered analysis
export ANTHROPIC_API_KEY="your-key"

# Add to your .env file
echo 'ANTHROPIC_API_KEY="your-key"' >> .env
```

## CI/CD Integration

Add to GitHub Actions:

```yaml
# .github/workflows/api-validation.yml
- name: Install ACV
  run: pip install -e /path/to/api-contract-validator

- name: Validate API
  run: acv validate --env staging
```

## Troubleshooting

**Command not found:**
```bash
pip install -e /Users/I764709/api-contract-validator
```

**Config not found:**
```bash
acv init  # Creates acv_config.yaml
```

**API not responding:**
```bash
# Check if your API is running
curl http://localhost:8000/health
```

**Changes to ACV not working:**
```bash
# Ensure editable install
pip show api-contract-validator | grep Location
# Should show: /Users/I764709/api-contract-validator
```

## Using ACV Programmatically

Import ACV directly in your Python code:

### In pytest
```python
# tests/test_contract.py
import pytest
from pathlib import Path
from api_contract_validator.input.openapi.parser import OpenAPIParser
from api_contract_validator.generation.test_generator import MasterTestGenerator
from api_contract_validator.execution.runner.executor import TestExecutor

@pytest.fixture
def api_spec():
    parser = OpenAPIParser()
    return parser.parse_file(Path("api/openapi.yaml"))

def test_api_contract(api_spec):
    generator = MasterTestGenerator()
    test_suite = generator.generate_test_suite(api_spec)
    
    executor = TestExecutor("http://localhost:8000")
    results = executor.execute_tests_sync(test_suite.test_cases)
    
    from api_contract_validator.execution.collector.result_collector import ResultCollector
    collector = ResultCollector()
    collector.add_results(results)
    summary = collector.get_summary()
    
    assert summary.failed == 0, f"{summary.failed} contract violations"
```

### In Custom Script
```python
# validate.py
from pathlib import Path
from api_contract_validator.input.openapi.parser import OpenAPIParser
from api_contract_validator.schema.contract.constraint_extractor import ConstraintExtractor
from api_contract_validator.generation.test_generator import MasterTestGenerator
from api_contract_validator.execution.runner.executor import TestExecutor
from api_contract_validator.execution.collector.result_collector import ResultCollector
from api_contract_validator.analysis.drift.detector import DriftDetector

parser = OpenAPIParser()
spec = parser.parse_file(Path("api/openapi.yaml"))

extractor = ConstraintExtractor(spec)
contract = extractor.extract_contract()

generator = MasterTestGenerator()
test_suite = generator.generate_test_suite(spec)

executor = TestExecutor("http://localhost:8000")
results = executor.execute_tests_sync(test_suite.test_cases)

collector = ResultCollector()
collector.add_results(results)
summary = collector.get_summary()

detector = DriftDetector(contract)
drift_report = detector.detect_drift(summary)

print(f"Total issues: {drift_report.summary.total_issues}")
```

## Architecture Overview

### Module Structure
```
src/api_contract_validator/
├── cli/                # CLI interface (acv command)
├── api/                # REST API server (FastAPI)
├── input/              # Input processing (OpenAPI, PRD)
│   ├── openapi/        # OpenAPI parser
│   └── prd/            # PRD parser
├── schema/             # Contract modeling
│   ├── contract/       # Contract extraction & rules
│   └── resolver/       # Reference resolution
├── generation/         # Test generation
│   ├── valid/          # Valid test cases
│   ├── invalid/        # Invalid test cases
│   ├── boundary/       # Boundary test cases
│   └── prioritizer/    # Risk-based prioritization
├── execution/          # Test execution
│   └── runner/         # Parallel HTTP executor
├── analysis/           # Drift detection
│   ├── drift/          # Multi-dimensional drift
│   └── reasoning/      # AI analysis (Claude)
└── reporting/          # Report generation
    ├── markdown/       # Markdown reports
    ├── json/           # JSON reports
    └── cli/            # CLI output
```

### Data Flow
```
OpenAPI Spec → Parser → UnifiedSpec
                           ↓
              Constraint Extractor → APIContract
                           ↓
              Test Generator → TestSuite (50-500 tests)
                           ↓
              Test Executor → Results (parallel)
                           ↓
              Drift Detector → DriftReport
                           ↓
              AI Analyzer → Analysis + Recommendations
                           ↓
              Report Generator → Markdown/JSON/CLI
```

## Configuration Reference

### Complete acv_config.yaml
```yaml
project:
  root: "."
  spec:
    path: "api/openapi.yaml"
    format: "openapi"
  endpoints:
    directory: "src"
    patterns: ["**/*.py", "**/*.js", "**/*.ts"]
  tests:
    directory: "tests"
    patterns: ["test_*.py", "*_test.py"]
  output:
    tests: "tests/generated"
    reports: "reports/acv"

api:
  base_url: "http://localhost:8000"
  environments:
    local: "http://localhost:8000"
    dev: "https://dev-api.example.com"
    staging: "https://staging-api.example.com"
    prod: "https://api.example.com"

execution:
  parallel_workers: 10
  timeout_seconds: 30
  retry_attempts: 3
  retry_delay_seconds: 1

test_generation:
  generate_valid: true
  generate_invalid: true
  generate_boundary: true
  max_tests_per_endpoint: 50
  enable_prioritization: true
  exclude_endpoints:
    - "/health"
    - "/metrics"

drift_detection:
  detect_contract_drift: true
  detect_validation_drift: true
  detect_behavioral_drift: true
  fail_on_critical: true
  fail_on_high: false

ai_analysis:
  enabled: true
  model: "claude-3-5-sonnet-20241022"
  max_tokens: 4000

reporting:
  formats: ["markdown", "json"]
  include_test_details: true
  include_recommendations: true

logging:
  level: "INFO"
  format: "detailed"
  file: "logs/acv.log"
```

## REST API Server

Run ACV as a web service:

```bash
# Start server
uvicorn api_contract_validator.api.server:app --reload --port 9000

# Open docs
open http://localhost:9000/docs
```

### Endpoints
- `POST /validate` - Start validation job (async)
- `GET /status/{job_id}` - Check job status
- `GET /report/{job_id}/{format}` - Download report
- `POST /parse` - Parse spec only
- `POST /generate-tests` - Generate tests only
- `GET /health` - Health check

### Example Usage
```bash
# Start validation
JOB_ID=$(curl -s -X POST http://localhost:9000/validate \
  -F "spec_file=@api/openapi.yaml" \
  -F 'validation_request={"api_url": "http://localhost:8000", "parallel_workers": 10}' \
  | jq -r '.job_id')

# Check status
curl http://localhost:9000/status/$JOB_ID | jq '.'

# Download report
curl http://localhost:9000/report/$JOB_ID/json -o report.json
```

## Development on ACV

### Running Tests
```bash
cd /Users/I764709/api-contract-validator
pytest
pytest --cov=api_contract_validator --cov-report=html
```

### Code Quality
```bash
black src/ tests/
ruff check src/ tests/
mypy src/
```

### Demo Locally
```bash
# Terminal 1: Start mock API
python examples/mock_apis/users_api.py

# Terminal 2: Run validation
acv validate examples/openapi/sample_users_api.yaml --api-url http://localhost:8000
```

## Key Concepts

### Editable Install (`-e` flag)
- Links to source code instead of copying
- Changes appear immediately in all projects
- Perfect for library development

### Auto-discovery
- `acv validate` automatically finds `acv_config.yaml`
- No need to specify paths every time
- Convention over configuration

### Multi-dimensional Drift Detection
- **Contract Drift**: Response schema doesn't match spec
- **Validation Drift**: Invalid inputs are accepted
- **Behavioral Drift**: Inconsistent response patterns

### Test Categories
- **Valid Tests**: Happy path scenarios
- **Invalid Tests**: Missing fields, wrong types, constraint violations
- **Boundary Tests**: Min/max values, edge cases, zero/negative values

## Summary

✅ **Install once**: `pip install -e /path/to/api-contract-validator`  
✅ **Configure once**: `acv init` creates `acv_config.yaml`  
✅ **Run anytime**: `acv validate`  
✅ **Update instantly**: Changes to ACV are live immediately  
✅ **Use everywhere**: Import in any project  

---

**You're all set!** Your ACV repo is now a reusable library with automatic live updates.

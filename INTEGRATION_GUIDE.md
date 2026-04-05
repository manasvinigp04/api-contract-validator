# API Contract Validator - Integration & Installation Guide

This guide explains how to install and use the API Contract Validator as a library or plugin in your own projects, and how to use the REST API server for contract validation and drift detection.

## Table of Contents

1. [Installation Methods](#installation-methods)
2. [Using as a Python Library](#using-as-a-python-library)
3. [Using the REST API Server](#using-the-rest-api-server)
4. [Integration Examples](#integration-examples)
5. [CI/CD Integration](#cicd-integration)

---

## Installation Methods

### Method 1: Install from Source (Recommended for Development)

```bash
# Clone the repository
git clone https://github.com/yourusername/api-contract-validator.git
cd api-contract-validator

# Install in editable mode
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"

# Download required spaCy model
python -m spacy download en_core_web_sm
```

### Method 2: Install as a Package

```bash
# Install from PyPI (once published)
pip install api-contract-validator

# Or install directly from GitHub
pip install git+https://github.com/yourusername/api-contract-validator.git

# Download required spaCy model
python -m spacy download en_core_web_sm
```

### Method 3: Add as a Dependency

Add to your `requirements.txt`:
```
api-contract-validator>=0.1.0
```

Or in `pyproject.toml`:
```toml
[project]
dependencies = [
    "api-contract-validator>=0.1.0",
]
```

---

## Using as a Python Library

### Basic Validation Example

```python
from pathlib import Path
from api_contract_validator.input.openapi.parser import OpenAPIParser
from api_contract_validator.schema.contract.constraint_extractor import ConstraintExtractor
from api_contract_validator.generation.test_generator import MasterTestGenerator
from api_contract_validator.execution.runner.executor import TestExecutor
from api_contract_validator.execution.collector.result_collector import ResultCollector
from api_contract_validator.analysis.drift.detector import DriftDetector
from api_contract_validator.config.loader import ConfigLoader, set_config

# Load configuration
config = ConfigLoader.load()
set_config(config)

# Parse OpenAPI specification
parser = OpenAPIParser()
spec = parser.parse_file(Path("path/to/openapi.yaml"))

# Extract contract rules
extractor = ConstraintExtractor(spec)
api_contract = extractor.extract_contract()

# Generate test cases
generator = MasterTestGenerator(config.test_generation)
test_suite = generator.generate_test_suite(spec)

# Execute tests against your API
executor = TestExecutor("https://api.example.com", config.execution)
test_results = executor.execute_tests_sync(test_suite.test_cases)

# Collect results
collector = ResultCollector()
collector.add_results(test_results)
execution_summary = collector.get_summary()

# Detect drift
drift_detector = DriftDetector(api_contract, config.drift_detection)
drift_report = drift_detector.detect_drift(execution_summary)

# Check for critical issues
if drift_report.has_critical_issues():
    print(f"❌ Critical drift detected: {drift_report.summary.critical_count} issues")
    # Handle critical drift (e.g., fail CI/CD pipeline)
else:
    print(f"✅ No critical drift detected")
```

### Test Generation Only

```python
from pathlib import Path
from api_contract_validator.input.openapi.parser import OpenAPIParser
from api_contract_validator.generation.test_generator import MasterTestGenerator
from api_contract_validator.config.models import TestGenerationConfig

# Parse specification
parser = OpenAPIParser()
spec = parser.parse_file(Path("openapi.yaml"))

# Configure test generation
gen_config = TestGenerationConfig(
    enable_prioritization=True,
    max_tests_per_endpoint=50,
)

# Generate tests
generator = MasterTestGenerator(gen_config)
test_suite = generator.generate_test_suite(spec)

# Use the test suite
print(f"Generated {len(test_suite.test_cases)} test cases")
print(f"Valid tests: {len(test_suite.get_valid_tests())}")
print(f"Invalid tests: {len(test_suite.get_invalid_tests())}")
print(f"Boundary tests: {len(test_suite.get_boundary_tests())}")
```

### Drift Detection for Existing Test Results

```python
from api_contract_validator.analysis.drift.detector import DriftDetector
from api_contract_validator.execution.collector.result_collector import ResultCollector
from api_contract_validator.config.models import DriftDetectionConfig

# Assuming you have api_contract and test_results from previous steps
config = DriftDetectionConfig(
    contract_drift_threshold=0.8,
    validation_drift_threshold=0.7,
    behavioral_drift_threshold=0.6,
)

drift_detector = DriftDetector(api_contract, config)
drift_report = drift_detector.detect_drift(execution_summary)

# Access drift details
for issue in drift_report.contract_drift.issues:
    print(f"Contract drift: {issue.severity} - {issue.message}")

for issue in drift_report.validation_drift.issues:
    print(f"Validation drift: {issue.severity} - {issue.message}")

for issue in drift_report.behavioral_drift.issues:
    print(f"Behavioral drift: {issue.severity} - {issue.message}")
```

### AI-Assisted Analysis

```python
from api_contract_validator.analysis.reasoning.analyzer import AIAnalyzer
from api_contract_validator.config.models import AIAnalysisConfig
import os

# Configure AI analysis
ai_config = AIAnalysisConfig(
    enabled=True,
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    model="claude-3-5-sonnet-20241022",
)

# Run AI analysis on drift report
ai_analyzer = AIAnalyzer(ai_config)
analysis_result = ai_analyzer.analyze_drift(drift_report)

# Access insights
if analysis_result.has_insights():
    print(f"Risk Score: {analysis_result.risk_score}")
    print(f"Confidence: {analysis_result.confidence}")
    
    for insight in analysis_result.insights:
        print(f"\n{insight.category}: {insight.title}")
        print(f"Description: {insight.description}")
        
        if insight.action_items:
            print("Action items:")
            for action in insight.action_items:
                print(f"  - {action}")
```

---

## Using the REST API Server

### Starting the Server

#### Development Mode (with auto-reload)
```bash
# Using uvicorn directly
uvicorn api_contract_validator.api.server:app --reload --host 0.0.0.0 --port 8000

# Or using the Python module
python -m api_contract_validator.api.server
```

#### Production Mode
```bash
# Single worker
uvicorn api_contract_validator.api.server:app --host 0.0.0.0 --port 8000

# Multiple workers
uvicorn api_contract_validator.api.server:app --host 0.0.0.0 --port 8000 --workers 4
```

#### Using VS Code Debugger
1. Open the project in VS Code
2. Go to "Run and Debug" (Ctrl+Shift+D / Cmd+Shift+D)
3. Select "FastAPI: Uvicorn Server (Development)"
4. Press F5 to start debugging

The server will start at `http://localhost:8000` with interactive API docs at `http://localhost:8000/docs`.

### API Endpoints

#### 1. Health Check
```bash
curl http://localhost:8000/health
```

#### 2. Parse OpenAPI Specification
```bash
curl -X POST http://localhost:8000/parse \
  -F "spec_file=@path/to/openapi.yaml"
```

#### 3. Generate Test Cases
```bash
curl -X POST http://localhost:8000/generate-tests \
  -F "spec_file=@path/to/openapi.yaml" \
  -F 'request_data={"prioritize": true, "max_tests_per_endpoint": 50}'
```

#### 4. Validate API (Full Workflow)
```bash
# Submit validation job
curl -X POST http://localhost:8000/validate \
  -F "spec_file=@path/to/openapi.yaml" \
  -F 'validation_request={"api_url": "https://api.example.com", "parallel_workers": 10, "timeout_seconds": 30, "enable_ai_analysis": true, "output_format": "all"}' \
  > job_response.json

# Extract job ID
JOB_ID=$(cat job_response.json | jq -r '.job_id')

# Check validation status
curl http://localhost:8000/status/$JOB_ID

# Download reports (when completed)
curl http://localhost:8000/report/$JOB_ID/json -o validation_report.json
curl http://localhost:8000/report/$JOB_ID/markdown -o validation_report.md
```

### Python Client Example

```python
import requests
import time
import json

# API endpoint
API_URL = "http://localhost:8000"

# Submit validation job
with open("openapi.yaml", "rb") as f:
    files = {"spec_file": f}
    data = {
        "validation_request": json.dumps({
            "api_url": "https://api.example.com",
            "parallel_workers": 10,
            "timeout_seconds": 30,
            "enable_ai_analysis": True,
            "output_format": "all"
        })
    }
    
    response = requests.post(f"{API_URL}/validate", files=files, data=data)
    job = response.json()
    job_id = job["job_id"]
    print(f"Job submitted: {job_id}")

# Poll for completion
while True:
    response = requests.get(f"{API_URL}/status/{job_id}")
    status = response.json()
    
    print(f"Status: {status['status']} - {status['message']}")
    
    if status["status"] == "completed":
        print(f"✅ Validation completed!")
        print(f"Total tests: {status['result']['total_tests']}")
        print(f"Passed: {status['result']['passed']}")
        print(f"Failed: {status['result']['failed']}")
        print(f"Drift issues: {status['result']['total_drift_issues']}")
        
        # Download report
        report_response = requests.get(f"{API_URL}/report/{job_id}/json")
        with open("validation_report.json", "w") as f:
            f.write(report_response.text)
        
        break
    elif status["status"] == "failed":
        print(f"❌ Validation failed: {status['message']}")
        break
    
    time.sleep(2)
```

---

## Integration Examples

### Integration with Pytest

Create a pytest plugin or conftest.py:

```python
# conftest.py
import pytest
from pathlib import Path
from api_contract_validator.input.openapi.parser import OpenAPIParser
from api_contract_validator.generation.test_generator import MasterTestGenerator
from api_contract_validator.config.models import TestGenerationConfig

@pytest.fixture(scope="session")
def api_test_suite():
    """Generate test suite from OpenAPI spec."""
    parser = OpenAPIParser()
    spec = parser.parse_file(Path("path/to/openapi.yaml"))
    
    gen_config = TestGenerationConfig(enable_prioritization=True)
    generator = MasterTestGenerator(gen_config)
    test_suite = generator.generate_test_suite(spec)
    
    return test_suite

@pytest.fixture(scope="session")
def api_base_url():
    """Base URL for API tests."""
    return "https://api.example.com"

# test_api_contracts.py
def test_api_contracts(api_test_suite, api_base_url):
    """Test API against generated contract tests."""
    from api_contract_validator.execution.runner.executor import TestExecutor
    from api_contract_validator.config.models import ExecutionConfig
    
    config = ExecutionConfig()
    executor = TestExecutor(api_base_url, config)
    results = executor.execute_tests_sync(api_test_suite.test_cases)
    
    failed_tests = [r for r in results if not r.passed]
    
    if failed_tests:
        failure_msg = "\n".join([
            f"  - {t.test_case.test_id}: {t.message}"
            for t in failed_tests
        ])
        pytest.fail(f"API contract tests failed:\n{failure_msg}")
```

### Integration with FastAPI Application

```python
from fastapi import FastAPI, Depends
from api_contract_validator.input.openapi.parser import OpenAPIParser
from api_contract_validator.generation.test_generator import MasterTestGenerator

app = FastAPI()

# Generate and expose contract tests
@app.get("/contract-tests")
async def get_contract_tests():
    """Endpoint to retrieve generated contract tests."""
    parser = OpenAPIParser()
    # Parse your own OpenAPI spec
    spec = parser.parse_from_fastapi(app)
    
    generator = MasterTestGenerator()
    test_suite = generator.generate_test_suite(spec)
    
    return test_suite.model_dump(mode="json")

# Validate your API at startup
@app.on_event("startup")
async def validate_api_contract():
    """Validate API contract on startup."""
    from api_contract_validator.execution.runner.executor import TestExecutor
    from api_contract_validator.config.models import ExecutionConfig
    
    # Self-validation
    parser = OpenAPIParser()
    spec = parser.parse_from_fastapi(app)
    
    generator = MasterTestGenerator()
    test_suite = generator.generate_test_suite(spec)
    
    config = ExecutionConfig(timeout_seconds=10)
    executor = TestExecutor("http://localhost:8000", config)
    
    # Run validation in background
    # ... (implement async validation logic)
```

---

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/api-contract-validation.yml
name: API Contract Validation

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  validate:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install api-contract-validator
        python -m spacy download en_core_web_sm
    
    - name: Start API server
      run: |
        # Start your API in background
        python -m your_api.server &
        sleep 5
    
    - name: Validate API contract
      env:
        ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      run: |
        api-contract-validator validate \
          specs/openapi.yaml \
          --api-url http://localhost:8000 \
          --format all \
          --output ./reports
    
    - name: Upload validation reports
      if: always()
      uses: actions/upload-artifact@v3
      with:
        name: contract-validation-reports
        path: ./reports/
```

### GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - test
  - validate

api_contract_validation:
  stage: validate
  image: python:3.11
  
  before_script:
    - pip install api-contract-validator
    - python -m spacy download en_core_web_sm
  
  script:
    # Start your API
    - python -m your_api.server &
    - sleep 5
    
    # Run validation
    - |
      api-contract-validator validate \
        specs/openapi.yaml \
        --api-url http://localhost:8000 \
        --format all \
        --output ./reports
  
  artifacts:
    paths:
      - reports/
    expire_in: 1 week
  
  allow_failure: false
```

### Jenkins Pipeline

```groovy
// Jenkinsfile
pipeline {
    agent any
    
    environment {
        ANTHROPIC_API_KEY = credentials('anthropic-api-key')
    }
    
    stages {
        stage('Setup') {
            steps {
                sh '''
                    pip install api-contract-validator
                    python -m spacy download en_core_web_sm
                '''
            }
        }
        
        stage('Start API') {
            steps {
                sh '''
                    python -m your_api.server &
                    sleep 5
                '''
            }
        }
        
        stage('Validate Contract') {
            steps {
                sh '''
                    api-contract-validator validate \
                        specs/openapi.yaml \
                        --api-url http://localhost:8000 \
                        --format all \
                        --output ./reports
                '''
            }
        }
    }
    
    post {
        always {
            archiveArtifacts artifacts: 'reports/**/*', allowEmptyArchive: true
        }
    }
}
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: api-contract-validation
        name: API Contract Validation
        entry: bash -c 'api-contract-validator validate specs/openapi.yaml --api-url http://localhost:8000'
        language: system
        pass_filenames: false
        always_run: false
        files: 'specs/.*\.yaml$'
```

---

## Environment Variables

Configure the validator using environment variables:

```bash
# AI Analysis
export ANTHROPIC_API_KEY="your-api-key"
export AI_ANALYSIS_ENABLED="true"
export AI_MODEL="claude-3-5-sonnet-20241022"

# Execution
export PARALLEL_WORKERS="10"
export TIMEOUT_SECONDS="30"

# Output
export OUTPUT_DIRECTORY="./reports"
export OUTPUT_FORMAT="all"
```

---

## Demo Script

Here's a complete demo script showing the validator in action:

```bash
#!/bin/bash

echo "🚀 API Contract Validator Demo"
echo "================================"
echo ""

# 1. Install dependencies
echo "📦 Installing dependencies..."
pip install -e .
python -m spacy download en_core_web_sm

# 2. Start the validator API server
echo "🌐 Starting validator API server..."
uvicorn api_contract_validator.api.server:app --port 9000 &
VALIDATOR_PID=$!
sleep 3

# 3. Start your API to be tested (example)
echo "🔧 Starting test API..."
python examples/mock_apis/users_api.py &
API_PID=$!
sleep 2

# 4. Run validation via REST API
echo "✅ Running API validation..."
JOB_RESPONSE=$(curl -s -X POST http://localhost:9000/validate \
  -F "spec_file=@examples/users/users-api.yaml" \
  -F 'validation_request={"api_url": "http://localhost:8000", "parallel_workers": 5, "timeout_seconds": 30, "enable_ai_analysis": true, "output_format": "all"}')

JOB_ID=$(echo $JOB_RESPONSE | jq -r '.job_id')
echo "Job ID: $JOB_ID"

# 5. Poll for completion
echo "⏳ Waiting for validation to complete..."
while true; do
    STATUS_RESPONSE=$(curl -s http://localhost:9000/status/$JOB_ID)
    STATUS=$(echo $STATUS_RESPONSE | jq -r '.status')
    
    if [ "$STATUS" = "completed" ]; then
        echo "✅ Validation completed!"
        echo $STATUS_RESPONSE | jq '.result'
        break
    elif [ "$STATUS" = "failed" ]; then
        echo "❌ Validation failed!"
        echo $STATUS_RESPONSE | jq '.message'
        break
    fi
    
    sleep 2
done

# 6. Download reports
echo "📄 Downloading reports..."
curl -s http://localhost:9000/report/$JOB_ID/json -o validation_report.json
curl -s http://localhost:9000/report/$JOB_ID/markdown -o validation_report.md

echo "Reports saved: validation_report.json, validation_report.md"

# Cleanup
kill $VALIDATOR_PID $API_PID
echo ""
echo "✨ Demo completed!"
```

---

## Support and Documentation

- **API Documentation**: `http://localhost:8000/docs` (when server is running)
- **CLI Help**: `api-contract-validator --help`
- **Examples**: See `/examples` directory in the repository
- **Issues**: Report bugs at https://github.com/yourusername/api-contract-validator/issues

---

## License

MIT License - See LICENSE file for details

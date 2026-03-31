# Integration Guide

This guide shows how to integrate the API Contract Validator into your existing projects.

## Installation

### From PyPI (After Publishing)

```bash
pip install api-contract-validator

# Verify installation
acv --version
acv --help
```

### Install spaCy Model

```bash
# Required for PRD parsing (optional for OpenAPI only)
python -m spacy download en_core_web_sm
```

---

## Quick Integration - Any Project

### 1. Add to Your Project

```bash
cd /path/to/your-project

# Install the validator
pip install api-contract-validator

# Or add to requirements.txt
echo "api-contract-validator>=0.1.0" >> requirements.txt
pip install -r requirements.txt
```

### 2. Create OpenAPI Spec (if you don't have one)

```bash
# Place your OpenAPI spec in the project
# Recommended location: docs/api/openapi.yaml or api-spec.yaml
```

### 3. Run Validation

```bash
# Basic usage
acv validate docs/api/openapi.yaml --api-url http://localhost:8000

# With your production API
acv validate docs/api/openapi.yaml --api-url https://api.yourapp.com
```

---

## Integration Scenarios

### Scenario 1: Django/Flask/FastAPI Project

**Project Structure:**
```
your-django-project/
├── manage.py
├── api/
│   └── openapi.yaml          # Your OpenAPI spec
├── config/
│   └── acv-config.yaml       # Validator config
└── requirements.txt
```

**Add to requirements.txt:**
```txt
Django==4.2.0
djangorestframework==3.14.0
api-contract-validator>=0.1.0
```

**Create config/acv-config.yaml:**
```yaml
test_generation:
  max_tests_per_endpoint: 25
  enable_prioritization: true

execution:
  parallel_workers: 10
  timeout_seconds: 30

ai_analysis:
  enabled: true
```

**Add npm script or Make command:**
```makefile
# Makefile
.PHONY: validate-api
validate-api:
	python manage.py runserver &
	sleep 3
	acv validate api/openapi.yaml \
		--api-url http://localhost:8000 \
		--config config/acv-config.yaml
	pkill -f "manage.py runserver"
```

**Usage:**
```bash
make validate-api
```

---

### Scenario 2: Node.js/Express Project

**Project Structure:**
```
your-node-project/
├── package.json
├── src/
├── docs/
│   └── openapi.yaml
└── scripts/
    └── validate-api.sh
```

**Install validator globally or in virtualenv:**
```bash
# Option 1: Global
pip install api-contract-validator

# Option 2: Project-specific
python -m venv .venv
source .venv/bin/activate
pip install api-contract-validator
```

**Create scripts/validate-api.sh:**
```bash
#!/bin/bash
set -e

echo "Starting API server..."
npm start &
SERVER_PID=$!
sleep 5

echo "Running API validation..."
acv validate docs/openapi.yaml \
  --api-url http://localhost:3000 \
  --output-dir reports/api-validation

echo "Stopping server..."
kill $SERVER_PID

echo "✅ Validation complete!"
```

**Add to package.json:**
```json
{
  "scripts": {
    "validate-api": "./scripts/validate-api.sh",
    "test": "jest && npm run validate-api"
  }
}
```

**Usage:**
```bash
npm run validate-api
```

---

### Scenario 3: Microservices Architecture

**Project Structure:**
```
microservices-project/
├── services/
│   ├── user-service/
│   │   └── openapi.yaml
│   ├── order-service/
│   │   └── openapi.yaml
│   └── payment-service/
│       └── openapi.yaml
└── scripts/
    └── validate-all.sh
```

**Create scripts/validate-all.sh:**
```bash
#!/bin/bash

SERVICES=(
  "user-service:8001"
  "order-service:8002"
  "payment-service:8003"
)

for SERVICE_PORT in "${SERVICES[@]}"; do
  SERVICE="${SERVICE_PORT%%:*}"
  PORT="${SERVICE_PORT##*:}"
  
  echo "Validating $SERVICE..."
  acv validate services/$SERVICE/openapi.yaml \
    --api-url "http://localhost:$PORT" \
    --output-dir "reports/$SERVICE" || {
      echo "❌ $SERVICE validation failed"
      exit 1
    }
  
  echo "✅ $SERVICE validated"
done

echo "✅ All services validated successfully!"
```

**Usage:**
```bash
# Start all services first
docker-compose up -d

# Run validation
./scripts/validate-all.sh

# Stop services
docker-compose down
```

---

### Scenario 4: CI/CD Integration

#### GitHub Actions

**Create .github/workflows/api-validation.yml:**
```yaml
name: API Contract Validation

on:
  pull_request:
    paths:
      - 'api/**'
      - 'docs/openapi.yaml'
  push:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install validator
        run: pip install api-contract-validator
      
      - name: Start API server
        run: |
          npm install
          npm start &
          sleep 5
      
      - name: Validate API contract
        run: |
          acv validate docs/openapi.yaml \
            --api-url http://localhost:3000 \
            --output-dir reports
      
      - name: Upload reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: validation-reports
          path: reports/
      
      - name: Check for critical issues
        run: |
          CRITICAL=$(jq '.summary.critical_count' reports/drift_report.json)
          if [ "$CRITICAL" -gt 0 ]; then
            echo "❌ Critical drift detected"
            exit 1
          fi
```

#### GitLab CI

**Add to .gitlab-ci.yml:**
```yaml
api-validation:
  stage: test
  image: python:3.11
  before_script:
    - pip install api-contract-validator
  script:
    - npm start &
    - sleep 5
    - acv validate docs/openapi.yaml --api-url http://localhost:3000
  artifacts:
    paths:
      - reports/
```

---

## Configuration Management

### Per-Environment Configs

```
project/
├── config/
│   ├── acv-dev.yaml        # Development
│   ├── acv-staging.yaml    # Staging
│   └── acv-prod.yaml       # Production
```

**acv-dev.yaml:**
```yaml
test_generation:
  max_tests_per_endpoint: 10
execution:
  timeout_seconds: 60
ai_analysis:
  enabled: false
logging:
  level: DEBUG
```

**acv-prod.yaml:**
```yaml
test_generation:
  max_tests_per_endpoint: 100
  enable_prioritization: true
execution:
  parallel_workers: 20
  timeout_seconds: 15
ai_analysis:
  enabled: true
```

**Usage:**
```bash
# Development
acv validate api/spec.yaml --api-url http://localhost:8000 --config config/acv-dev.yaml

# Production
acv validate api/spec.yaml --api-url https://api.prod.com --config config/acv-prod.yaml
```

---

## Pre-commit Hook Integration

**Add to .pre-commit-config.yaml:**
```yaml
repos:
  - repo: local
    hooks:
      - id: api-contract-validation
        name: Validate API Contract
        entry: bash -c 'if [ -f "docs/openapi.yaml" ]; then acv parse docs/openapi.yaml; fi'
        language: system
        pass_filenames: false
        always_run: false
        files: 'docs/openapi.yaml'
```

---

## Docker Integration

**Dockerfile approach:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install validator
RUN pip install api-contract-validator

# Copy specs
COPY docs/openapi.yaml /app/openapi.yaml

# Run validation
CMD ["acv", "validate", "openapi.yaml", "--api-url", "${API_URL}"]
```

**Usage:**
```bash
docker build -t api-validator .
docker run -e API_URL=http://host.docker.internal:8000 api-validator
```

---

## Authentication Examples

### API Key
```bash
acv validate spec.yaml \
  --api-url https://api.example.com \
  --header "X-API-Key: your-api-key"
```

### Bearer Token
```bash
TOKEN=$(cat ~/.secrets/api-token)
acv validate spec.yaml \
  --api-url https://api.example.com \
  --header "Authorization: Bearer $TOKEN"
```

### Basic Auth
```bash
acv validate spec.yaml \
  --api-url https://api.example.com \
  --header "Authorization: Basic $(echo -n user:pass | base64)"
```

### Custom Headers in Config
```yaml
# config/auth.yaml
execution:
  headers:
    X-API-Key: "${API_KEY}"
    X-Client-ID: "validator-client"
```

---

## Best Practices

### 1. Version Control Your Spec
```bash
# Keep OpenAPI spec in version control
git add docs/openapi.yaml
git commit -m "docs: update API specification"
```

### 2. Automate in CI/CD
- Run on every PR that touches API code
- Block merges if critical drift detected
- Generate reports as artifacts

### 3. Schedule Regular Checks
```yaml
# GitHub Actions - scheduled validation
on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
```

### 4. Track Drift Over Time
```bash
# Save reports with timestamps
acv validate spec.yaml --api-url $URL \
  --output-dir "reports/$(date +%Y%m%d-%H%M%S)"
```

### 5. Use Environment Variables
```bash
# .env file
export API_URL=http://localhost:8000
export ANTHROPIC_API_KEY=sk-...
export ACV_PARALLEL_WORKERS=10

# Use in scripts
acv validate spec.yaml --api-url $API_URL
```

---

## Troubleshooting

### Issue: Command not found after pip install
```bash
# Ensure pip bin directory is in PATH
which acv
# If not found:
export PATH="$HOME/.local/bin:$PATH"
```

### Issue: API not reachable during validation
```bash
# Check if API is running
curl http://localhost:8000/health

# Check firewall/ports
netstat -tuln | grep 8000
```

### Issue: Too many test failures
```bash
# Reduce test load for debugging
acv validate spec.yaml --api-url $URL --config minimal-config.yaml

# minimal-config.yaml:
# test_generation:
#   max_tests_per_endpoint: 5
```

---

## Next Steps

1. **Install the validator**: `pip install api-contract-validator`
2. **Add your OpenAPI spec** to your project
3. **Configure** for your environment
4. **Integrate** into your workflow (pre-commit, CI/CD, scripts)
5. **Monitor** and track drift over time

For more examples, see:
- [Usage Examples](USAGE_EXAMPLES.md)
- [CI/CD Integration](CI_CD_INTEGRATION.md)
- [Configuration Guide](../config/README.md)

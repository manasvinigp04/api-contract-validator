# Usage Examples

This document provides comprehensive examples of using the API Contract Validator in various scenarios.

## Table of Contents

- [Basic Usage](#basic-usage)
- [Advanced Scenarios](#advanced-scenarios)
- [Configuration Examples](#configuration-examples)
- [CI/CD Integration](#cicd-integration)
- [Real-World Use Cases](#real-world-use-cases)

## Basic Usage

### 1. Validate an OpenAPI Specification

```bash
# Simple validation
acv validate examples/openapi/sample_users_api.yaml \
  --api-url https://api.example.com

# With custom config
acv validate spec.yaml \
  --api-url https://api.example.com \
  --config config/validation.yaml

# Output to specific directory
acv validate spec.yaml \
  --api-url https://api.example.com \
  --output-dir ./reports/$(date +%Y%m%d)
```

### 2. Parse and Inspect an OpenAPI Specification

```bash
# Parse OpenAPI spec
acv parse examples/openapi/sample_users_api.yaml

# Parse with detailed output
acv parse spec.yaml --verbose

# Export parsed contract to JSON
acv parse spec.yaml --output contract.json
```

### 3. Generate Test Cases

```bash
# Generate all test types
acv generate-tests spec.yaml -o tests/generated_tests.json

# Generate only valid tests
acv generate-tests spec.yaml \
  --test-types valid \
  -o tests/valid_tests.json

# Generate with prioritization
acv generate-tests spec.yaml \
  --max-per-endpoint 25 \
  --enable-prioritization \
  -o tests/prioritized_tests.json
```

### 4. Configuration Check

```bash
# Check current configuration
acv config-check

# Check with custom config file
acv config-check --config config/custom.yaml

# Display resolved configuration
acv config-check --verbose
```

## Advanced Scenarios

### Authentication

#### API Key Authentication

```bash
# Pass via environment variable
export API_KEY="your-api-key"
acv validate spec.yaml --api-url https://api.example.com

# Or configure in YAML
cat > config/auth.yaml << EOF
execution:
  headers:
    X-API-Key: "your-api-key"
EOF

acv validate spec.yaml \
  --api-url https://api.example.com \
  --config config/auth.yaml
```

#### Bearer Token Authentication

```bash
# JWT token
export AUTH_TOKEN="eyJhbGc..."
acv validate spec.yaml \
  --api-url https://api.example.com \
  --header "Authorization: Bearer $AUTH_TOKEN"
```

#### OAuth 2.0

```bash
# Get token first
TOKEN=$(curl -X POST https://auth.example.com/oauth/token \
  -d "client_id=xxx&client_secret=yyy" | jq -r .access_token)

# Use in validation
acv validate spec.yaml \
  --api-url https://api.example.com \
  --header "Authorization: Bearer $TOKEN"
```

### Multi-Environment Validation

```bash
#!/bin/bash
# validate_all_envs.sh

ENVIRONMENTS=("dev" "staging" "production")
SPEC="openapi.yaml"

for ENV in "${ENVIRONMENTS[@]}"; do
  echo "Validating $ENV environment..."
  
  acv validate $SPEC \
    --api-url "https://api-${ENV}.example.com" \
    --config "config/${ENV}.yaml" \
    --output-dir "reports/${ENV}/$(date +%Y%m%d)"
  
  # Check for critical drift
  if [ -f "reports/${ENV}/$(date +%Y%m%d)/drift_report.json" ]; then
    CRITICAL=$(jq '.summary.critical_count' "reports/${ENV}/$(date +%Y%m%d)/drift_report.json")
    if [ "$CRITICAL" -gt 0 ]; then
      echo "❌ Critical drift in $ENV: $CRITICAL issues"
    else
      echo "✅ $ENV passed validation"
    fi
  fi
done
```

### Progressive Drift Tracking

```bash
#!/bin/bash
# track_drift_over_time.sh

OUTPUT_DIR="drift-history"
mkdir -p $OUTPUT_DIR

# Run validation
acv validate spec.yaml \
  --api-url https://api.example.com \
  --output-dir $OUTPUT_DIR/temp

# Archive results with timestamp
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
mv $OUTPUT_DIR/temp/drift_report.json \
   $OUTPUT_DIR/drift-${TIMESTAMP}.json

# Analyze trend
python scripts/analyze_drift_trend.py $OUTPUT_DIR
```

### Parallel Validation

```bash
#!/bin/bash
# parallel_validation.sh

SPECS=(
  "api/users/openapi.yaml:https://api.example.com/users"
  "api/orders/openapi.yaml:https://api.example.com/orders"
  "api/products/openapi.yaml:https://api.example.com/products"
)

for SPEC_URL in "${SPECS[@]}"; do
  SPEC="${SPEC_URL%%:*}"
  URL="${SPEC_URL##*:}"
  NAME=$(basename $SPEC .yaml)
  
  (
    echo "Validating $NAME..."
    acv validate $SPEC \
      --api-url $URL \
      --output-dir "reports/$NAME" &
  )
done

wait
echo "All validations complete"
```

## Configuration Examples

### Minimal Configuration

```yaml
# config/minimal.yaml
test_generation:
  max_tests_per_endpoint: 10

execution:
  timeout_seconds: 15
```

### Strict Validation Configuration

```yaml
# config/strict.yaml
test_generation:
  generate_valid: true
  generate_invalid: true
  generate_boundary: true
  max_tests_per_endpoint: 100
  enable_prioritization: true

execution:
  parallel_workers: 20
  timeout_seconds: 30
  retry_attempts: 3
  retry_delay_seconds: 1

drift_detection:
  detect_contract_drift: true
  detect_validation_drift: true
  detect_behavioral_drift: true

ai_analysis:
  enabled: true
  model: "claude-3-5-sonnet-20241022"
  enable_root_cause_analysis: true
  enable_remediation_suggestions: true
  enable_correlation_analysis: true

reporting:
  generate_markdown: true
  generate_json: true
  generate_cli_summary: true
```

### Performance-Optimized Configuration

```yaml
# config/performance.yaml
test_generation:
  max_tests_per_endpoint: 25
  enable_prioritization: true

execution:
  parallel_workers: 50
  timeout_seconds: 10
  retry_attempts: 1

drift_detection:
  detect_contract_drift: true
  detect_validation_drift: false  # Disable for speed
  detect_behavioral_drift: false

ai_analysis:
  enabled: false  # Disable for speed

reporting:
  generate_markdown: false
  generate_json: true
  generate_cli_summary: true
```

### Development Configuration

```yaml
# config/dev.yaml
test_generation:
  max_tests_per_endpoint: 5
  generate_valid: true
  generate_invalid: false
  generate_boundary: false

execution:
  parallel_workers: 5
  timeout_seconds: 60

drift_detection:
  detect_contract_drift: true
  detect_validation_drift: false
  detect_behavioral_drift: false

ai_analysis:
  enabled: false

logging:
  level: "DEBUG"
```

## CI/CD Integration

### GitHub Actions - Pull Request Validation

```yaml
name: Validate API Changes

on:
  pull_request:
    paths:
      - 'api/**'
      - 'openapi.yaml'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install validator
        run: |
          pip install api-contract-validator
          python -m spacy download en_core_web_sm
      
      - name: Validate API
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          acv validate openapi.yaml \
            --api-url https://api-staging.example.com \
            --output-dir ./reports
      
      - name: Comment PR with results
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const report = JSON.parse(fs.readFileSync('reports/drift_report.json'));
            
            const comment = `## API Validation Results
            
            - **Total Issues:** ${report.summary.total_issues}
            - **Critical:** ${report.summary.critical_count}
            - **High:** ${report.summary.high_count}
            - **Medium:** ${report.summary.medium_count}
            
            ${report.summary.critical_count > 0 ? '❌ Critical issues found!' : '✅ No critical issues'}
            
            [View detailed report](./reports/drift_report.md)`;
            
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });
```

### Scheduled Monitoring

```yaml
name: API Health Monitor

on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  workflow_dispatch:

jobs:
  monitor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Validate Production API
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          acv validate openapi.yaml \
            --api-url https://api.example.com \
            --output-dir ./reports
      
      - name: Check for issues
        id: check
        run: |
          CRITICAL=$(jq '.summary.critical_count' reports/drift_report.json)
          HIGH=$(jq '.summary.high_count' reports/drift_report.json)
          
          echo "critical=$CRITICAL" >> $GITHUB_OUTPUT
          echo "high=$HIGH" >> $GITHUB_OUTPUT
          
          if [ "$CRITICAL" -gt 0 ] || [ "$HIGH" -gt 5 ]; then
            exit 1
          fi
      
      - name: Send Slack alert
        if: failure()
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "⚠️ API Drift Detected",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "API drift detected in production!\n*Critical:* ${{ steps.check.outputs.critical }}\n*High:* ${{ steps.check.outputs.high }}"
                  }
                }
              ]
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

## Real-World Use Cases

### 1. Pre-Deployment Gate

```bash
#!/bin/bash
# pre_deploy_check.sh

echo "Running pre-deployment API validation..."

acv validate openapi.yaml \
  --api-url https://api-staging.example.com \
  --config config/strict.yaml \
  --output-dir ./pre-deploy-reports

# Check results
CRITICAL=$(jq '.summary.critical_count' ./pre-deploy-reports/drift_report.json)
HIGH=$(jq '.summary.high_count' ./pre-deploy-reports/drift_report.json)

if [ "$CRITICAL" -gt 0 ]; then
  echo "❌ Deployment blocked: $CRITICAL critical issues found"
  exit 1
elif [ "$HIGH" -gt 10 ]; then
  echo "⚠️  Deployment warning: $HIGH high-severity issues found"
  echo "Proceed with caution"
  exit 0
else
  echo "✅ Deployment approved: No blocking issues"
  exit 0
fi
```

### 2. Contract-First Development Workflow

```bash
# 1. Design API contract
vim openapi.yaml

# 2. Validate contract syntax
acv parse openapi.yaml

# 3. Generate test cases for development
acv generate-tests openapi.yaml -o tests/contract_tests.json

# 4. Start development with mock server
# (Use generated tests to guide implementation)

# 5. Validate implementation against contract
acv validate openapi.yaml --api-url http://localhost:8000

# 6. Fix drift issues iteratively
# (Repeat step 5 until no drift detected)
```

### 3. Regression Testing

```bash
#!/bin/bash
# regression_test.sh

BASELINE="reports/baseline/drift_report.json"
CURRENT="reports/current/drift_report.json"

# Run validation
acv validate openapi.yaml \
  --api-url https://api.example.com \
  --output-dir reports/current

# Compare with baseline
BASELINE_ISSUES=$(jq '.summary.total_issues' $BASELINE)
CURRENT_ISSUES=$(jq '.summary.total_issues' $CURRENT)

echo "Baseline issues: $BASELINE_ISSUES"
echo "Current issues: $CURRENT_ISSUES"

if [ "$CURRENT_ISSUES" -gt "$BASELINE_ISSUES" ]; then
  echo "❌ Regression detected: Issues increased from $BASELINE_ISSUES to $CURRENT_ISSUES"
  exit 1
else
  echo "✅ No regression: Issues stayed same or decreased"
  exit 0
fi
```

### 4. Documentation Verification

```bash
# Ensure API documentation matches implementation
acv validate docs/api/openapi.yaml \
  --api-url https://api.example.com

# Generate human-readable report
acv validate docs/api/openapi.yaml \
  --api-url https://api.example.com \
  --output-format markdown

# Publish report to documentation site
cp reports/drift_report.md docs/api-validation.md
```

## Tips and Best Practices

### Performance Optimization

1. **Adjust parallel workers** based on API rate limits:
```yaml
execution:
  parallel_workers: 10  # Start conservative, increase gradually
```

2. **Use test prioritization** to focus on critical paths:
```yaml
test_generation:
  enable_prioritization: true
  max_tests_per_endpoint: 25
```

3. **Cache test generation** results:
```bash
# Generate once
acv generate-tests spec.yaml -o tests/cached_tests.json

# Reuse in multiple validations
acv validate spec.yaml --api-url $URL --tests tests/cached_tests.json
```

### Error Handling

```bash
# Graceful failure with reporting
acv validate spec.yaml --api-url $URL || {
  echo "Validation failed, but continuing..."
  cat reports/drift_report.json
  # Don't exit 1 if you want to continue
}
```

### Environment-Specific Configuration

```bash
# Use environment-specific configs
ENV=${ENV:-dev}
acv validate spec.yaml \
  --api-url $(cat config/${ENV}.env | grep API_URL | cut -d= -f2) \
  --config config/${ENV}.yaml
```

## Additional Resources

- [CLI Reference](./CLI_REFERENCE.md)
- [Configuration Guide](./CONFIGURATION.md)
- [CI/CD Integration](./CI_CD_INTEGRATION.md)
- [GitHub Actions Workflow](../.github/workflows/ci.yml)

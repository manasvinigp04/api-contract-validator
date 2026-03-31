# CI/CD Integration with GitHub Actions

This document provides comprehensive guidance for integrating the API Contract Validator into your GitHub Actions workflows.

## Quick Start

The project includes a complete GitHub Actions workflow at `.github/workflows/ci.yml` with:
- Multi-version Python testing (3.10, 3.11, 3.12)
- Code quality checks (linting, type checking)
- Test coverage reporting
- API validation with mock server
- Distribution building
- Artifact uploads

**Setup:**
1. The workflow is already configured in this repository
2. Add `ANTHROPIC_API_KEY` to GitHub Secrets (Settings → Secrets → Actions)
3. Push to `main` or `develop` branches or create a pull request

## Integration Strategies

### 1. Pre-merge Validation

Run validation on every pull request to catch drift before merging:

```yaml
# GitHub Actions example
on:
  pull_request:
    branches: [ main ]

jobs:
  validate:
    steps:
      - name: Validate API
        run: acv validate spec.yaml --api-url ${{ secrets.STAGING_API_URL }}
```

### 2. Post-deployment Verification

Validate the deployed API matches its contract:

```yaml
# After deployment step
- name: Verify deployed API
  run: |
    acv validate openapi.yaml \
      --api-url https://api.production.com \
      --config config/strict.yaml
    
    # Fail if critical drift detected
    if [ $(jq '.summary.critical_count' reports/drift_report.json) -gt 0 ]; then
      exit 1
    fi
```

### 3. Scheduled Monitoring

Run periodic checks to detect drift over time:

```yaml
# GitHub Actions scheduled workflow
on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours

jobs:
  monitor:
    steps:
      - name: Monitor API drift
        run: acv validate spec.yaml --api-url ${{ secrets.API_URL }}
      
      - name: Send alerts
        if: failure()
        run: # Send Slack/email notification
```

### 4. Contract Testing in Feature Branches

Validate feature branch changes don't break contracts:

```yaml
- name: Compare with main
  run: |
    # Checkout main branch spec
    git show origin/main:openapi.yaml > spec-main.yaml
    
    # Validate current changes
    acv validate openapi.yaml --api-url http://localhost:5000
    
    # Compare drift reports
    # (Custom script to compare drift_report.json files)
```

## Environment Variables

All pipelines support these environment variables:

```bash
# Required for AI analysis
ANTHROPIC_API_KEY=your-api-key

# Optional configuration overrides
ACV_EXECUTION_PARALLEL_WORKERS=20
ACV_AI_ANALYSIS_ENABLED=true
ACV_REPORTING_OUTPUT_DIRECTORY=./reports

# API endpoint configuration
API_URL=https://api.staging.example.com
API_AUTH_TOKEN=your-token
```

## Best Practices

### 1. **Cache Dependencies**
Speed up builds by caching pip packages:

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('pyproject.toml') }}
```

### 2. **Parallel Testing**
Run tests across multiple Python versions in parallel:

```yaml
strategy:
  matrix:
    python-version: ["3.10", "3.11", "3.12"]
```

### 3. **Artifact Preservation**
Always save validation reports for debugging:

```yaml
- uses: actions/upload-artifact@v4
  if: always()
  with:
    name: validation-reports
    path: ./reports/
```

### 4. **Fail on Critical Drift**
Block deployment if critical issues are found:

```bash
CRITICAL_COUNT=$(jq '.summary.critical_count' reports/drift_report.json)
if [ "$CRITICAL_COUNT" -gt 0 ]; then
  echo "Critical drift detected!"
  exit 1
fi
```

### 5. **Separate Test and Production APIs**
Use different API URLs for different environments:

```yaml
env:
  STAGING_API: https://api.staging.example.com
  PRODUCTION_API: https://api.example.com
```

## Troubleshooting

### Mock API Not Starting
Add sufficient sleep time after starting mock server:

```bash
python examples/mock_apis/users_api.py &
sleep 5  # Give server time to start
```

### Coverage Upload Failures
Set `fail_ci_if_error: false` for coverage uploads:

```yaml
- uses: codecov/codecov-action@v4
  with:
    fail_ci_if_error: false
```

### Authentication Issues
For APIs requiring authentication, pass tokens via environment:

```bash
export API_AUTH_TOKEN="${{ secrets.API_TOKEN }}"
acv validate spec.yaml --api-url $API_URL
```

## Advanced Configurations

### Progressive Drift Tracking

Track drift over time by storing reports:

```yaml
- name: Store drift history
  run: |
    mkdir -p drift-history
    cp reports/drift_report.json \
       drift-history/drift-$(date +%Y%m%d-%H%M%S).json
    
- uses: actions/upload-artifact@v4
  with:
    name: drift-history
    path: drift-history/
```

### Multi-environment Validation

Validate across multiple environments:

```yaml
jobs:
  validate:
    strategy:
      matrix:
        environment: [staging, production]
    steps:
      - name: Validate ${{ matrix.environment }}
        run: |
          acv validate spec.yaml \
            --api-url ${{ secrets[format('{0}_API_URL', matrix.environment)] }}
```

### Custom Reporting

Generate custom reports from JSON output:

```bash
python scripts/generate_custom_report.py \
  --input reports/drift_report.json \
  --output reports/custom_report.html
```

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [API Contract Validator Documentation](../README.md)
- [OpenAPI Specification](https://swagger.io/specification/)

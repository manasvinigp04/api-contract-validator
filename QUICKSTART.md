# Quick Start for End Users

## What is API Contract Validator?

A CLI tool that automatically validates your live API against its OpenAPI specification, detecting drift and providing AI-powered insights.

## Installation (After Publishing)

```bash
pip install api-contract-validator
acv --version
```

## 5-Minute Integration

### 1. In ANY Project Directory

```bash
cd /path/to/your-project

# Install the tool
pip install api-contract-validator
```

### 2. Create/Place Your OpenAPI Spec

```bash
# If you have an OpenAPI spec
cp your-api-spec.yaml api-spec.yaml

# If you don't have one, create a minimal one
cat > api-spec.yaml << 'EOF'
openapi: 3.0.0
info:
  title: My API
  version: 1.0.0
paths:
  /api/health:
    get:
      responses:
        '200':
          description: Health check
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
EOF
```

### 3. Validate Your API

```bash
# Start your API first (if not already running)
# python manage.py runserver  # Django
# npm start                    # Node.js
# flask run                    # Flask

# Run validation
acv validate api-spec.yaml --api-url http://localhost:8000

# View results
ls reports/
cat reports/drift_report.md
```

That's it! 🎉

## Add to Your Workflow

### For Python Projects

**requirements.txt:**
```txt
api-contract-validator>=0.1.0
```

**Makefile:**
```makefile
validate-api:
	acv validate api-spec.yaml --api-url http://localhost:8000
```

**Usage:**
```bash
make validate-api
```

### For Node.js Projects

**Install:**
```bash
pip install api-contract-validator
```

**package.json:**
```json
{
  "scripts": {
    "validate-api": "acv validate api-spec.yaml --api-url http://localhost:3000"
  }
}
```

**Usage:**
```bash
npm run validate-api
```

### For Any Project (Shell Script)

**validate.sh:**
```bash
#!/bin/bash
set -e

# Start your API (adjust as needed)
npm start &
API_PID=$!
sleep 3

# Run validation
acv validate api-spec.yaml --api-url http://localhost:3000

# Cleanup
kill $API_PID

echo "✅ API validation complete!"
```

**Usage:**
```bash
chmod +x validate.sh
./validate.sh
```

## CI/CD Integration (GitHub Actions)

**.github/workflows/api-check.yml:**
```yaml
name: API Validation

on: [pull_request, push]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - run: pip install api-contract-validator
      
      - run: |
          npm start &
          sleep 3
          acv validate api-spec.yaml --api-url http://localhost:3000
```

## Commands Overview

```bash
# Parse spec (syntax check)
acv parse api-spec.yaml

# Generate test cases
acv generate-tests api-spec.yaml -o tests.json

# Validate API
acv validate api-spec.yaml --api-url http://localhost:8000

# Check configuration
acv config-check

# Get help
acv --help
```

## Common Use Cases

### Scenario 1: Local Development
```bash
# Quick check before committing
acv validate api-spec.yaml --api-url http://localhost:8000
```

### Scenario 2: Pre-deployment
```bash
# Validate staging before production deploy
acv validate api-spec.yaml --api-url https://staging-api.example.com
```

### Scenario 3: Continuous Monitoring
```bash
# In cron or scheduled job
acv validate api-spec.yaml --api-url https://api.example.com
```

### Scenario 4: Multiple Environments
```bash
# Validate all environments
for ENV in dev staging prod; do
  acv validate api-spec.yaml --api-url "https://${ENV}-api.example.com"
done
```

## Authentication

### API Key
```bash
acv validate api-spec.yaml \
  --api-url https://api.example.com \
  --header "X-API-Key: your-key"
```

### Bearer Token
```bash
acv validate api-spec.yaml \
  --api-url https://api.example.com \
  --header "Authorization: Bearer YOUR_TOKEN"
```

## Next Steps

1. ✅ Install: `pip install api-contract-validator`
2. ✅ Add your OpenAPI spec to your project
3. ✅ Run validation: `acv validate spec.yaml --api-url YOUR_URL`
4. ✅ Integrate into your workflow (Makefile/npm scripts/CI)
5. ✅ Monitor and iterate

## Need Help?

- **Full Integration Guide**: See `docs/INTEGRATION_GUIDE.md`
- **Usage Examples**: See `docs/USAGE_EXAMPLES.md`
- **CI/CD Setup**: See `docs/CI_CD_INTEGRATION.md`
- **Report Issues**: https://github.com/yourusername/api-contract-validator/issues

## What It Does

```
OpenAPI Spec → Parse → Generate Tests → Execute → Detect Drift → Report
```

**Input:** OpenAPI specification + Live API URL  
**Output:** Validation reports showing:
- ✅ What matches the contract
- ❌ What doesn't match (drift)
- 💡 AI-powered suggestions to fix issues

**Detects:**
- Missing/extra fields in responses
- Type mismatches
- Validation gaps (invalid data accepted)
- Behavioral inconsistencies

That's all you need to get started! 🚀

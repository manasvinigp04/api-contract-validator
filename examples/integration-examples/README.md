# Integration Examples

This directory contains complete examples showing how to integrate the API Contract Validator into different types of projects.

## Available Examples

### 1. Django REST Framework Project
- Location: `django-project/`
- Shows: Integration with Django REST API
- Features: Custom management command, CI/CD integration

### 2. Flask API Project
- Location: `flask-project/`
- Shows: Integration with Flask REST API
- Features: Makefile commands, Docker integration

### 3. FastAPI Project
- Location: `fastapi-project/`
- Shows: Integration with FastAPI
- Features: Automated testing, pre-commit hooks

### 4. Node.js/Express Project
- Location: `nodejs-project/`
- Shows: Cross-language integration
- Features: npm scripts, validation in tests

### 5. Microservices Architecture
- Location: `microservices/`
- Shows: Multi-service validation
- Features: Parallel validation, aggregate reporting

## Quick Start

Each example includes:
- `README.md` - Setup and usage instructions
- OpenAPI specification
- Configuration files
- Integration scripts
- CI/CD workflow example

## Usage

```bash
# Navigate to an example
cd examples/integration-examples/django-project

# Follow the README
cat README.md

# Try it out
./run-validation.sh
```

## Common Integration Patterns

### Pattern 1: Pre-commit Validation
Validate OpenAPI spec syntax before committing:
```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: api-spec-parse
      name: Parse API Specification
      entry: acv parse
      args: [docs/openapi.yaml]
      language: system
```

### Pattern 2: CI/CD Gate
Block merges if API contract is violated:
```yaml
# .github/workflows/api-check.yml
- name: Validate API
  run: acv validate spec.yaml --api-url $API_URL
- name: Fail on critical drift
  run: |
    CRITICAL=$(jq '.summary.critical_count' reports/drift_report.json)
    test $CRITICAL -eq 0
```

### Pattern 3: Scheduled Monitoring
Monitor production APIs continuously:
```yaml
# .github/workflows/monitor.yml
on:
  schedule:
    - cron: '0 */6 * * *'
jobs:
  monitor:
    runs-on: ubuntu-latest
    steps:
      - run: acv validate spec.yaml --api-url $PROD_API_URL
```

### Pattern 4: Local Development
Validate during development:
```bash
# Watch mode (pseudo-code)
watchman-make -p 'api/**/*.py' -t validate-api
```

## Contributing Examples

Have a unique integration? Contribute your example:

1. Create a directory: `examples/integration-examples/your-framework/`
2. Include:
   - `README.md` with setup instructions
   - Working code example
   - OpenAPI specification
   - Integration scripts
3. Submit a pull request

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

# Django REST Framework + API Contract Validator

This example shows how to integrate the API Contract Validator into a Django REST Framework project.

## Project Structure

```
django-project/
├── manage.py
├── myproject/
│   ├── settings.py
│   └── urls.py
├── api/
│   ├── views.py
│   ├── serializers.py
│   └── urls.py
├── docs/
│   └── openapi.yaml          # API specification
├── config/
│   └── acv-config.yaml       # Validator config
├── scripts/
│   └── validate_api.py       # Custom management command
├── requirements.txt
└── .github/
    └── workflows/
        └── api-validation.yml
```

## Setup

### 1. Install Dependencies

```bash
# requirements.txt
Django==4.2.0
djangorestframework==3.14.0
api-contract-validator>=0.1.0

# Install
pip install -r requirements.txt
```

### 2. Add Configuration

**config/acv-config.yaml:**
```yaml
test_generation:
  max_tests_per_endpoint: 25
  enable_prioritization: true

execution:
  parallel_workers: 10
  timeout_seconds: 30
  headers:
    X-Test-Client: "api-validator"

drift_detection:
  detect_contract_drift: true
  detect_validation_drift: true
  detect_behavioral_drift: true

ai_analysis:
  enabled: true

reporting:
  output_directory: "reports/api-validation"
```

### 3. Create OpenAPI Spec

**docs/openapi.yaml:**
```yaml
openapi: 3.0.0
info:
  title: Django API
  version: 1.0.0
servers:
  - url: http://localhost:8000
paths:
  /api/users/:
    get:
      summary: List users
      responses:
        '200':
          description: List of users
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/User'
    post:
      summary: Create user
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UserCreate'
      responses:
        '201':
          description: User created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'

components:
  schemas:
    User:
      type: object
      required:
        - id
        - email
        - username
      properties:
        id:
          type: integer
        email:
          type: string
          format: email
        username:
          type: string
        created_at:
          type: string
          format: date-time
    
    UserCreate:
      type: object
      required:
        - email
        - username
      properties:
        email:
          type: string
          format: email
        username:
          type: string
          minLength: 3
          maxLength: 50
```

## Integration Methods

### Method 1: Management Command

**scripts/validate_api.py:**
```python
#!/usr/bin/env python
"""
Django management command for API contract validation.
"""
import subprocess
import sys
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Validate API against OpenAPI contract'

    def add_arguments(self, parser):
        parser.add_argument(
            '--api-url',
            default='http://localhost:8000',
            help='API base URL'
        )
        parser.add_argument(
            '--config',
            default='config/acv-config.yaml',
            help='Validator config file'
        )

    def handle(self, *args, **options):
        api_url = options['api_url']
        config = options['config']
        
        self.stdout.write('Starting API contract validation...')
        
        try:
            result = subprocess.run([
                'acv', 'validate',
                'docs/openapi.yaml',
                '--api-url', api_url,
                '--config', config
            ], capture_output=True, text=True)
            
            self.stdout.write(result.stdout)
            
            if result.returncode != 0:
                self.stderr.write(self.style.ERROR(result.stderr))
                sys.exit(1)
            else:
                self.stdout.write(self.style.SUCCESS('✅ Validation passed'))
        
        except FileNotFoundError:
            self.stderr.write(
                self.style.ERROR('acv command not found. Install: pip install api-contract-validator')
            )
            sys.exit(1)
```

**Install as management command:**
```bash
mkdir -p myproject/management/commands
cp scripts/validate_api.py myproject/management/commands/
```

**Usage:**
```bash
python manage.py validate_api
python manage.py validate_api --api-url http://staging.example.com
```

### Method 2: Makefile Commands

**Makefile:**
```makefile
.PHONY: help runserver test validate-api validate-api-prod

help:
	@echo "Available commands:"
	@echo "  make runserver        - Start development server"
	@echo "  make test            - Run Django tests"
	@echo "  make validate-api    - Validate API contract (local)"
	@echo "  make validate-api-prod - Validate production API"

runserver:
	python manage.py runserver

test:
	python manage.py test

validate-api:
	@echo "Starting Django server..."
	@python manage.py runserver > /dev/null 2>&1 & echo $$! > .server.pid
	@sleep 3
	@echo "Running API validation..."
	@acv validate docs/openapi.yaml \
		--api-url http://localhost:8000 \
		--config config/acv-config.yaml || \
		(kill `cat .server.pid`; rm .server.pid; exit 1)
	@echo "Stopping server..."
	@kill `cat .server.pid` && rm .server.pid
	@echo "✅ Validation complete"

validate-api-prod:
	acv validate docs/openapi.yaml \
		--api-url https://api.production.com \
		--config config/acv-config.yaml
```

**Usage:**
```bash
make validate-api
make validate-api-prod
```

### Method 3: pytest Integration

**tests/test_api_contract.py:**
```python
import pytest
import subprocess
from django.test import LiveServerTestCase


class APIContractTest(LiveServerTestCase):
    """Test API contract compliance."""
    
    def test_api_contract_validation(self):
        """Validate API against OpenAPI specification."""
        result = subprocess.run([
            'acv', 'validate',
            'docs/openapi.yaml',
            '--api-url', self.live_server_url,
            '--config', 'config/acv-config.yaml'
        ], capture_output=True, text=True)
        
        # Check for critical drift
        if 'critical_count' in result.stdout:
            assert 'critical_count: 0' in result.stdout, \
                "Critical API drift detected"
        
        assert result.returncode == 0, \
            f"API validation failed:\n{result.stderr}"
```

**Usage:**
```bash
pytest tests/test_api_contract.py
```

## CI/CD Integration

**.github/workflows/api-validation.yml:**
```yaml
name: API Contract Validation

on:
  pull_request:
    paths:
      - 'api/**'
      - 'docs/openapi.yaml'
  push:
    branches: [main, develop]

jobs:
  validate:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run migrations
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost/test_db
        run: |
          python manage.py migrate
      
      - name: Start Django server
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost/test_db
        run: |
          python manage.py runserver &
          sleep 5
      
      - name: Validate API contract
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          acv validate docs/openapi.yaml \
            --api-url http://localhost:8000 \
            --config config/acv-config.yaml
      
      - name: Upload validation reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: api-validation-reports
          path: reports/
      
      - name: Check for critical drift
        run: |
          if [ -f reports/api-validation/drift_report.json ]; then
            CRITICAL=$(jq '.summary.critical_count' reports/api-validation/drift_report.json)
            if [ "$CRITICAL" -gt 0 ]; then
              echo "❌ Critical API drift detected: $CRITICAL issues"
              exit 1
            fi
          fi
```

## Pre-commit Hook

**.pre-commit-config.yaml:**
```yaml
repos:
  - repo: local
    hooks:
      - id: validate-openapi-syntax
        name: Validate OpenAPI Syntax
        entry: acv parse
        args: [docs/openapi.yaml]
        language: system
        files: docs/openapi.yaml
        pass_filenames: false
```

## Usage Examples

### Development Workflow

```bash
# 1. Make API changes
vim api/views.py

# 2. Update OpenAPI spec
vim docs/openapi.yaml

# 3. Validate locally
make validate-api

# 4. Commit if validation passes
git add api/ docs/
git commit -m "feat: add new user endpoint"
```

### Pre-deployment Check

```bash
# Validate staging before promoting to production
acv validate docs/openapi.yaml \
  --api-url https://api-staging.example.com \
  --config config/acv-config.yaml

# Check reports
cat reports/api-validation/drift_report.md

# If OK, deploy to production
```

### Continuous Monitoring

```bash
# Schedule in cron
# Validate production API every 6 hours
0 */6 * * * cd /path/to/project && acv validate docs/openapi.yaml --api-url https://api.production.com
```

## Troubleshooting

### Issue: Django server not starting in CI

**Solution:** Ensure database is configured and migrations are run:
```yaml
- run: python manage.py migrate --no-input
- run: python manage.py runserver &
- run: sleep 5  # Wait for server to start
```

### Issue: Authentication required

**Solution:** Generate test token and use in headers:
```yaml
execution:
  headers:
    Authorization: "Token YOUR_TEST_TOKEN"
```

### Issue: CORS errors during validation

**Solution:** Add validator to ALLOWED_HOSTS and configure CORS:
```python
# settings.py
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']
CORS_ALLOW_ALL_ORIGINS = True  # For testing only
```

## Best Practices

1. **Keep OpenAPI spec in sync** with code changes
2. **Validate on every PR** that touches API code
3. **Use separate configs** for dev/staging/prod
4. **Monitor production** with scheduled validations
5. **Track drift over time** by archiving reports

## Next Steps

- Customize `config/acv-config.yaml` for your needs
- Add more endpoints to `docs/openapi.yaml`
- Integrate validation into your test suite
- Set up CI/CD pipeline
- Configure monitoring and alerting

For more information, see the [Integration Guide](../../docs/INTEGRATION_GUIDE.md).

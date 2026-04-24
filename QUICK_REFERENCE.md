# API Contract Validator - Quick Reference Card

## Installation
```bash
pip install api-contract-validator
```

## Basic Commands
```bash
# Initialize config
acv init

# Validate API
acv validate

# Validate specific environment
acv validate --env staging

# Validate with custom spec
acv validate api/openapi.yaml --api-url https://api.example.com

# Enable advanced features
acv validate --enable-fuzzing --enable-stateful
```

## Configuration File (acv_config.yaml)
```yaml
project:
  spec:
    path: "api/openapi.yaml"

api:
  base_url: "http://localhost:8000"
  environments:
    dev: "http://localhost:8000"
    staging: "https://staging-api.example.com"
    prod: "https://api.example.com"

execution:
  parallel_workers: 10
  timeout_seconds: 30

test_generation:
  generate_valid: true
  generate_invalid: true
  generate_boundary: true

ai_analysis:
  enabled: true
  model: "claude-3-5-sonnet-20241022"
```

## Environment Variables
```bash
export ANTHROPIC_API_KEY="your-api-key"
export ACV_EXECUTION_PARALLEL_WORKERS=20
export ACV_AI_ANALYSIS_ENABLED=true
```

## GitHub Actions
```yaml
- name: Validate API
  run: |
    pip install api-contract-validator
    acv validate api/openapi.yaml --api-url ${{ secrets.API_URL }}
```

## Python Library
```python
from pathlib import Path
from api_contract_validator.input.openapi.parser import OpenAPIParser
from api_contract_validator.generation.test_generator import MasterTestGenerator
from api_contract_validator.execution.runner.executor import TestExecutor

parser = OpenAPIParser()
spec = parser.parse_file(Path("api/openapi.yaml"))

generator = MasterTestGenerator()
test_suite = generator.generate_test_suite(spec)

executor = TestExecutor("https://api.example.com")
results = executor.execute_tests_sync(test_suite.test_cases)
```

## Common Issues

**"Command not found: acv"**
```bash
pip install api-contract-validator
# Or add to PATH: export PATH="$PATH:$HOME/.local/bin"
```

**"No module named 'api_contract_validator'"**
```bash
pip install --upgrade api-contract-validator
```

**"API unreachable"**
```bash
# Check API is running
curl https://api.example.com/health

# Check SSL verification
acv validate --no-verify-ssl
```

## Documentation
- **Full docs**: [README.md](README.md)
- **Quick start**: [QUICKSTART.md](QUICKSTART.md)
- **Demos**: [demo/README.md](demo/README.md)

## Support
- GitHub Issues: (your repo URL)
- License: MIT

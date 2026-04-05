# API Contract Validator

A sophisticated API contract validation system with multi-fidelity input support, intelligent test generation, and multi-dimensional drift detection.

## Features

- **Multi-fidelity Input Support**: Parse both OpenAPI 3.0 specifications and semi-structured PRD documents
- **Intelligent Test Generation**: Automatically generate valid, invalid, and boundary test cases
- **Parallel Test Execution**: Execute tests efficiently with configurable parallelism
- **Multi-dimensional Drift Detection**: Detect contract, validation, behavioral, and progressive drift
- **AI-Assisted Analysis**: Leverage Claude API for root cause analysis and remediation suggestions
- **Rich Reporting**: Generate Markdown and JSON reports with actionable insights
- **CI/CD Integration**: Seamless integration with GitHub Actions, GitLab CI, and other platforms

## Installation

### For End Users (After Publishing to PyPI)

```bash
# Install from PyPI
pip install api-contract-validator

# Verify installation
acv --version

# Download spaCy model (optional - only for PRD parsing)
python -m spacy download en_core_web_sm
```

### For Development

```bash
# Clone the repository
git clone <repository-url>
cd api-contract-validator

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install package with dev dependencies
pip install -e ".[dev]"

# Download spaCy language model
python -m spacy download en_core_web_sm

# Install pre-commit hooks
pre-commit install
```

## Quick Start

### Option 1: Using the CLI

```bash
# 1. Check configuration
acv config-check

# 2. Parse an OpenAPI specification
acv parse examples/openapi/sample_users_api.yaml

# 3. Generate test cases
acv generate-tests examples/openapi/sample_users_api.yaml -o tests/generated_tests.json

# 4. Validate API
acv validate examples/openapi/sample_users_api.yaml --api-url https://api.example.com
```

### Option 2: Using the REST API Server

```bash
# 1. Start the FastAPI server
uvicorn api_contract_validator.api.server:app --reload --port 8000

# 2. Open API documentation
open http://localhost:8000/docs

# 3. Use the REST endpoints
curl -X POST http://localhost:8000/validate \
  -F "spec_file=@openapi.yaml" \
  -F 'validation_request={"api_url": "https://api.example.com", "parallel_workers": 10}'
```

### Option 3: Using as a Python Library

```python
from pathlib import Path
from api_contract_validator.input.openapi.parser import OpenAPIParser
from api_contract_validator.generation.test_generator import MasterTestGenerator
from api_contract_validator.execution.runner.executor import TestExecutor

# Parse specification
parser = OpenAPIParser()
spec = parser.parse_file(Path("openapi.yaml"))

# Generate and execute tests
generator = MasterTestGenerator()
test_suite = generator.generate_test_suite(spec)

executor = TestExecutor("https://api.example.com")
results = executor.execute_tests_sync(test_suite.test_cases)
```

**See [Usage Examples](docs/USAGE_EXAMPLES.md) and [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) for more detailed examples.**

## Configuration

Create a `config.yaml` file (see `config/default.yaml` for template):

```yaml
# Test execution settings
execution:
  parallel_workers: 10
  timeout_seconds: 30
  retry_attempts: 3

# Test generation settings
test_generation:
  generate_valid: true
  generate_invalid: true
  generate_boundary: true
  max_tests_per_endpoint: 50
  enable_prioritization: true

# AI analysis (requires ANTHROPIC_API_KEY)
ai_analysis:
  enabled: true
  model: "claude-3-5-sonnet-20241022"
```

Use with:

```bash
acv validate spec.yaml --api-url https://api.example.com --config config.yaml
```

**See [Usage Examples](docs/USAGE_EXAMPLES.md) for configuration examples for different scenarios.**

## Environment Variables

```bash
export ANTHROPIC_API_KEY="your-api-key"          # For AI analysis
export ACV_EXECUTION_PARALLEL_WORKERS=20         # Override config
export ACV_AI_ANALYSIS_ENABLED=true              # Enable/disable AI
export ACV_REPORTING_OUTPUT_DIRECTORY=./reports  # Output directory
```

## Architecture

```
src/api_contract_validator/
├── api/                # FastAPI REST server
├── cli/                # CLI interface
├── input/              # Input processing (OpenAPI, PRD)
├── schema/             # Contract modeling and validation
├── generation/         # Test case generation
├── execution/          # Test execution engine
├── analysis/           # Drift detection and AI analysis
├── reporting/          # Report generation
└── config/             # Configuration management
```

### Usage Modes

The validator can be used in three ways:

1. **CLI Tool** - Command-line interface for direct usage (`acv validate ...`)
2. **REST API** - FastAPI server for web service integration (`uvicorn api_contract_validator.api.server:app`)
3. **Python Library** - Import and use in your Python code (`from api_contract_validator import ...`)

See [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) for detailed integration instructions.

## Development

### Run Tests

```bash
pytest
pytest --cov=api_contract_validator --cov-report=html
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/

# Or use pre-commit hooks
pre-commit run --all-files
```

**See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed development guidelines.**

## Project Status

### ✅ Completed (Phases 1-7)

- **Phase 1: Foundation** - Project structure, CLI, configuration, logging
- **Phase 2: Input Processing** - OpenAPI parser, PRD parser, reference resolution
- **Phase 3: Contract Modeling** - Contract models, constraint extraction, rules engine
- **Phase 4: Test Generation** - Valid, invalid, boundary test generators with prioritization
- **Phase 5: Test Execution** - Async HTTP executor with retry logic and result collection
- **Phase 6: Drift Detection** - Contract, validation, behavioral drift detectors
- **Phase 7: Reporting & Analysis** - AI-assisted analysis, Markdown/JSON/CLI reports

### 📋 Next Steps

- Expand test coverage
- Add more example specifications
- Performance optimization
- Additional documentation

## Documentation

- **[Integration Guide](INTEGRATION_GUIDE.md)** - Install as library/plugin, REST API usage, CI/CD integration
- **[API Server Guide](src/api_contract_validator/api/README.md)** - FastAPI/Uvicorn server documentation
- **[Usage Examples](docs/USAGE_EXAMPLES.md)** - Comprehensive usage scenarios and patterns
- **[CI/CD Integration](docs/CI_CD_INTEGRATION.md)** - GitHub Actions workflow setup
- **[Publishing Guide](docs/PUBLISHING.md)** - How to publish to PyPI
- **[Contributing Guide](CONTRIBUTING.md)** - Development and contribution guidelines

### Debugging in VS Code

Launch configurations are provided in `.vscode/launch.json`:

- **FastAPI: Uvicorn Server (Development)** - Start the API server with auto-reload
- **FastAPI: Uvicorn Server (Production)** - Start with multiple workers
- **CLI: Validate API** - Debug the CLI validation command

Just press `F5` in VS Code and select your configuration!

## Use Cases

✅ **Pre-merge validation** - Catch API contract violations before merging PRs  
✅ **Post-deployment verification** - Ensure production API matches specification  
✅ **Continuous monitoring** - Detect drift in live APIs over time  
✅ **Regression testing** - Compare API behavior across versions  
✅ **Contract-first development** - TDD approach for API development

## License

MIT License

## Contributing

Contributions welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
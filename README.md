# API Contract Validator

A sophisticated API contract validation system with multi-fidelity input support, intelligent test generation, and multi-dimensional drift detection.

## 🚀 Quick Start for Using ACV in Your Project

**See [QUICKSTART.md](QUICKSTART.md) for the complete guide.**

```bash
# 1. Install ACV in your project (editable mode for live updates)
pip install -e /Users/I764709/api-contract-validator

# 2. Initialize configuration
acv init

# 3. Run validation (ensure your API is running)
acv validate
```

**Key Benefit**: Changes you make to ACV code are **immediately available** in all your projects—no reinstall needed!

## Features

- **Multi-fidelity Input Support**: Parse both OpenAPI 3.0 specifications and semi-structured PRD documents
- **Intelligent Test Generation**: Automatically generate valid, invalid, and boundary test cases
- **Parallel Test Execution**: Execute tests efficiently with configurable parallelism (default: 10 workers)
- **Multi-dimensional Drift Detection**: Detect contract, validation, behavioral, and progressive drift
- **AI-Assisted Analysis**: Leverage Claude API for root cause analysis and remediation suggestions
- **Rich Reporting**: Generate Markdown and JSON reports with actionable insights
- **CI/CD Integration**: Seamless integration with GitHub Actions, GitLab CI, and other platforms
- **Multiple Usage Modes**: Use as CLI tool, REST API server, or Python library
- **Reusable Library**: Install once, use in any project with automatic live updates

## Installation

### Using ACV in Your Project (Recommended)

Install ACV as a reusable library in any project with **editable mode** for live updates:

```bash
# Install in editable mode
pip install -e /Users/I764709/api-contract-validator

# Initialize in your project
acv init

# Run validation
acv validate
```

Add to your `requirements.txt`:
```txt
-e /Users/I764709/api-contract-validator
```

**Why `-e` flag?**
- Changes to ACV code are immediately available in all projects
- No reinstall needed after updates
- Perfect for continuous development and testing

**📖 Complete setup guide:** [QUICKSTART.md](QUICKSTART.md)

### For End Users (After Publishing to PyPI)

```bash
# Install from PyPI
pip install api-contract-validator

# Verify installation
acv --version

# Download spaCy model (optional - only for PRD parsing)
python -m spacy download en_core_web_sm
```

### For ACV Development

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

### Option 1: Using ACV with acv_config.yaml (Recommended)

```bash
# In your project directory
acv init  # Creates acv_config.yaml

# Edit acv_config.yaml to point to your spec and API
vim acv_config.yaml

# Run validation
acv validate

# Or validate against specific environment
acv validate --env dev
acv validate --env staging
```

### Option 2: Using the CLI with Arguments

```bash
# Check configuration
acv config-check

# Parse an OpenAPI specification
acv parse examples/openapi/sample_users_api.yaml

# Generate test cases
acv generate-tests examples/openapi/sample_users_api.yaml -o tests/generated_tests.json

# Validate API
acv validate examples/openapi/sample_users_api.yaml --api-url https://api.example.com
```

### Option 3: Using the REST API Server

```bash
# Start the FastAPI server
uvicorn api_contract_validator.api.server:app --reload --port 9000

# Open API documentation
open http://localhost:9000/docs

# Use the REST endpoints
curl -X POST http://localhost:9000/validate \
  -F "spec_file=@openapi.yaml" \
  -F 'validation_request={"api_url": "https://api.example.com", "parallel_workers": 10}'
```

### Option 4: Using as a Python Library

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

**See [QUICKSTART.md](QUICKSTART.md) for more detailed examples including pytest integration and custom scripts.**

## Configuration

### Using acv_config.yaml (Recommended)

Create `acv_config.yaml` in your project root:

```bash
# Initialize interactively
acv init

# Or initialize with values
acv init --spec-path api/openapi.yaml --api-url http://localhost:8000
```

Example `acv_config.yaml`:

```yaml
project:
  spec:
    path: "api/openapi.yaml"
  output:
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

test_generation:
  generate_valid: true
  generate_invalid: true
  generate_boundary: true
  max_tests_per_endpoint: 50
  enable_prioritization: true

ai_analysis:
  enabled: true
  model: "claude-3-5-sonnet-20241022"
```

Run with config:
```bash
acv validate                  # Uses acv_config.yaml
acv validate --env dev        # Uses dev environment from config
acv validate --parallel 20    # Override specific settings
```

### Using Command-Line Config

```bash
acv validate spec.yaml --api-url https://api.example.com --config config.yaml
```

**See [acv_config.yaml.template](acv_config.yaml.template) for all available options.**

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
3. **Python Library** - Import and use in your Python code

See [QUICKSTART.md](QUICKSTART.md) for detailed examples of each usage mode.

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

### ✅ Completed (Phases 1-7)

- **Phase 1: Foundation** - Project structure, CLI, configuration, logging
- **Phase 2: Input Processing** - OpenAPI parser, PRD parser, reference resolution
- **Phase 3: Contract Modeling** - Contract models, constraint extraction, rules engine
- **Phase 4: Test Generation** - Valid, invalid, boundary test generators with prioritization
- **Phase 5: Test Execution** - Async HTTP executor with retry logic and result collection
- **Phase 6: Drift Detection** - Contract, validation, behavioral drift detectors
- **Phase 7: Reporting & Analysis** - AI-assisted analysis, Markdown/JSON/CLI reports

### 🎯 Current State

✅ **Production-ready** as a reusable library  
✅ **Live update support** via editable install  
✅ **Project-based configuration** with `acv_config.yaml`  
✅ **Multi-environment support** (local/dev/staging/prod)  
✅ **Complete documentation** in README.md and QUICKSTART.md

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Complete setup guide with examples, architecture, and REST API documentation
- **[acv_config.yaml.template](acv_config.yaml.template)** - Configuration template with all available options

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
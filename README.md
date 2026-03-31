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

```bash
# Clone the repository
git clone <repository-url>
cd api-contract-validator

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install package
pip install -e ".[dev]"

# Download spaCy language model
python -m spacy download en_core_web_sm
```

## Quick Start

### 1. Check Configuration

```bash
acv config-check
```

### 2. Parse an OpenAPI Specification

```bash
acv parse path/to/openapi.yaml
```

### 3. Generate Test Cases

```bash
acv generate-tests path/to/openapi.yaml -o tests/generated_tests.json
```

### 4. Validate API

```bash
acv validate path/to/openapi.yaml --api-url https://api.example.com
```

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
├── cli/                 # CLI interface
├── input/              # Input processing (OpenAPI, PRD)
├── schema/             # Contract modeling and validation
├── generation/         # Test case generation
├── execution/          # Test execution engine
├── analysis/           # Drift detection and AI analysis
├── reporting/          # Report generation
└── config/             # Configuration management
```

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
```

## Project Status

### ✅ Completed (Phases 1-7)

- **Phase 1: Foundation** - Project structure, CLI, configuration, logging
- **Phase 2: Input Processing** - OpenAPI parser, PRD parser, reference resolution
- **Phase 3: Contract Modeling** - Contract models, constraint extraction, rules engine
- **Phase 4: Test Generation** - Valid, invalid, boundary test generators with prioritization
- **Phase 5: Test Execution** - Async HTTP executor with retry logic and result collection
- **Phase 6: Drift Detection** - Contract, validation, behavioral drift detectors
- **Phase 7: Reporting & Analysis** - AI-assisted analysis, Markdown/JSON/CLI reports

### 📋 Remaining

- Phase 8: CI/CD integration examples
- Comprehensive test suite
- Example specifications and PRDs
- Full documentation

## License

MIT License

## Contributing

Contributions welcome! Please see CONTRIBUTING.md for guidelines.
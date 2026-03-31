# Contributing to API Contract Validator

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Release Process](#release-process)

## Code of Conduct

This project adheres to a code of conduct based on respect, inclusivity, and collaboration. We expect all contributors to:

- Be respectful and constructive in communication
- Welcome newcomers and help them get started
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- A GitHub account

### Finding Issues to Work On

- Check the [Issues](https://github.com/yourusername/api-contract-validator/issues) page
- Look for issues labeled `good first issue` or `help wanted`
- Comment on an issue to indicate you're working on it

## Development Setup

1. **Fork and clone the repository**

```bash
git clone https://github.com/YOUR-USERNAME/api-contract-validator.git
cd api-contract-validator
```

2. **Create a virtual environment**

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install development dependencies**

```bash
pip install -e ".[dev]"
python -m spacy download en_core_web_sm
```

4. **Install pre-commit hooks**

```bash
pre-commit install
```

This will automatically run linting, formatting, and type checking before each commit.

## Development Workflow

1. **Create a feature branch**

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

2. **Make your changes**

- Write code following our [code standards](#code-standards)
- Add tests for new functionality
- Update documentation as needed

3. **Run tests locally**

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_drift_models.py

# Run with coverage
pytest --cov=api_contract_validator --cov-report=html
```

4. **Check code quality**

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/

# Or let pre-commit run everything
pre-commit run --all-files
```

5. **Commit your changes**

```bash
git add .
git commit -m "feat: add new drift detection feature"
```

Follow [Conventional Commits](https://www.conventionalcommits.org/) format:
- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation changes
- `test:` adding or updating tests
- `refactor:` code refactoring
- `chore:` maintenance tasks

6. **Push and create a pull request**

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## Code Standards

### Python Style

- Follow [PEP 8](https://pep8.org/) style guide
- Use Black for code formatting (line length: 100)
- Use type hints for function signatures
- Write docstrings for all public functions, classes, and modules

### Code Organization

```python
"""
Module docstring explaining the purpose.
"""

from typing import List, Optional
import external_library

from api_contract_validator.module import LocalClass


class MyClass:
    """
    Class docstring.
    
    Attributes:
        attr: Description of attribute
    """
    
    def __init__(self, param: str) -> None:
        """Initialize with parameter."""
        self.attr = param
    
    def public_method(self, arg: int) -> str:
        """
        Public method with docstring.
        
        Args:
            arg: Description of argument
            
        Returns:
            Description of return value
            
        Raises:
            ValueError: When something is wrong
        """
        return str(arg)
```

### Error Handling

- Use specific exception types from `api_contract_validator.config.exceptions`
- Always provide meaningful error messages
- Log errors appropriately

```python
from api_contract_validator.config.exceptions import ValidationError
from api_contract_validator.config.logging import get_logger

logger = get_logger(__name__)

def validate_data(data: dict) -> None:
    """Validate input data."""
    if not data:
        logger.error("Empty data provided")
        raise ValidationError("Data cannot be empty")
```

### Logging

- Use the centralized logger: `get_logger(__name__)`
- Log levels:
  - `DEBUG`: Detailed diagnostic information
  - `INFO`: General informational messages
  - `WARNING`: Warning messages for recoverable issues
  - `ERROR`: Error messages for failures

## Testing

### Test Structure

```
tests/
├── unit/              # Unit tests for individual components
│   ├── test_drift_models.py
│   └── test_detector.py
└── integration/       # Integration tests for workflows
    └── test_validation_flow.py
```

### Writing Tests

```python
import pytest
from api_contract_validator.module import MyClass


class TestMyClass:
    """Test MyClass functionality."""
    
    @pytest.fixture
    def instance(self):
        """Create test instance."""
        return MyClass(param="test")
    
    def test_basic_functionality(self, instance):
        """Test that basic functionality works."""
        result = instance.public_method(42)
        assert result == "42"
    
    def test_error_handling(self, instance):
        """Test error handling."""
        with pytest.raises(ValueError):
            instance.public_method(-1)
```

### Test Coverage

- Aim for 80%+ code coverage
- All new features must include tests
- Bug fixes should include regression tests

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/unit/test_drift_models.py

# Specific test
pytest tests/unit/test_drift_models.py::TestDriftReport::test_has_issues

# With coverage
pytest --cov=api_contract_validator --cov-report=html

# Skip slow tests
pytest -m "not slow"
```

## Submitting Changes

### Pull Request Process

1. **Update documentation** if you've added or changed functionality
2. **Add tests** for new features or bug fixes
3. **Ensure all tests pass** and coverage is maintained
4. **Update CHANGELOG.md** with your changes (under "Unreleased")
5. **Create a pull request** with a clear title and description

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests pass locally
- [ ] CHANGELOG.md updated
```

### Review Process

- All PRs require at least one approval
- CI checks must pass
- Address review comments
- Keep PRs focused and reasonably sized

## Additional Guidelines

### Documentation

- Update README.md for user-facing changes
- Add docstrings to all public APIs
- Create examples for new features
- Update docs/ for architectural changes

### Performance

- Consider performance implications
- Add benchmarks for performance-critical code
- Profile before optimizing

### Security

- Never commit secrets or API keys
- Validate all user inputs
- Use parameterized queries
- Follow OWASP guidelines

### Backwards Compatibility

- Avoid breaking changes when possible
- Deprecate features before removing
- Document migration paths for breaking changes

## Getting Help

- Open a [Discussion](https://github.com/yourusername/api-contract-validator/discussions) for questions
- Comment on relevant issues
- Join our community chat (if available)

## Recognition

Contributors are recognized in:
- CHANGELOG.md for each release
- README.md contributors section
- GitHub contributors page

Thank you for contributing! 🎉

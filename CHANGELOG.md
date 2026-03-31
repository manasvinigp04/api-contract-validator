# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of API Contract Validator
- Multi-fidelity input support (OpenAPI 3.0, PRD documents)
- Intelligent test generation (valid, invalid, boundary cases)
- Parallel test execution with retry logic
- Multi-dimensional drift detection (contract, validation, behavioral)
- AI-assisted analysis with Claude API integration
- Rich reporting (Markdown, JSON, CLI formats)
- Comprehensive CLI interface
- GitHub Actions CI/CD workflow
- Pre-commit hooks for code quality
- Full documentation and usage examples

## [0.1.0] - 2024-03-31

### Added
- Phase 1: Foundation (project structure, CLI, configuration, logging)
- Phase 2: Input processing (OpenAPI parser, PRD parser)
- Phase 3: Contract modeling (constraint extraction, rules engine)
- Phase 4: Test generation (valid, invalid, boundary tests with prioritization)
- Phase 5: Test execution (async HTTP executor with retry logic)
- Phase 6: Drift detection (contract, validation, behavioral detectors)
- Phase 7: Reporting & analysis (AI-assisted analysis, multi-format reports)
- Phase 8: CI/CD integration, testing, documentation

### Documentation
- README with quick start guide
- Contributing guidelines
- Usage examples
- CI/CD integration guide
- Publishing guide

### Infrastructure
- GitHub Actions workflow
- Pre-commit hooks
- Unit test suite
- Code quality tooling (Black, Ruff, mypy)

[Unreleased]: https://github.com/yourusername/api-contract-validator/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yourusername/api-contract-validator/releases/tag/v0.1.0

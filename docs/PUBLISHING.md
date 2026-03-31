# Publishing to PyPI

This guide explains how to publish the API Contract Validator to PyPI so users can install it via `pip install api-contract-validator`.

## Prerequisites

1. PyPI account: https://pypi.org/account/register/
2. TestPyPI account (for testing): https://test.pypi.org/account/register/
3. Create API tokens for both

## One-Time Setup

### 1. Install Build Tools

```bash
pip install build twine
```

### 2. Configure PyPI Credentials

```bash
# Create .pypirc file
cat > ~/.pypirc << EOF
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR-ACTUAL-TOKEN-HERE

[testpypi]
username = __token__
password = pypi-YOUR-TEST-TOKEN-HERE
EOF

chmod 600 ~/.pypirc
```

## Pre-Release Checklist

- [ ] Update version in `pyproject.toml`
- [ ] Update CHANGELOG.md
- [ ] All tests passing
- [ ] Documentation up to date
- [ ] Git tag created for release

## Building the Package

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build distribution packages
python -m build

# Verify contents
ls -lh dist/
# Should see:
# - api_contract_validator-0.1.0-py3-none-any.whl
# - api_contract_validator-0.1.0.tar.gz

# Check package validity
twine check dist/*
```

## Publishing

### Test on TestPyPI First (Recommended)

```bash
# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  api-contract-validator

# Verify it works
acv --version
acv config-check
```

### Publish to PyPI (Production)

```bash
# Upload to PyPI
twine upload dist/*

# Verify on PyPI
# Visit: https://pypi.org/project/api-contract-validator/

# Test installation
pip install api-contract-validator
acv --version
```

## Version Management

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR.MINOR.PATCH** (e.g., 1.2.3)
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

### Update Version

Edit `pyproject.toml`:
```toml
[project]
version = "0.2.0"  # Update this
```

### Create Git Tag

```bash
git tag -a v0.2.0 -m "Release version 0.2.0"
git push origin v0.2.0
```

## Automated Publishing with GitHub Actions

Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install build tools
        run: |
          pip install build twine
      
      - name: Build package
        run: python -m build
      
      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*
```

**Setup:**
1. Add `PYPI_API_TOKEN` to GitHub Secrets
2. Create a release on GitHub
3. Package automatically publishes to PyPI

## Release Workflow

```bash
# 1. Update version
vim pyproject.toml  # Bump version

# 2. Update changelog
vim CHANGELOG.md

# 3. Commit changes
git add pyproject.toml CHANGELOG.md
git commit -m "chore: bump version to 0.2.0"
git push

# 4. Create and push tag
git tag -a v0.2.0 -m "Release version 0.2.0"
git push origin v0.2.0

# 5. Build and publish
python -m build
twine check dist/*
twine upload dist/*

# 6. Create GitHub release
# Go to: https://github.com/yourusername/api-contract-validator/releases/new
# - Tag: v0.2.0
# - Title: Release v0.2.0
# - Description: Copy from CHANGELOG.md
```

## Troubleshooting

### Issue: Package name already taken

```toml
# Use a different name in pyproject.toml
[project]
name = "your-unique-name-api-validator"
```

### Issue: Upload fails

```bash
# Check credentials
cat ~/.pypirc

# Try with explicit repository
twine upload --repository pypi dist/*

# Verbose output
twine upload --verbose dist/*
```

### Issue: Dependencies not installing

```toml
# Ensure dependencies are in pyproject.toml
[project]
dependencies = [
    "pydantic>=2.0.0,<3.0.0",
    # ... all required packages
]
```

## Post-Publication

1. **Verify installation:**
```bash
pip install api-contract-validator
acv --help
```

2. **Update documentation:**
   - Add PyPI badge to README
   - Update installation instructions

3. **Announce:**
   - Create GitHub release notes
   - Post on community channels
   - Update project documentation

## Maintenance

### Patch Release (0.1.0 → 0.1.1)

```bash
# Fix bug
# Update version to 0.1.1
# Build and publish
python -m build && twine upload dist/*
```

### Minor Release (0.1.0 → 0.2.0)

```bash
# Add new feature
# Update version to 0.2.0
# Update docs
# Build and publish
python -m build && twine upload dist/*
```

### Major Release (0.1.0 → 1.0.0)

```bash
# Breaking changes
# Update version to 1.0.0
# Update migration guide
# Build and publish
python -m build && twine upload dist/*
```

## Security

- Never commit `.pypirc` to git
- Use API tokens, not passwords
- Add `.pypirc` to `.gitignore`
- Rotate tokens periodically
- Use GitHub Secrets for CI/CD

## Resources

- [PyPI Publishing Guide](https://packaging.python.org/tutorials/packaging-projects/)
- [Twine Documentation](https://twine.readthedocs.io/)
- [Python Packaging Guide](https://packaging.python.org/)

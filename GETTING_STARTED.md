# API Contract Validator - Getting Started

> **Stop breaking APIs in production. Start validating contracts automatically.**

## What is ACV?

API Contract Validator automatically tests your API against its OpenAPI specification to detect:
- **Contract Drift**: Response doesn't match spec (missing fields, wrong types)
- **Validation Drift**: API accepts invalid inputs it should reject
- **Behavioral Drift**: Performance degradation, error rate changes

**Zero test code required. Just point at your spec and API.**

---

## Install & Run (30 Seconds)

```bash
# 1. Install
pip install api-contract-validator

# 2. Create config
acv init

# 3. Edit config (set your API URL)
vim acv_config.yaml

# 4. Run validation
acv validate

# 5. View results
cat output/drift_report_*.md
```

---

## Complete Documentation

- **[README.md](README.md)** - Full documentation with all features
- **[QUICKSTART.md](QUICKSTART.md)** - Detailed setup guide
- **[demo/README.md](demo/README.md)** - Demo scenarios with complex examples
- **CI/CD Examples** - See README.md for GitHub Actions, GitLab CI, Jenkins

---

## Key Features

✅ **Automatic test generation** from OpenAPI specs  
✅ **Parallel execution** (10x faster)  
✅ **AI-powered analysis** with root cause & fixes  
✅ **70-85% cheaper AI** (vs traditional tools)  
✅ **CI/CD ready** (GitHub Actions, GitLab, Jenkins)  
✅ **8 advanced modes** (fuzzing, stateful, chaos, mutation, etc.)  

---

## Quick Examples

### Basic CLI Usage
```bash
acv validate api/openapi.yaml --api-url https://api.example.com
```

### Multi-Environment Testing
```yaml
# acv_config.yaml
api:
  environments:
    dev: "http://localhost:8000"
    staging: "https://staging-api.example.com"
    prod: "https://api.example.com"
```
```bash
acv validate --env staging
```

### GitHub Actions Integration
```yaml
- name: Validate API Contract
  run: |
    pip install api-contract-validator
    acv validate api/openapi.yaml --api-url ${{ secrets.API_URL }}
```

---

## When to Use ACV

| You Have... | ACV Can... |
|-------------|------------|
| OpenAPI spec + live API | ✅ Auto-test for drift |
| Frequent API changes | ✅ Catch breaking changes |
| Manual API testing | ✅ Save 10+ hours/sprint |
| CI/CD pipeline | ✅ Drop-in integration |
| Security concerns | ✅ Fuzzing for SQL injection, XSS |
| Compliance needs | ✅ HIPAA, SOC2 validation |

---

## Sample Output

```bash
$ acv validate

✓ Parsed specification: 15 endpoints
✓ Generated 342 test cases
✓ Executed in 12 seconds

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DRIFT SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Contract Drift: 8 issues
⚠️  Validation Drift: 15 issues  
⏱️  Behavioral Drift: 2 issues

💡 AI ANALYSIS
Root Cause: Missing input validation middleware
Fix: Add Pydantic models for request validation
Effort: 2-4 hours

Full report: output/drift_report_20260425_103045.md
```

---

## Support

- **Documentation**: [README.md](README.md)
- **Issues**: GitHub Issues (your repo URL)
- **License**: MIT

---

*Prevent breaking changes. Start testing in 30 seconds.*

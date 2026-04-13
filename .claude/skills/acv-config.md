---
name: acv-config
description: Validate ACV configuration files with comprehensive checks (no API calls needed)
---

# ACV Config Validation Skill

Fast, local validation of `acv_config.yaml` files. No Claude API calls - 100% free!

## When to Use

Trigger this skill when the user:
- Creates or edits `acv_config.yaml`
- Runs `acv init`
- Sees config-related errors
- Asks "is my config correct?"
- Before running `acv validate`

## What This Skill Does

1. **Loads config** from `acv_config.yaml` or specified path
2. **Validates syntax** - YAML parsing, structure
3. **Validates fields** - Type checking, constraints, ranges
4. **Cross-field validation** - Logical consistency checks
5. **Environment checks** - Environment-specific rules
6. **Generates report** - Clear errors and warnings with fixes

## Validation Layers

### Layer 1: Syntax Validation
```yaml
# ❌ Bad YAML syntax
project:
  spec:
    path: "api.yaml
  # Missing closing quote

# ✅ Good YAML syntax  
project:
  spec:
    path: "api.yaml"
```

### Layer 2: Type & Constraint Validation
```yaml
# ❌ Invalid types
execution:
  parallel_workers: "ten"  # Should be int
  timeout_seconds: -5      # Should be >= 1

# ✅ Valid types
execution:
  parallel_workers: 10
  timeout_seconds: 30
```

### Layer 3: Cross-Field Validation
```yaml
# ❌ Inconsistent config
drift_detection:
  detect_progressive_drift: true  # Requires storage
storage:
  enabled: false                  # Contradiction!

# ✅ Consistent config
drift_detection:
  detect_progressive_drift: true
storage:
  enabled: true
  storage_type: "tinydb"
```

### Layer 4: Environment-Specific Validation
```yaml
# ❌ Production config issues
environment: "production"
execution:
  verify_ssl: false  # Must be true in prod
logging:
  level: "DEBUG"     # Should be INFO+ in prod

# ✅ Production-ready config
environment: "production"
execution:
  verify_ssl: true
logging:
  level: "INFO"
```

## Workflow

### Step 1: Find Config File
```bash
# Check standard locations
if [ -f "acv_config.yaml" ]; then
    CONFIG="acv_config.yaml"
elif [ -f ".acv/config.yaml" ]; then
    CONFIG=".acv/config.yaml"
elif [ -f "config/default.yaml" ]; then
    CONFIG="config/default.yaml"
else
    echo "❌ No config file found"
    exit 1
fi
```

### Step 2: Load & Parse
```python
import yaml
from pydantic import ValidationError
from api_contract_validator.config.models import Config

try:
    with open(config_path) as f:
        config_dict = yaml.safe_load(f)
except yaml.YAMLError as e:
    print(f"❌ YAML Syntax Error:")
    print(f"   {e}")
    exit(1)
```

### Step 3: Validate Fields
```python
try:
    config = Config(**config_dict)
    print("✅ Field validation passed")
except ValidationError as e:
    print("❌ Validation Errors:")
    for error in e.errors():
        field = '.'.join(str(x) for x in error['loc'])
        print(f"   • {field}: {error['msg']}")
    exit(1)
```

### Step 4: Cross-Field Checks
```python
warnings = []

# Check 1: Test generation enabled?
if not any([
    config.test_generation.generate_valid,
    config.test_generation.generate_invalid,
    config.test_generation.generate_boundary
]):
    warnings.append(
        "⚠️  All test generation disabled - no tests will be generated"
    )

# Check 2: Progressive drift needs storage
if config.drift_detection.detect_progressive_drift:
    if not config.storage.enabled:
        warnings.append(
            "⚠️  Progressive drift requires storage.enabled=true"
        )

# Check 3: AI analysis needs API key
if config.ai_analysis.enabled:
    if not config.ai_analysis.api_key:
        if not os.getenv('ANTHROPIC_API_KEY'):
            warnings.append(
                "⚠️  AI analysis enabled but ANTHROPIC_API_KEY not set"
            )

# Check 4: Parallel workers vs test count
if config.execution.parallel_workers > config.test_generation.max_tests_per_endpoint:
    warnings.append(
        f"⚠️  parallel_workers ({config.execution.parallel_workers}) > "
        f"max_tests_per_endpoint ({config.test_generation.max_tests_per_endpoint})"
    )
```

### Step 5: Environment Checks
```python
if config.environment == "production":
    # Production-specific checks
    if not config.execution.verify_ssl:
        errors.append("❌ SSL verification required in production")
    
    if config.logging.level == "DEBUG":
        warnings.append("⚠️  DEBUG logging not recommended in production")
    
    if not config.storage.enabled:
        warnings.append("⚠️  Storage recommended for production")

elif config.environment == "ci":
    # CI-specific checks
    if config.execution.parallel_workers > 5:
        warnings.append("⚠️  CI should use ≤5 parallel workers")
    
    if config.ai_analysis.enabled:
        warnings.append("⚠️  Consider disabling AI analysis in CI (cost)")
```

### Step 6: Generate Report
```python
print("\n" + "="*60)
print("🔧 CONFIG VALIDATION REPORT")
print("="*60)

print(f"\n📁 Config File: {config_path}")
print(f"🌍 Environment: {config.environment}")

if errors:
    print(f"\n❌ Errors Found ({len(errors)}):")
    for error in errors:
        print(f"   {error}")
    print("\n⚠️  Fix errors before running validation")
    exit(1)

if warnings:
    print(f"\n⚠️  Warnings ({len(warnings)}):")
    for warning in warnings:
        print(f"   {warning}")
else:
    print("\n✨ No warnings!")

print(f"\n✅ Config is valid!")

# Show summary
print(f"\n📊 Configuration Summary:")
print(f"   Parallel Workers: {config.execution.parallel_workers}")
print(f"   Timeout: {config.execution.timeout_seconds}s")
print(f"   Max Tests/Endpoint: {config.test_generation.max_tests_per_endpoint}")
print(f"   AI Analysis: {'Enabled' if config.ai_analysis.enabled else 'Disabled'}")
print(f"   Drift Detection: {sum([
    config.drift_detection.detect_contract_drift,
    config.drift_detection.detect_validation_drift,
    config.drift_detection.detect_behavioral_drift
])} types enabled")
```

## Common Config Issues & Fixes

### Issue 1: Unknown Fields
```yaml
# ❌ Typo in field name
ai_analysis:
  enabeld: true  # Typo!

# Error: Extra inputs are not permitted

# ✅ Fix
ai_analysis:
  enabled: true
```

### Issue 2: Out of Range Values
```yaml
# ❌ Value out of range
execution:
  parallel_workers: 200  # Max is 100

# Error: Input should be less than or equal to 100

# ✅ Fix
execution:
  parallel_workers: 50
```

### Issue 3: Missing Required Dependencies
```yaml
# ❌ Inconsistent settings
drift_detection:
  detect_progressive_drift: true
storage:
  enabled: false  # ← Missing dependency

# Warning: Progressive drift requires storage

# ✅ Fix
drift_detection:
  detect_progressive_drift: true
storage:
  enabled: true
  storage_type: "tinydb"
  database_path: "./snapshots/drift.db"
```

### Issue 4: Invalid Paths
```yaml
# ❌ File doesn't exist
project:
  spec:
    path: "nonexistent.yaml"

# Error: Specification file not found

# ✅ Fix
project:
  spec:
    path: "api/openapi.yaml"  # Correct path
```

### Issue 5: Production Misconfig
```yaml
# ❌ Insecure production config
environment: "production"
execution:
  verify_ssl: false  # Dangerous!
logging:
  level: "DEBUG"     # Too verbose

# ✅ Fix
environment: "production"
execution:
  verify_ssl: true
logging:
  level: "INFO"
```

## Usage Examples

### Example 1: Valid Config
```bash
$ acv config-check

🔧 CONFIG VALIDATION REPORT
============================================================

📁 Config File: acv_config.yaml
🌍 Environment: development

✨ No warnings!
✅ Config is valid!

📊 Configuration Summary:
   Parallel Workers: 10
   Timeout: 30s
   Max Tests/Endpoint: 50
   AI Analysis: Enabled
   Drift Detection: 3 types enabled
```

### Example 2: Config with Warnings
```bash
$ acv config-check

🔧 CONFIG VALIDATION REPORT
============================================================

📁 Config File: acv_config.yaml
🌍 Environment: production

⚠️  Warnings (2):
   ⚠️  DEBUG logging not recommended in production
   ⚠️  Storage recommended for production

✅ Config is valid!

💡 Tip: Run with --strict to treat warnings as errors
```

### Example 3: Config with Errors
```bash
$ acv config-check

🔧 CONFIG VALIDATION REPORT
============================================================

📁 Config File: acv_config.yaml
🌍 Environment: production

❌ Errors Found (3):
   ❌ execution.parallel_workers: Input should be less than or equal to 100
   ❌ ai_analysis.enabeld: Extra inputs are not permitted
   ❌ SSL verification required in production

⚠️  Fix errors before running validation

Exit code: 1
```

### Example 4: Interactive Fix
```bash
$ acv config-check --interactive

❌ Found 2 errors in config

Error 1: execution.verify_ssl should be true in production
  Current: false
  
  Fix automatically? [y/N] y
  ✅ Fixed: verify_ssl = true

Error 2: logging.level should not be DEBUG in production
  Current: DEBUG
  Suggested: INFO
  
  Apply suggestion? [y/N] y
  ✅ Fixed: level = INFO

💾 Saving changes to acv_config.yaml...
✅ Config fixed and saved!
```

## CLI Integration

### Basic Check
```bash
acv config-check
```

### Strict Mode (warnings = errors)
```bash
acv config-check --strict
```

### Check Specific File
```bash
acv config-check --config my_config.yaml
```

### Interactive Fix Mode
```bash
acv config-check --interactive
```

### JSON Output
```bash
acv config-check --json
```

### Pre-Commit Hook
```bash
# .git/hooks/pre-commit
#!/bin/bash
if [ -f "acv_config.yaml" ]; then
    acv config-check --strict || exit 1
fi
```

## Validation Rules Reference

### Execution Config
- `parallel_workers`: 1-100
- `timeout_seconds`: 1-300
- `retry_attempts`: 0-10
- `retry_delay_seconds`: 0.1-10.0
- `verify_ssl`: boolean (must be true in production)

### Test Generation Config
- `max_tests_per_endpoint`: >= 1
- At least one of: `generate_valid`, `generate_invalid`, `generate_boundary` must be true

### AI Analysis Config
- `max_tokens`: 100-10000
- `temperature`: 0.0-1.0
- `api_key`: Required if enabled in production

### Drift Detection Config
- `progressive_drift_history_size`: 2-100
- If `detect_progressive_drift=true`, requires `storage.enabled=true`

### Storage Config
- `max_snapshots`: >= 10
- `retention_days`: >= 1
- `storage_type`: "tinydb" or "sqlite"

### Logging Config
- `level`: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
- Production should use INFO or higher

## Environment-Specific Rules

### Production
- ✅ Must have: `verify_ssl=true`
- ✅ Must have: `logging.level` >= INFO
- ⚠️  Recommended: `storage.enabled=true`
- ⚠️  Recommended: `ai_analysis.enabled=true` with API key

### CI
- ⚠️  `parallel_workers` <= 5 (resource limits)
- ⚠️  Consider disabling `ai_analysis` (cost savings)
- ✅ Must have: `reporting.generate_cli_summary=true`

### Development
- ✅ Flexible settings
- ⚠️  Consider `logging.level=DEBUG` for troubleshooting

## Performance

| Validation | Time | API Calls | Cost |
|------------|------|-----------|------|
| Syntax check | <10ms | 0 | $0 |
| Field validation | <50ms | 0 | $0 |
| Cross-field checks | <100ms | 0 | $0 |
| **Total** | **<200ms** | **0** | **$0** |

**100% local validation - no API costs!**

## Configuration Tips

### 1. Start with Template
```bash
acv init  # Creates acv_config.yaml from template
acv config-check  # Validate
```

### 2. Environment-Specific Configs
```bash
# Create environment configs
acv_config.dev.yaml
acv_config.staging.yaml
acv_config.prod.yaml

# Validate specific env
acv config-check --config acv_config.prod.yaml
```

### 3. Use Environment Variables
```bash
# Override sensitive values
export ANTHROPIC_API_KEY="sk-..."
export ACV_EXECUTION_PARALLEL_WORKERS=20
```

### 4. Version Control
```bash
# .gitignore
acv_config.local.yaml  # Local overrides
.acv_cache/            # Cache directory

# Commit these
acv_config.yaml        # Base config
acv_config.*.yaml      # Environment configs
```

## Troubleshooting

### Issue: "Config file not found"
**Solution:** Run `acv init` or specify path with `--config`

### Issue: "YAML syntax error"
**Solution:** Use a YAML validator or check indentation

### Issue: "Extra inputs not permitted"
**Solution:** Check field names for typos, refer to template

### Issue: "Validation failed but file looks correct"
**Solution:** Check for hidden characters, try recreating from template

## Integration with CI/CD

### GitHub Actions
```yaml
- name: Validate ACV Config
  run: |
    pip install -e .
    acv config-check --strict
```

### GitLab CI
```yaml
validate:config:
  script:
    - acv config-check --strict
  rules:
    - changes:
      - acv_config.yaml
```

### Pre-Commit Hook
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: acv-config-check
        name: Validate ACV Config
        entry: acv config-check --strict
        language: system
        files: acv_config\.yaml$
```

---

**Skill Version:** 1.0  
**Requires:** ACV >= 0.1.0  
**Cost:** $0 (100% local validation)

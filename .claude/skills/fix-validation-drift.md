---
name: fix-validation-drift
description: Automatically fix validation drift issues detected by ACV
---

# Fix Validation Drift Issues

Automatically applies fixes for validation drift issues found in the ACV drift report.

## Context

**Total Validation Issues:** 14
**Affected Endpoints:**
- `POST:/users`: 14 issues

## When to Use

Invoke this skill when the user asks to:
- "fix the validation drift"
- "add input validation"
- "fix validation issues"
- "prevent invalid inputs"

## What This Skill Does

1. Loads the latest ACV drift report
2. Parses validation drift issues
3. Detects the API framework (Flask, FastAPI, Django, Express, etc.)
4. Generates appropriate validation code
5. Applies fixes to affected endpoints
6. Verifies fixes by re-running ACV
7. Commits changes with descriptive message

## Implementation Strategy

### Step 1: Load Latest Drift Report

```bash
# Find most recent drift report
REPORT=$(find . -name "drift_report_*.json" -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -f2- -d" ")
```

### Step 2: Parse Validation Drift Issues

Extract validation drift issues and group by endpoint:

```python
import json
from collections import defaultdict

report = json.load(open(report_path))
validation_issues = report['drift_details']['validation_drift']

# Group by endpoint
by_endpoint = defaultdict(list)
for issue in validation_issues:
    by_endpoint[issue['endpoint_id']].append(issue)
```

### Step 3: Detect API Framework

Search for framework indicators:

**Python Frameworks:**
- Flask: `from flask import`, `@app.route`
- FastAPI: `from fastapi import`, `@app.get`, `@app.post`
- Django: `from django`, `django.http`, `urls.py`

**JavaScript Frameworks:**
- Express: `const express = require`, `app.get(`, `app.post(`
- NestJS: `@Controller`, `@Post`, `@Get`

**Other:**
- Ruby on Rails: `class ... < ApplicationController`
- Go: `func (.*) ServeHTTP`

### Step 4: Generate Validation Code

#### For Flask + Marshmallow:

```python
from flask import Flask, request, jsonify
from marshmallow import Schema, fields, validate, ValidationError

# Generate schema from OpenAPI spec
class {ResourceName}InputSchema(Schema):
    # Example for POST /users validation drift
    email = fields.Email(required=True)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    age = fields.Int(validate=validate.Range(min=0, max=150))

schema = {ResourceName}InputSchema()

@app.route("{path}", methods=["{method}"])
def {handler_name}():
    try:
        # Add validation before existing logic
        validated_data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({"error": "validation_failed", "details": err.messages}), 422

    # PRESERVE existing handler logic below
    # ... original code ...
```

#### For FastAPI + Pydantic:

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, EmailStr, validator

class {ResourceName}Input(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    age: int = Field(None, ge=0, le=150)

    @validator('age')
    def validate_age(cls, v):
        if v is not None and (v < 0 or v > 150):
            raise ValueError('Age must be between 0 and 150')
        return v

@app.post("{path}")
def {handler_name}(data: {ResourceName}Input):
    # Validation happens automatically via Pydantic
    # PRESERVE existing handler logic
    # ... original code ...
```

#### For Express + Joi:

```javascript
const Joi = require('joi');

const {resourceName}Schema = Joi.object({
  email: Joi.string().email().required(),
  name: Joi.string().min(1).max(100).required(),
  age: Joi.number().integer().min(0).max(150)
});

app.post('{path}', (req, res) => {
  // Add validation before existing logic
  const { error, value } = {resourceName}Schema.validate(req.body);

  if (error) {
    return res.status(422).json({
      error: 'validation_failed',
      details: error.details
    });
  }

  // PRESERVE existing handler logic
  // ... original code ...
});
```

### Step 5: Apply Fixes

For each affected endpoint:

1. **Find handler file**: Use grep to locate endpoint path definition
2. **Read handler code**: Load the current implementation
3. **Detect framework**: Identify which framework is being used
4. **Generate validation**: Create appropriate validation code
5. **Insert validation**: Add validation BEFORE business logic
6. **Preserve logic**: Keep all existing functionality
7. **Format code**: Maintain consistent code style

**Important Rules:**
- ❌ NEVER delete existing business logic
- ✅ ONLY add validation layer at the beginning
- ✅ Preserve all error handling
- ✅ Match existing code style and indentation
- ✅ Import required validation libraries

### Step 6: Verify Fixes

```bash
# Re-run ACV validation
acv validate --spec {spec_path} --url {api_url}

# Check results
python3 << 'EOF'
import json
from pathlib import Path

# Find latest report
reports = sorted(Path('.').glob('**/drift_report_*.json'), key=lambda p: p.stat().st_mtime)
if reports:
    report = json.load(reports[-1].open())
    remaining = len(report['drift_details']['validation_drift'])
    fixed = 14 - remaining

    print(f"\n✅ Fixed {fixed} validation drift issues!")
    print(f"📊 {remaining} issues remaining\n")

    if remaining == 0:
        print("🎉 All validation drift issues resolved!")
EOF
```

### Step 7: Commit Changes

```bash
# Stage modified files
git add {modified_files}

# Generate descriptive commit message
git commit -m "fix: add input validation to resolve ACV drift

- Added validation schemas for affected endpoints
- Fixes 14 validation drift issues
- Prevents invalid data from entering the system

Affected endpoints:
  - POST:/users

ACV Report: {report_path}"
```

## Example Interaction

```
User: "fix the validation drift issues"

Claude:
🔍 Analyzing validation drift report...

Found 14 validation drift issues across 1 endpoint(s).

📦 Detecting framework... Flask detected

🔧 Generating validation schemas...
   ✓ UserInputSchema for POST /users

📝 Applying fixes...
   ✓ Modified src/api/users.py
   ✓ Added marshmallow validation
   ✓ Preserved existing business logic

✅ Running verification...
   acv validate --spec openapi/api.yaml --url http://localhost:8000

   Fixed: 14 issues
   Remaining: 0 issues

🎉 All validation drift resolved!

📦 Committing changes...
   git commit -m "fix: add input validation..."

✅ Done! Your API now properly validates inputs.
```

## Notes

- This skill preserves all existing code
- Only adds validation layer at the beginning of handlers
- Requires appropriate validation library (marshmallow, pydantic, joi, etc.)
- If library is missing, Claude will suggest installation command
- Always review generated code before committing

---

*Auto-generated by API Contract Validator*

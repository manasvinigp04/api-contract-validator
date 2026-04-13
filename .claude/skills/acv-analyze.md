---
name: acv-analyze
description: Analyze API Contract Validator drift reports with cost-optimized AI analysis
---

# ACV Drift Analysis Skill

Efficiently analyze drift reports from API Contract Validator, minimizing Claude API costs while maximizing insight quality.

## When to Use

Trigger this skill when the user:
- Runs `acv validate` and wants analysis of results
- Asks to "analyze the drift report"
- Wants to understand API validation failures
- Needs remediation suggestions for drift issues

## What This Skill Does

1. **Loads the latest drift report** from `./output/` directory
2. **Performs cost-optimized triage**:
   - 0 issues → Simple "all clear" message (no API call)
   - 1-3 issues → Pattern matching from CLAUDE.md (no API call)
   - 4-10 issues → Standard analysis (1-2 API calls)
   - 11+ issues → Batched analysis (2-3 API calls max)
3. **Applies intelligent batching** to group similar issues
4. **Uses caching** to avoid re-analyzing similar issues
5. **Generates actionable report** with priorities and code examples

## Cost Optimization Strategy

### Pattern Matching (No API Call)
```
Common patterns from CLAUDE.md:
- Missing required field → Add field to serializer
- Type mismatch → Convert type or fix spec
- Validation drift → Add input validation
- Status code drift → Use correct HTTP status
```

### Smart Batching
```python
# Instead of 10 individual API calls:
for issue in issues:
    analyze(issue)  # ❌ Expensive

# Do this (1 API call):
grouped = group_by_similarity(issues)
for batch in grouped[:5]:
    analyze_batch(batch)  # ✅ Cost-effective
```

### Caching Strategy
```python
# Check cache before API call
cache_key = hash(issue.endpoint + issue.type)
if cached_analysis := cache.get(cache_key):
    return cached_analysis  # ✅ Free!

# Only call API if not cached
result = call_claude_api(issue)
cache.set(cache_key, result)
```

## Workflow

### Step 1: Find Latest Report
```bash
# Auto-detect latest report
REPORT=$(ls -t output/drift_report_*.json | head -n1)
```

### Step 2: Quick Triage
```python
issue_count = len(report.all_issues)
severity_counts = report.summary.by_severity

if issue_count == 0:
    print("✅ All tests passed! No drift detected.")
    exit(0)

if issue_count <= 3:
    # Use pattern matching (no API call)
    for issue in report.all_issues:
        remediation = match_pattern_from_claude_md(issue)
        print(f"Issue: {issue.message}")
        print(f"Fix: {remediation}")
    exit(0)
```

### Step 3: Batch Similar Issues
```python
# Group by (endpoint, issue_type)
batches = defaultdict(list)
for issue in report.all_issues:
    key = (issue.endpoint_id, issue.__class__.__name__)
    batches[key].append(issue)

# Sort by priority (severity + count)
sorted_batches = sorted(
    batches.values(),
    key=lambda b: severity_score(b) * len(b),
    reverse=True
)[:5]  # Top 5 batches only
```

### Step 4: Check Cache
```python
for batch in sorted_batches:
    cache_key = generate_cache_key(batch)
    
    if cached := cache.get(cache_key):
        print(f"📦 Using cached analysis for {batch[0].endpoint_id}")
        display_cached_analysis(cached)
        continue
    
    # Cache miss - need API call
    analysis = call_claude_api_for_batch(batch)
    cache.set(cache_key, analysis)
    display_analysis(analysis)
```

### Step 5: Generate Report
```python
# Combine all analyses into actionable report
print("\n" + "="*60)
print("🎯 DRIFT ANALYSIS REPORT")
print("="*60)

print(f"\n📊 Summary:")
print(f"  Total Issues: {issue_count}")
print(f"  Critical: {severity_counts.critical}")
print(f"  High: {severity_counts.high}")
print(f"  Medium: {severity_counts.medium}")
print(f"  Low: {severity_counts.low}")

print(f"\n🔍 Root Causes:")
for rc in root_causes:
    print(f"  • {rc.hypothesis}")

print(f"\n🛠️  Remediation (Priority Order):")
for i, rem in enumerate(remediations, 1):
    print(f"\n  {i}. {rem.title}")
    print(f"     Priority: {rem.priority.upper()}")
    print(f"     Effort: {rem.estimated_effort}")
    print(f"     Steps: {len(rem.implementation_steps)}")

print(f"\n💡 Quick Wins:")
for qw in quick_wins:
    print(f"  • {qw}")

print(f"\n💰 Analysis Cost:")
print(f"  API Calls: {api_calls_made}")
print(f"  Cache Hits: {cache_hits}")
print(f"  Tokens Saved: ~{tokens_saved}")
```

## Usage Examples

### Example 1: Clean Report (0 Issues)
```bash
$ acv validate
Running validation...
✅ All tests passed!

$ # Skill automatically detects clean report
✅ All tests passed! No drift detected.
API is fully compliant with specification.
```

**Cost:** $0 (no API call)

---

### Example 2: Small Issues (1-3)
```bash
$ acv validate
Found 2 issues

$ # Skill uses pattern matching
📋 2 issues found - using pattern matching:

Issue #1: Missing required field 'email'
  Endpoint: POST /users
  Pattern: Missing Required Field
  Fix: Add 'email' field to user serializer
  Code:
    response_data = {
        "id": user.id,
        "name": user.name,
        "email": user.email  # ← Add this
    }
  Priority: HIGH
  Effort: LOW

Issue #2: Status code should be 201, got 200
  Endpoint: POST /users
  Pattern: Status Code Drift
  Fix: Return 201 for resource creation
  Code:
    return jsonify(user), 201  # ← Use 201 not 200
  Priority: MEDIUM
  Effort: LOW
```

**Cost:** $0 (pattern matching)

---

### Example 3: Medium Report (4-10 Issues)
```bash
$ acv validate
Found 8 issues across 5 endpoints

$ # Skill batches and uses cache
🔍 Analyzing 8 issues across 5 endpoints...

📦 Checking cache...
  ✓ Cached: POST /users (3 issues)
  ✗ New: GET /products (2 issues) - analyzing...
  ✓ Cached: PUT /orders (2 issues)
  ✗ New: DELETE /cart (1 issue) - analyzing...

🎯 Analysis Complete!
  API Calls: 2
  Cache Hits: 2
  Tokens Saved: ~3,200

📊 Summary:
  8 issues (2 critical, 4 high, 2 medium)
  Primary Issue: Validation drift across write operations
  
🔍 Root Cause:
  Missing input validation middleware for POST/PUT/DELETE endpoints.
  Validation logic exists but not registered in API routes.

🛠️  Remediations:
  1. Add validation middleware [CRITICAL - 4h]
  2. Fix missing required fields [HIGH - 2h]
  3. Update status codes [MEDIUM - 1h]

💡 Quick Win: Fix all status codes in one commit (1 hour)
```

**Cost:** ~$0.03 (2 small API calls, 2 cache hits)

---

### Example 4: Large Report (10+ Issues)
```bash
$ acv validate
Found 24 issues across 12 endpoints

$ # Skill batches aggressively
🔍 Analyzing 24 issues (batched into 5 groups)...

Batch 1: Validation drift (8 issues) - analyzing...
Batch 2: Missing fields (6 issues) - analyzing...
Batch 3: Type mismatches (4 issues) - analyzing...
Batch 4-5: Using cached patterns...

🎯 Analysis Complete!
  API Calls: 3
  Cache Hits: 2
  Tokens Saved: ~8,000

📊 Systematic Issues Found:
  1. No input validation on write operations (8 endpoints)
  2. Incomplete serializer (missing 6 required fields)
  3. Schema drift (spec outdated for 4 endpoints)

🛠️  Recommended Strategy:
  Phase 1: Add validation middleware [CRITICAL - 1 day]
    → Fixes 8 critical issues immediately
  
  Phase 2: Update serializers [HIGH - 4 hours]
    → Fixes 6 high-priority issues
  
  Phase 3: Sync OpenAPI spec [MEDIUM - 2 hours]
    → Resolves remaining 4 issues

💰 Cost Optimized:
  Individual analysis would cost: ~$0.30 (24 issues)
  Batched analysis cost: ~$0.04 (3 batches)
  Savings: 86%
```

**Cost:** ~$0.04 (3 batched API calls)

---

## Integration with ACV Commands

### Automatic Analysis After Validation
```bash
# Add to acv_config.yaml:
reporting:
  auto_analyze: true  # Automatically run skill after validation
```

### Manual Analysis
```bash
# Analyze latest report
acv analyze

# Analyze specific report
acv analyze output/drift_report_20260406_120000.json

# Skip cache (force fresh analysis)
acv analyze --no-cache
```

## Cache Management

### Cache Location
```
.acv_cache/
  ├── analysis_<hash>.json  # Cached analyses
  └── metadata.json         # Cache metadata
```

### Cache Settings
```python
# Default: 7 days TTL
cache_ttl = timedelta(days=7)

# Clear old cache
acv cache clear --older-than 7d

# View cache stats
acv cache stats
```

## Performance Metrics

| Scenario | Issues | API Calls | Cost | Time |
|----------|--------|-----------|------|------|
| Clean | 0 | 0 | $0 | <1s |
| Small | 1-3 | 0 | $0 | <1s |
| Medium | 4-10 | 1-2 | ~$0.02 | 3-5s |
| Large | 11-25 | 2-4 | ~$0.05 | 8-12s |
| Very Large | 25+ | 4-5 | ~$0.08 | 15-20s |

**Traditional approach (no optimization):**
- Large report (25 issues): 25 API calls, ~$0.30, 60-90s

**This skill:**
- Large report (25 issues): 3-4 API calls, ~$0.05, 8-12s
- **Savings: 83% cost, 80% time**

## Configuration

Add to `.claude/settings.json`:
```json
{
  "skills": {
    "acv-analyze": {
      "enabled": true,
      "auto_run": true,
      "cache_ttl_days": 7,
      "max_api_calls": 5,
      "batch_size": 5
    }
  }
}
```

## Troubleshooting

### Issue: "No drift report found"
**Solution:** Run `acv validate` first to generate a report

### Issue: "Cache outdated"
**Solution:** Run with `--no-cache` or `acv cache clear`

### Issue: "API rate limit exceeded"
**Solution:** Increase cache TTL or reduce batch size

## Future Enhancements

- [ ] ML-based pattern recognition (reduce API calls further)
- [ ] Historical trend analysis
- [ ] Automated PR comments with analysis
- [ ] Slack/Teams notifications with summaries
- [ ] Dashboard with drift trends

---

**Skill Version:** 1.0  
**Requires:** ACV >= 0.1.0  
**Dependencies:** anthropic >= 0.18.0

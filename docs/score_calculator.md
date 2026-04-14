# Score Calculator

**File:** `backend/app/processing/output_generators/score_calculator.py`

Computes a 0–100 accessibility score for an asset based on its unresolved issues.

## Scoring formula

```
score = max(0, 100 - sum(weight for each unresolved issue))
```

An issue is **resolved** if `review_status` is `APPROVED` or `SKIPPED`. `REJECTED` and `PENDING` issues keep their deduction.

## Issue weights

| Issue type | Weight | WCAG criterion |
|---|---|---|
| `MISSING_ALT_TEXT` | 20 | 1.1.1 Non-text Content (A) |
| `MISSING_CAPTIONS` | 20 | 1.2.2 Captions Prerecorded (A) |
| `UNTAGGED_PDF` | 15 | 1.3.1 Info and Relationships (A) |
| `MISSING_SLIDE_TITLE` | 10 | 2.4.2 Page Titled (A) |
| `LOW_CONTRAST` | 10 | 1.4.3 Contrast Minimum (AA) |
| `MISSING_HEADING_STRUCTURE` | 8 | 1.3.1 / 2.4.6 Headings and Labels |
| `MISSING_LINK_TEXT` | 8 | 2.4.4 Link Purpose (A) |
| `MISSING_TABLE_HEADERS` | 8 | 1.3.1 Info and Relationships (A) |
| `MISSING_DOCUMENT_TITLE` | 6 | 2.4.2 Page Titled (A) |
| `INADEQUATE_ALT_TEXT` | 5 | 1.1.1 Non-text Content (A) |
| `MISSING_LANGUAGE` | 5 | 3.1.1 Language of Page (A) |
| `LOW_OCR_CONFIDENCE` | 3 | 1.1.1 Non-text Content (A) |
| `CONTRAST_UNVERIFIABLE` | 1 | 1.4.3 Contrast Minimum (AA) |
| Unknown type | 2 | (fallback) |

Weights reflect both severity and frequency. Per-occurrence deduction means a document with 10 images all missing alt text loses 200 points — effectively guaranteed zero without remediation.

## Return value

`calculate_score(db, asset)` returns:

```json
{
  "asset_id": "uuid",
  "score": 72,
  "total_issues": 8,
  "issues_by_severity": {
    "CRITICAL": 2,
    "SERIOUS": 4,
    "MODERATE": 1,
    "MINOR": 1
  },
  "auto_fixed_count": 3,
  "pending_review_count": 5,
  "wcag_criteria_map": {
    "1.1.1 Non-text Content (Level A)": ["MISSING_ALT_TEXT"],
    "2.4.4 Link Purpose (Level A)": ["MISSING_LINK_TEXT"]
  }
}
```

This JSON is saved as `accessibility_report.json` in the asset directory and stored as a `GENERATED_ARTIFACT` record.

## Adding a new issue type

1. Add the issue type string to `_ISSUE_WEIGHTS` with an appropriate weight
2. Add it to `_WCAG_MAP` with the relevant WCAG success criterion
3. No code changes needed in `calculate_score()` itself — it picks up new types automatically

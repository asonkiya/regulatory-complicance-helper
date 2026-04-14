# Checkers

Checkers are **pure functions** with the signature:

```python
def check_something(doc: NormalizedDocument) -> list[IssueResult]:
    ...
```

No database access, no file I/O, no side effects. They consume `NormalizedDocument` and return a list of `IssueResult` objects. All checkers live in `backend/app/processing/checkers/`.

## IssueResult

```python
@dataclass
class IssueResult:
    issue_type: str              # string constant — see table below
    severity: str                # "CRITICAL" | "SERIOUS" | "MODERATE" | "MINOR"
    location_in_asset: dict | None   # where in the file the issue is
    fix_recommendation: str | None   # human-readable suggestion
    auto_fixable: bool           # if True, remediate_task will call a remediator
    confidence_score: float | None   # 0.0-1.0; None = certain
    extra: dict[str, Any]        # additional data, rarely used
```

`IssueResult` objects are bulk-inserted as `AccessibilityIssue` DB rows by `check_task.py`. The `location_in_asset` dict is stored as JSONB and its schema varies by issue type.

---

## Issue types reference

| Issue type | Severity | auto_fixable | WCAG criterion | Weight |
|---|---|---|---|---|
| `MISSING_ALT_TEXT` | CRITICAL | ✅ | 1.1.1 Non-text Content (A) | 20 |
| `MISSING_CAPTIONS` | CRITICAL | ✅ | 1.2.2 Captions Prerecorded (A) | 20 |
| `UNTAGGED_PDF` | CRITICAL | ✅ | 1.3.1 Info and Relationships (A) | 15 |
| `MISSING_SLIDE_TITLE` | SERIOUS | ❌ | 2.4.2 Page Titled (A) | 10 |
| `LOW_CONTRAST` | SERIOUS | ❌ | 1.4.3 Contrast Minimum (AA) | 10 |
| `MISSING_HEADING_STRUCTURE` | SERIOUS | ❌ | 1.3.1 / 2.4.6 Headings and Labels (A/AA) | 8 |
| `MISSING_LINK_TEXT` | SERIOUS | ❌ | 2.4.4 Link Purpose (A) | 8 |
| `MISSING_TABLE_HEADERS` | SERIOUS | ❌ | 1.3.1 Info and Relationships (A) | 8 |
| `INADEQUATE_ALT_TEXT` | SERIOUS | ✅ | 1.1.1 Non-text Content (A) | 5 |
| `MISSING_LANGUAGE` | MODERATE | ✅ | 3.1.1 Language of Page (A) | 5 |
| `MISSING_DOCUMENT_TITLE` | MODERATE | ✅ | 2.4.2 Page Titled (A) | 6 |
| `LOW_OCR_CONFIDENCE` | SERIOUS | ❌ | 1.1.1 Non-text Content (A) | 3 |
| `CONTRAST_UNVERIFIABLE` | MINOR | ❌ | 1.4.3 Contrast Minimum (AA) | 1 |

Weight = points deducted from the 100-point accessibility score per unresolved issue.

---

## Checker: alt_text_checker

**File:** `checkers/alt_text_checker.py`  
**Applies to:** PPTX, PDF

Checks every `IMAGE` and `CHART` element in the normalized document.

**Logic:**
- `alt_text is None` → `MISSING_ALT_TEXT` (CRITICAL, auto_fixable=True)
- `alt_text` is in the generic words set **or** matches a filename pattern **or** is < 3 chars → `INADEQUATE_ALT_TEXT` (SERIOUS, auto_fixable=True)
- Otherwise: no issue

**Generic words checked:** `{"image", "img", "picture", "photo", "graphic", "figure", "fig", "chart", "diagram", "slide", "shape", "object", "untitled"}`

**location_in_asset:**
```json
{"slide": 2, "element_id": "slide2_img0"}         // PPTX
{"page": 4, "element_id": "page4_img1"}            // PDF
```

---

## Checker: caption_checker

**File:** `checkers/caption_checker.py`  
**Applies to:** MP4

Simple check: if `doc.media.has_embedded_captions is False`, emit `MISSING_CAPTIONS` (CRITICAL, auto_fixable=True).

**location_in_asset:** `{"document": True}`

---

## Checker: contrast_checker

**File:** `checkers/contrast_checker.py`  
**Applies to:** PPTX (PDF contrast detection is deferred — pdfplumber color extraction is unreliable)

For every TEXT element with a `font_color` in `extra`, calculates the WCAG 2.0 contrast ratio against an assumed white background.

**WCAG AA thresholds:**
- Normal text (< 18pt, or < 14pt bold): ratio ≥ 4.5:1
- Large text (≥ 18pt, or ≥ 14pt bold): ratio ≥ 3.0:1

Below threshold → `LOW_CONTRAST` (SERIOUS, confidence=0.9)  
Color unextractable → `CONTRAST_UNVERIFIABLE` (MINOR, confidence=1.0)

**location_in_asset:**
```json
{"slide": 1, "element_id": "slide1_shape3", "contrast_ratio": 2.8, "font_color": "#999999"}
```

---

## Checker: pdf_tag_checker

**File:** `checkers/pdf_tag_checker.py`  
**Applies to:** PDF

| Condition | Issue emitted |
|---|---|
| `is_tagged_pdf is False` | `UNTAGGED_PDF` (CRITICAL, auto_fixable=True) |
| `has_pdf_language is False` | `MISSING_LANGUAGE` (MODERATE, auto_fixable=True) |
| `is_tagged_pdf is True` AND `has_document_title is False` | `MISSING_DOCUMENT_TITLE` (MODERATE, auto_fixable=True) |
| Scanned page with `ocr_confidence < 0.70` | `LOW_OCR_CONFIDENCE` (SERIOUS, confidence_score=ocr_value) |

Note: `MISSING_DOCUMENT_TITLE` is only emitted for **tagged** PDFs. For untagged PDFs, `UNTAGGED_PDF` already subsumes it (the tagged PDF generator always injects a title).

---

## Checker: pdf_content_checker

**File:** `checkers/pdf_content_checker.py`  
**Applies to:** PDF

### Link text (`MISSING_LINK_TEXT`)

For each hyperlink in `page.hyperlinks`, flags it if the link text:
- Is empty
- Matches the ambiguous-text deny-list (case-insensitive, punctuation stripped): `{"click here", "here", "read more", "more", "link", "click", "this link", "this", "url", "learn more", "more info", "details", "info", "go", "visit", "see more"}`
- Is a raw URL (starts with `http://` or `https://`)

**location_in_asset:**
```json
{"page": 2, "bbox": [120, 340, 200, 355], "url": "https://example.com", "link_text": "click here"}
```

### Table headers (`MISSING_TABLE_HEADERS`)

For each table in `page.tables` where `has_header_row is False` AND `row_count >= 2`, emits `MISSING_TABLE_HEADERS` (SERIOUS, confidence_score=0.75 to signal heuristic detection).

**location_in_asset:**
```json
{"page": 5, "table_bbox": [72, 200, 540, 400], "row_count": 6}
```

---

## Checker: structure_checker

**File:** `checkers/structure_checker.py`  
**Applies to:** PPTX, PDF

**PPTX:** Emits `MISSING_SLIDE_TITLE` (SERIOUS) for any slide where `title is None` or `title == ""`.

**PDF:** Only runs on **untagged** PDFs (tagged PDFs handle heading semantics natively). Uses a font-size heuristic: calculates average body size across all text blocks on a page, then flags text blocks with `font_size >= avg * 1.5` AND `len(text) < 150` as candidate headings. If any candidate headings are found, emits `MISSING_HEADING_STRUCTURE` (SERIOUS) for that page.

**location_in_asset:**
```json
{"page": 0, "candidate_headings": ["Introduction", "Key Concepts"]}
```

---

## Registering a new checker

1. Create `checkers/my_checker.py` with a `check_my_thing(doc: NormalizedDocument) -> list[IssueResult]` function
2. Add its issue type(s) to the comment in `models/issue.py`
3. Add weights and WCAG criteria to `score_calculator.py` (`_ISSUE_WEIGHTS` and `_WCAG_MAP`)
4. Add it to the checker list in `tasks/check_task.py`

If the checker needs data not yet in `NormalizedDocument`, add the extraction to the appropriate normalizer first — **checkers must remain pure functions**.

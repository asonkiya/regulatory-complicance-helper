# Remediators

Remediators generate AI-powered fixes for issues where `auto_fixable=True`. They run in stage 3 of the pipeline (`remediate_task.py`) on the `ai_remediation` Celery queue.

All Claude API calls go through `services/claude_service.py`, which handles retries (exponential backoff on `RateLimitError`, up to 3 attempts) and JSON response parsing.

## How remediation works

`remediate_task.py` queries all `auto_fixable=True, review_status=PENDING` issues for the asset, then dispatches each to the appropriate remediator via `_remediate_issue()`:

```python
if issue.issue_type in ("MISSING_ALT_TEXT", "INADEQUATE_ALT_TEXT"):
    result = generate_alt_text_for_issue(asset, issue)
    # → creates GeneratedArtifact(artifact_type="ALT_TEXT")

elif issue.issue_type == "MISSING_DOCUMENT_TITLE":
    result = generate_title_for_issue(asset, issue)
    # → creates GeneratedArtifact(artifact_type="DOCUMENT_TITLE")

elif issue.issue_type == "MISSING_CAPTIONS":
    result = generate_captions_for_asset(asset)
    # → creates GeneratedArtifact(artifact_type="CAPTIONS_VTT")
    # → creates GeneratedArtifact(artifact_type="CAPTIONS_SRT")
```

Each remediator writes a `GeneratedArtifact` row and updates `issue.fix_recommendation` and `issue.confidence_score`. Artifacts need professor approval (`approved_at` set) before they are used in the final output generation.

---

## alt_text_generator

**File:** `remediators/alt_text_generator.py`  
**Handles:** `MISSING_ALT_TEXT`, `INADEQUATE_ALT_TEXT`

```python
generate_alt_text_for_issue(asset, issue) -> AltTextGenResult
    .alt_text: str
    .confidence: float
```

**Process:**
1. Reads `element_id` and location metadata from `issue.location_in_asset`
2. Constructs context: `"Slide 3 of lecture_slides.pptx"` or `"Page 5 of report.pdf"`
3. Finds the image file on disk using the `element_id` pattern (e.g. `page2_img0.png`); falls back to globbing the asset directory for the first image
4. Determines if the element is a chart (if `"CHART"` appears in the element_id)
5. Calls `claude_service.generate_alt_text(image_path, context, is_chart)`

**Claude prompt (image):**
> You are an accessibility expert. Generate concise, descriptive alt text for images used in university course materials. Follow WCAG 2.0 AA guidelines. Be specific and functional. Avoid starting with "Image of" or "Picture of".
> Respond as JSON: `{"alt_text": "...", "long_description": null, "confidence": 0.0}`

**Claude prompt (chart):**
> You are an accessibility expert specializing in data visualization. Generate concise, informative alt text for charts. Include: chart type, axes, key values/trends.
> Respond as JSON: `{"alt_text": "...", "long_description": "...", "confidence": 0.0}`

**Fallback:** If no image file is found, returns `AltTextGenResult("Alt text could not be generated — image not found.", 0.1)`.

---

## document_title_generator

**File:** `remediators/document_title_generator.py`  
**Handles:** `MISSING_DOCUMENT_TITLE`

```python
generate_title_for_issue(asset, issue) -> TitleGenResult
    .title: str
    .confidence: float
```

**Process:**
1. Loads `normalized.json`, extracts the first page's text blocks (up to 500 chars)
2. Calls `claude_service.generate_document_title(filename, first_page_text)`

**Claude prompt:**
> You are an accessibility metadata expert. Generate a concise, descriptive document title (5-12 words, Title Case, no file extensions or course codes) for a university course PDF.
> Respond as JSON: `{"title": "...", "confidence": 0.0}`

**Fallback:** If Claude fails, derives a title from the filename by replacing `_` and `-` with spaces and applying title case. Returns `confidence=0.0`.

---

## caption_generator

**File:** `remediators/caption_generator.py`  
**Handles:** `MISSING_CAPTIONS`

```python
generate_captions_for_asset(asset) -> dict[str, Path] | None
# Returns: {"CAPTIONS_VTT": Path, "CAPTIONS_SRT": Path}
# Returns None if transcript not found
```

**Process:**
1. Loads `transcript_raw.json` from the asset directory (written by the video normalizer)
2. If `ANTHROPIC_API_KEY` is set, calls `claude_service.clean_transcript()` to fix spelling, remove filler words, and correct domain terminology while preserving timestamps. Saves result to `transcript_clean.json`.
3. Writes a `.vtt` file (WEBVTT format, lines wrapped at 32 chars per WCAG guidance)
4. Writes a `.srt` file (SubRip format with sequential numbering)
5. Returns paths to both files

**Claude prompt (transcript cleaning):**
> You are an expert transcript editor for university course materials. Clean the transcript: fix spelling, correct domain terminology, remove filler words ("um", "uh", "like"), fix punctuation. IMPORTANT: Preserve all timestamps exactly.
> Respond as JSON: `{"segments": [{...}], "confidence": 0.9}`

**Timestamp formats:**
- VTT: `HH:MM:SS.mmm` (milliseconds with dot separator)
- SRT: `HH:MM:SS,mmm` (milliseconds with comma separator)

---

## Adding a new remediator

1. Create `remediators/my_remediator.py` with a function that returns a result dataclass
2. Add a new `elif` branch in `tasks/remediate_task.py`'s `_remediate_issue()` function
3. Create the `GeneratedArtifact` with an appropriate `artifact_type` string
4. Document the new `artifact_type` in the comment in `models/artifact.py`
5. Set `auto_fixable=True` on the issue type in the checker that emits it
6. If the artifact affects `tagged_pdf_generator`, wire it in there too

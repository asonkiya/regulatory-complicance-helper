# Claude Service

**File:** `backend/app/services/claude_service.py`

All Anthropic API calls go through this module. It owns prompt construction, retry logic, and JSON parsing of Claude's responses. Nothing else in the codebase should import `anthropic` directly.

## Configuration

```python
MODEL = "claude-sonnet-4-6"
```

**Retry policy** (applied to all functions via `@tenacity.retry`):
- Retries only on `anthropic.RateLimitError`
- Exponential backoff: 4–60 seconds between retries
- Maximum 3 attempts

The client is lazily initialized on first call as a module-level singleton.

---

## `generate_alt_text`

```python
generate_alt_text(
    image_path: str,
    context: str = "",
    is_chart: bool = False,
) -> AltTextResult
```

Sends a vision message to Claude with the image encoded as base64.

**Supported image formats:** PNG, JPEG, GIF, WebP

**Response JSON Claude returns:**
```json
{"alt_text": "...", "long_description": "...", "confidence": 0.9}
```

`long_description` is only populated for charts (null for regular images).

**System prompts:**
- *Image:* "Accessibility expert. Concise, descriptive alt text for university course materials. WCAG 2.0 AA. No 'Image of' / 'Picture of' prefix."
- *Chart:* "Accessibility expert specializing in data visualization. Include chart type, axes, key values/trends."

**Fallback:** If JSON parsing fails, returns raw response text (capped at 300 chars) with `confidence=0.6`.

---

## `generate_document_title`

```python
generate_document_title(
    filename: str,
    first_page_text: str,
) -> DocumentTitleResult
```

**Input:** Filename + first 500 chars of page 0 text blocks.

**Response JSON:**
```json
{"title": "Introduction to Organic Chemistry", "confidence": 0.85}
```

**System prompt:** "Accessibility metadata expert. 5-12 words, Title Case, no file extensions or course codes."

**Fallback:** Returns the filename string with `confidence=0.0`.

---

## `clean_transcript`

```python
clean_transcript(
    raw_segments: list[dict],
    course_title: str = "",
) -> CleanedTranscriptResult
```

Input segments format: `[{"start": 0.0, "end": 2.5, "text": "Um, today we'll be..."}]`

Formats as: `[0.0s - 2.5s] Um, today we'll be...` and sends to Claude.

**System prompt:** "Expert transcript editor. Fix spelling, correct domain terminology, remove filler words ('um', 'uh', 'like'), fix punctuation. Preserve all timestamps exactly."

**Response JSON:**
```json
{"segments": [{"start": 0.0, "end": 2.5, "text": "Today we will..."}], "confidence": 0.9}
```

**Fallback:** Returns original `raw_segments` unchanged with `confidence=0.5` if parsing fails.

`max_tokens=4096` — long lectures may be truncated; the system currently passes the full transcript in one call.

---

## Return types

```python
@dataclass
class AltTextResult:
    alt_text: str
    long_description: str | None
    confidence: float

@dataclass
class DocumentTitleResult:
    title: str
    confidence: float

@dataclass
class CleanedTranscriptResult:
    segments: list[dict]   # [{start, end, text}]
    confidence: float
```

## JSON parsing pattern

All functions use the same safe extraction:
```python
start = text.find("{")
end = text.rfind("}") + 1
data = json.loads(text[start:end])
```

This strips any prose Claude adds around the JSON object.

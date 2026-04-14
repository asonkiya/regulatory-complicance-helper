# System Architecture

Accessibility Copilot ingests university course materials (PPTX, PDF, MP4), detects Section 508 / WCAG 2.0 AA violations, uses Claude to generate fixes, and presents a professor-facing review queue with downloadable remediated outputs.

## Stack

| Layer | Technology |
|---|---|
| API | FastAPI (Python 3.11+) |
| Task queue | Celery + Redis |
| Database | PostgreSQL via SQLAlchemy 2.0 |
| AI | Anthropic Claude (claude-sonnet-4-6) |
| PDF parsing | pdfplumber, pymupdf, pikepdf |
| PPTX parsing | python-pptx |
| OCR | pytesseract (Tesseract) |
| Transcription | faster-whisper |
| Video | ffmpeg / ffprobe |
| Frontend | Next.js 16 / React 19 |

## Processing pipeline

Every file upload dispatches a four-stage Celery chain:

```
upload (FastAPI)
  └─ process_asset_pipeline
       ├─ 1. normalize_asset     [queue: default]
       ├─ 2. check_asset         [queue: default]
       ├─ 3. remediate_asset     [queue: ai_remediation]
       └─ 4. generate_outputs    [queue: default]
```

Each stage writes its progress to a Redis key (`asset:{id}:stage`) and updates `AccessibilityAsset.processing_status` in Postgres. The frontend polls `GET /api/v1/jobs/{task_id}/status` which reads this key.

### Stage 1 — Normalize

Converts the raw file into a `NormalizedDocument` (see [normalizers.md](normalizers.md)) and saves it as `normalized.json` in the asset directory. This is the single handoff point between file ingestion and all downstream logic.

### Stage 2 — Check

Loads `normalized.json`, runs all checker functions against it (see [checkers.md](checkers.md)), and bulk-inserts `AccessibilityIssue` rows into Postgres. Each issue has `auto_fixable=True/False` which controls whether stage 3 acts on it.

### Stage 3 — Remediate

Queries all `auto_fixable=True, review_status=PENDING` issues and calls the appropriate remediator for each (see [remediators.md](remediators.md)). Remediators call Claude and write `GeneratedArtifact` rows back to Postgres.

### Stage 4 — Generate outputs

Calculates the accessibility score (see [score_calculator.md](score_calculator.md)), writes `accessibility_report.json`, and for PDFs produces an `output_tagged.pdf` with approved alt text and metadata injected (see [tagged_pdf_generator.md](tagged_pdf_generator.md)).

## Storage layout

All files for an asset live under a single directory:

```
{STORAGE_BASE_PATH}/{asset_id}/
  original.{ext}            ← uploaded file
  normalized.json           ← NormalizedDocument
  slide0_img0.png           ← extracted PPTX images
  page0_img0.png            ← extracted PDF images
  transcript_raw.json       ← faster-whisper output
  transcript_clean.json     ← Claude-cleaned transcript
  captions.vtt
  captions.srt
  accessibility_report.json
  output_tagged.pdf
```

## Celery queues

| Queue | Workers | What runs there |
|---|---|---|
| `default` | 4 concurrent | normalize, check, output |
| `ai_remediation` | 8 concurrent (gevent) | remediate (I/O bound — Claude API) |
| `transcription` | 1 concurrent | video normalization (memory heavy) |

## Database models

```
AccessibilityAsset
  ├─ AccessibilityIssue[]   (detected violations)
  ├─ GeneratedArtifact[]    (AI-generated fixes)
  └─ AuditEvent[]           (download / approval log)
```

See [models.md](models.md) for full field reference.

## Key environment variables

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Required for all Claude calls |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Celery broker and progress store |
| `STORAGE_BASE_PATH` | Root directory for all asset files |
| `WHISPER_MODEL_SIZE` | `base` / `small` / `medium` / `large` |
| `ALLOWED_ORIGINS` | CORS origins (default: localhost:3000) |

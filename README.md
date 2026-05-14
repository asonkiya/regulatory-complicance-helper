# Accessibility Copilot

A web app that helps university professors bring their course materials into Section 508 / WCAG 2.0 AA compliance. Upload slides, PDFs, or lecture videos — the system detects violations, uses AI to generate fixes, and presents a review queue where professors can approve, edit, or reject each remediation before downloading the corrected files.

---

## What it does

1. **Ingest** — drag-and-drop upload of PPTX, PDF, or MP4 files
2. **Detect** — automated checks against ~12 WCAG/Section 508 criteria (missing alt text, untagged PDFs, missing captions, low-contrast text, etc.)
3. **Remediate** — Claude generates alt text for images, cleans transcripts, adds document metadata
4. **Review** — professor-facing queue with a PDF viewer that highlights exactly where each issue is
5. **Export** — download a tagged, remediated PDF with an accessibility score

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16 (App Router), React 19, Tailwind CSS 4, react-pdf |
| Backend | Python 3.11, FastAPI, Celery |
| Database | PostgreSQL (SQLAlchemy + Alembic) |
| Queue / cache | Redis |
| AI | Anthropic Claude (vision + text) |
| File processing | pymupdf, pdfplumber, python-pptx, faster-whisper, pytesseract |

---

## Quick start (Docker)

```bash
cp .env.example .env
# add your ANTHROPIC_API_KEY to .env

docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs

---

## Local development

### Backend

```bash
cd backend
pip install -e ".[dev]"

# needs postgres + redis running
docker compose up postgres redis -d

alembic upgrade head
uvicorn app.main:app --reload
```

### Celery workers

```bash
cd backend
celery -A app.tasks.celery_app worker -Q default --concurrency=4 --loglevel=info
celery -A app.tasks.celery_app worker -Q ai_remediation --concurrency=8 -P gevent --loglevel=info
celery -A app.tasks.celery_app worker -Q transcription --concurrency=1 --loglevel=info
```

### Frontend

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

### Tests & lint

```bash
# backend
cd backend
pytest
ruff check .

# frontend
cd frontend
npm run lint
```

---

## Processing pipeline

Every upload runs through an async Celery chain:

```
upload → normalize → check → remediate → generate outputs
```

Each stage updates the asset's processing status in Postgres and writes the current stage name to Redis, which the frontend polls to show real-time progress.

The canonical intermediate format is `NormalizedDocument` — all normalizers produce it, all checkers consume it. See [`docs/normalizers.md`](docs/normalizers.md) and [`docs/checkers.md`](docs/checkers.md).

---

## Issue types

| Issue | Severity | Auto-fixable |
|---|---|---|
| Missing alt text | Critical | Yes |
| Inadequate alt text | High | Yes |
| Untagged PDF | High | Yes |
| Missing document title | Medium | Yes |
| Missing language declaration | Medium | Yes |
| Missing captions (video) | Critical | Yes |
| Missing link text | High | No |
| Missing table headers | High | No |
| Missing heading structure | Medium | No |
| Low OCR confidence | High | No |
| Low color contrast | High | No |
| Inaccessible font | Low | No |

Auto-fixable issues get a Claude-generated remediation that professors review before it's applied. Non-auto-fixable issues get a recommendation and must be acknowledged manually.

---

## Key environment variables

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Required — powers alt text and transcript remediation |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `STORAGE_BASE_PATH` | Where uploaded and processed files are stored |
| `WHISPER_MODEL_SIZE` | `base` (default) / `small` / `medium` / `large` |

---

## Documentation

Detailed docs live in [`docs/`](docs/):

- [`architecture.md`](docs/architecture.md) — system design and pipeline
- [`checkers.md`](docs/checkers.md) — all issue types and WCAG mappings
- [`remediators.md`](docs/remediators.md) — how AI fixes are generated
- [`api.md`](docs/api.md) — REST endpoint reference
- [`development.md`](docs/development.md) — local setup and contributing

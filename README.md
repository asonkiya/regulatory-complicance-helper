# Accessibility Copilot

A full-stack platform that helps university professors bring course materials into Section 508 / WCAG 2.0 AA compliance. Upload slides, PDFs, or lecture videos — the system detects violations, uses AI to generate fixes, and presents a review queue where professors can approve, edit, or reject each remediation before downloading the corrected files.

---

## Features

- **Multi-format ingestion** — PPTX, PDF, and MP4 via drag-and-drop upload
- **Automated accessibility auditing** — 12 WCAG/Section 508 checks covering alt text, document structure, captions, contrast, OCR confidence, and more
- **AI-powered remediation** — Claude generates alt text for images, cleans video transcripts, and injects document metadata
- **Interactive review queue** — side-by-side PDF viewer with per-issue highlighting so professors can see exactly what needs attention
- **Scored output** — exports a tagged, remediated PDF with a weighted accessibility score
- **Real-time pipeline status** — per-stage progress updates streamed from Celery workers through Redis to the UI

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16 (App Router), React 19, Tailwind CSS 4, react-pdf |
| Backend | Python 3.11, FastAPI, Celery |
| Database | PostgreSQL (SQLAlchemy + Alembic) |
| Queue / cache | Redis |
| AI | Anthropic Claude API (vision + text) |
| File processing | pymupdf, pdfplumber, python-pptx, faster-whisper, pytesseract |

---

## Architecture

Every upload runs through an async Celery pipeline:

```
upload → normalize → check → remediate → generate outputs
```

Files are converted to a canonical `NormalizedDocument` format that decouples the checkers from the file types — adding support for a new format only requires a new normalizer. Remediation runs on a dedicated `ai_remediation` queue (gevent, I/O-bound) while transcription runs isolated on its own single-worker queue (memory-heavy). See [`docs/architecture.md`](docs/architecture.md) for the full design.

---

## Accessibility checks

| Issue | Severity | Auto-remediated |
|---|---|---|
| Missing alt text | Critical | Yes — Claude vision |
| Inadequate alt text | High | Yes — Claude vision |
| Untagged PDF | High | Yes — structure injection |
| Missing document title | Medium | Yes — Claude text |
| Missing language declaration | Medium | Yes — metadata injection |
| Missing captions (video) | Critical | Yes — Whisper + Claude |
| Missing link text | High | No |
| Missing table headers | High | No |
| Missing heading structure | Medium | No |
| Low OCR confidence | High | No |
| Low color contrast | High | No |
| Inaccessible font | Low | No |

Auto-remediated issues are reviewed and approved by the professor before being written to the output file.

---

## Running locally

### Docker (recommended)

```bash
cp .env.example .env        # add ANTHROPIC_API_KEY
docker compose up --build
```

- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs

### Without Docker

```bash
# Start dependencies
docker compose up postgres redis -d

# Backend
cd backend
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload

# Celery workers (separate terminals)
celery -A app.tasks.celery_app worker -Q default --concurrency=4 --loglevel=info
celery -A app.tasks.celery_app worker -Q ai_remediation --concurrency=8 -P gevent --loglevel=info
celery -A app.tasks.celery_app worker -Q transcription --concurrency=1 --loglevel=info

# Frontend
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

### Tests

```bash
cd backend && pytest
cd frontend && npm run lint
```

---

## Configuration

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Required — powers AI remediation |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `STORAGE_BASE_PATH` | Upload and output file storage path |
| `WHISPER_MODEL_SIZE` | `base` / `small` / `medium` / `large` (default: `base`) |

---

## Documentation

- [`docs/architecture.md`](docs/architecture.md) — system design and pipeline stages
- [`docs/checkers.md`](docs/checkers.md) — all issue types, WCAG mappings, and scoring weights
- [`docs/remediators.md`](docs/remediators.md) — AI remediation prompts and output formats
- [`docs/api.md`](docs/api.md) — REST endpoint reference
- [`docs/development.md`](docs/development.md) — contributing and local setup

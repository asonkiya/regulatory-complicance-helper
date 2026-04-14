# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Accessibility Copilot — a web app that ingests university course materials (PPTX, PDF, MP4), detects Section 508 / WCAG 2.0 AA violations, uses Claude + local AI models to generate fixes, and presents a professor-facing review queue with downloadable remediated outputs.

Monorepo: `backend/` (Python/FastAPI) + `frontend/` (Next.js 16 / React 19).

---

## Commands

### Full stack (recommended)

```bash
cp .env.example .env          # then add ANTHROPIC_API_KEY
docker compose up --build     # starts postgres, redis, backend, 3 celery workers, frontend
```

Backend API docs at `http://localhost:8000/docs`, frontend at `http://localhost:3000`.

### Backend (local)

```bash
cd backend
pip install -e ".[dev]"       # installs app + dev deps

# Requires postgres + redis running (e.g. via: docker compose up postgres redis -d)
alembic upgrade head           # run migrations
uvicorn app.main:app --reload  # dev server on :8000

# Tests
pytest                         # all tests
pytest tests/test_checkers.py  # single file
pytest -k "test_missing_alt"   # single test by name

# Lint
ruff check .
ruff format .
```

### Celery workers (local)

```bash
cd backend
celery -A app.tasks.celery_app worker -Q default --concurrency=4 --loglevel=info
celery -A app.tasks.celery_app worker -Q ai_remediation --concurrency=8 -P gevent --loglevel=info
celery -A app.tasks.celery_app worker -Q transcription --concurrency=1 --loglevel=info
```

### Frontend (local)

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev   # dev server on :3000
npm run build
npm run lint
```

### Database migrations

```bash
cd backend
alembic revision --autogenerate -m "description"   # generate from model changes
alembic upgrade head                                # apply
alembic downgrade -1                               # rollback one
```

---

## Architecture

### Processing pipeline

The core of the system is an async Celery chain dispatched on every upload:

```
upload (FastAPI) → process_asset_pipeline → normalize_asset → check_asset → remediate_asset → generate_outputs
```

Each task in `backend/app/tasks/` updates `AccessibilityAsset.processing_status` in Postgres and writes the current stage name to Redis (`asset:{id}:stage`). The frontend polls `GET /api/v1/jobs/{task_id}/status`, which reads that Redis key to report real pipeline progress (not just Celery's binary PENDING/SUCCESS state).

### Canonical data format

`backend/app/processing/normalizers/__init__.py` defines `NormalizedDocument` — the contract between every normalizer and every checker. All three normalizers (PPTX, PDF, MP4) produce a `NormalizedDocument`; all five checkers consume it. If you change this dataclass you must update all normalizers and all checkers.

### Checkers → Issues → Remediators → Artifacts

- **Checkers** (`processing/checkers/`) return `list[IssueResult]` (dataclass in `checkers/__init__.py`). They are pure functions: `(NormalizedDocument) → list[IssueResult]`. No DB access, no side effects.
- `check_task.py` bulk-inserts `IssueResult` objects as `AccessibilityIssue` rows.
- **Remediators** (`processing/remediators/`) are called from `remediate_task.py` for issues where `auto_fixable=True`. Each remediator creates a `GeneratedArtifact` row linked to both the asset and the issue.
- All Claude calls funnel through `services/claude_service.py`. That module owns retry logic (`tenacity`), prompt construction, and JSON parsing of Claude's responses.

### Three Celery queues

| Queue | Workers | Tasks |
|---|---|---|
| `default` | 4 concurrent | normalize, check, output |
| `ai_remediation` | 8 concurrent (gevent) | remediate (Claude API calls — I/O bound) |
| `transcription` | 1 concurrent | video normalization (faster-whisper, memory-heavy) |

Adding new AI-heavy work: route to `ai_remediation`. Adding new CPU/file-I/O work: route to `default`.

### Frontend data flow

- `lib/api.ts` — all backend calls; typed against `lib/types.ts` which mirrors Pydantic schemas exactly
- `lib/hooks/useJobStatus.ts` — polls job status; stops automatically on terminal states; pauses when tab is hidden
- `swr` is used for all data fetching on the dashboard and review pages
- The review page (`app/assets/[assetId]/review/page.tsx`) renders different right-panel components depending on `issue.issue_type`

### Storage

Files are stored at `{STORAGE_BASE_PATH}/{asset_id}/` on the local filesystem. All intermediate files (extracted images, normalized JSON, transcript JSON, generated VTT/SRT/PDF) land in this directory. `storage_service.py` is the only module that constructs paths.

### Key env vars

| Var | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Required for AI remediation (alt text, transcript cleaning) |
| `WHISPER_MODEL_SIZE` | `base` (default, ~1GB) / `small` / `medium` / `large` |
| `STORAGE_BASE_PATH` | Where uploaded and processed files are stored |
| `DATABASE_URL` | PostgreSQL connection string |

---

## Important conventions

- **Issue types are strings**, not enums — new issue types can be added in checkers without a migration. The valid set is documented in `models/issue.py` as a comment and in `score_calculator.py`'s `_ISSUE_WEIGHTS` dict (which also determines whether a new type affects the score).
- **`auto_fixable=True`** means `remediate_task` will call a remediator for it. `auto_fixable=False` means Claude generates a recommendation text only; the professor must acknowledge it manually.
- **`review_status="APPROVED"`** is what makes an issue count as resolved in the score calculation. `SKIPPED` also resolves it. `REJECTED` and `PENDING` leave the deduction in place.
- **Tagged PDF generation** (`tagged_pdf_generator.py`) is MVP-scoped: it only injects `/MarkInfo`, `/Lang`, image `/Alt` attributes, and XMP title. Full structure tree re-tagging is not implemented.
- The `NormalizedElement.element_id` format is `slide{N}_shape{M}` for PPTX and `page{N}_img{M}` for PDF. These IDs are stored in `AccessibilityIssue.location_in_asset.element_id` and used by `alt_text_generator.py` to find the corresponding image file on disk.

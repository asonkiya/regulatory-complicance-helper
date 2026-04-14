# Development Guide

## Quick start (Docker — recommended)

```bash
cp .env.example .env
# Add ANTHROPIC_API_KEY to .env

docker compose up --build
```

- API + Swagger UI: `http://localhost:8000/docs`
- Frontend: `http://localhost:3000`

## Local backend setup

Requires Postgres and Redis running. Start just those via Docker:

```bash
docker compose up postgres redis -d
```

Then in `backend/`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

alembic upgrade head        # apply DB migrations
uvicorn app.main:app --reload
```

## Running Celery workers locally

Three separate worker processes (each in `backend/`):

```bash
# General work — normalize, check, output
celery -A app.tasks.celery_app worker -Q default --concurrency=4 --loglevel=info

# AI remediation — Claude API calls (I/O bound, gevent pool)
celery -A app.tasks.celery_app worker -Q ai_remediation --concurrency=8 -P gevent --loglevel=info

# Video transcription — one at a time (memory heavy)
celery -A app.tasks.celery_app worker -Q transcription --concurrency=1 --loglevel=info
```

## Running tests

```bash
cd backend
source .venv/bin/activate

pytest                              # all tests
pytest tests/test_pdf_checkers.py  # new PDF checker tests
pytest tests/test_checkers.py      # original checker tests
pytest tests/test_score_calculator.py
pytest -k "test_missing_alt"       # single test by name
pytest -v                          # verbose output
```

All tests are unit tests — no database or Redis required. Checkers are pure functions; the score calculator uses mocked DB sessions.

## Linting

```bash
cd backend
ruff check .
ruff format .
```

## Database migrations

```bash
cd backend

# After changing a model, generate a migration:
alembic revision --autogenerate -m "add new field"

# Apply:
alembic upgrade head

# Roll back one step:
alembic downgrade -1
```

## Frontend

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

## Manual end-to-end PDF test

```bash
# From project root (backend must be running)
./pdf_test.sh                      # auto-generates a test PDF
./pdf_test.sh path/to/your.pdf     # test your own PDF

# Custom API URL:
API_URL=http://localhost:8000 ./pdf_test.sh
```

The script runs unit tests, uploads a PDF, polls until processing completes, prints detected issues, accessibility score, and checks whether the tagged PDF was generated.

## Environment variables

Copy `.env.example` to `.env` and fill in:

| Variable | Required | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | — |
| `DATABASE_URL` | ✅ | `postgresql://...@localhost/accessibility_copilot` |
| `REDIS_URL` | ✅ | `redis://localhost:6379/0` |
| `STORAGE_BASE_PATH` | ❌ | `/tmp/accessibility_copilot_storage` |
| `WHISPER_MODEL_SIZE` | ❌ | `base` |
| `ALLOWED_ORIGINS` | ❌ | `http://localhost:3000` |
| `ENVIRONMENT` | ❌ | `development` |
| `DEBUG` | ❌ | `true` |

## Project structure

```
regulatory-complicance-helper/
├── backend/
│   ├── app/
│   │   ├── api/v1/          ← FastAPI endpoints
│   │   ├── models/          ← SQLAlchemy ORM models
│   │   ├── schemas/         ← Pydantic request/response schemas
│   │   ├── processing/
│   │   │   ├── normalizers/ ← PPTX, PDF, video → NormalizedDocument
│   │   │   ├── checkers/    ← pure functions → list[IssueResult]
│   │   │   ├── remediators/ ← Claude-powered fixes → GeneratedArtifact
│   │   │   └── output_generators/ ← score + tagged PDF
│   │   ├── services/        ← claude_service, storage_service
│   │   ├── tasks/           ← Celery pipeline tasks
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   ├── migrations/          ← Alembic migration scripts
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── app/                 ← Next.js app router pages
│   ├── lib/
│   │   ├── api.ts           ← all backend calls
│   │   ├── types.ts         ← mirrors Pydantic schemas
│   │   └── hooks/
│   └── package.json
├── docker-compose.yml
├── .env.example
└── docs/                    ← you are here
```

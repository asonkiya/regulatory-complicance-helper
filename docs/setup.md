# Setup Guide

For first-time contributors or anyone running this locally.

## Prerequisites

- **Docker Desktop** — [download here](https://www.docker.com/products/docker-desktop/)
  - Make sure it's running before you start (you'll see the whale icon in your menu bar)
- **Git** — comes pre-installed on Mac; `git --version` to confirm
- **Anthropic API key** — get one at [console.anthropic.com](https://console.anthropic.com/) → API Keys
  - Needed for AI features: alt text generation, transcript cleaning, document title generation
  - The app runs without it, but those features will fail

That's it. No Python, Node, or Postgres needed locally — everything runs in Docker.

## First-time setup

Clone and run the setup script:

```bash
git clone <repo-url>
cd regulatory-complicance-helper
./setup.sh
```

The script will:
1. Check that Docker is installed and running
2. Copy `.env.example` → `.env`
3. Prompt you for your Anthropic API key and save it
4. Build all Docker images and start the stack
5. Wait for the backend to be ready and print the URLs

First build takes ~5 minutes (downloading base images, installing Python/Node dependencies).

## What's running

| Service | URL | What it does |
|---|---|---|
| Frontend | http://localhost:3000 | Professor-facing UI |
| Backend API | http://localhost:8000 | FastAPI REST API |
| API docs (Swagger) | http://localhost:8000/docs | Interactive API explorer |
| Postgres | localhost:5432 | Database (internal) |
| Redis | localhost:6379 | Task queue broker (internal) |

Three Celery workers run in the background (no exposed ports):
- `celery_worker_default` — normalizes files, runs checkers, generates output
- `celery_worker_ai` — calls Claude API for remediation
- `celery_worker_transcribe` — runs Whisper for video captions

## Stopping and starting

```bash
# Stop all services (data is preserved)
docker compose down

# Start again (fast — images already built)
docker compose up -d

# Stop and wipe the database (fresh start)
docker compose down -v
```

## Viewing logs

```bash
docker compose logs -f                   # all services
docker compose logs -f backend           # API server
docker compose logs -f celery_worker_ai  # Claude API worker
```

## If something breaks

**Port already in use:**
Something else is using port 3000 or 8000. Find and stop it, or change the ports in `docker-compose.yml`.

**Backend keeps restarting:**
Usually a bad `.env` value. Check with `docker compose logs backend`. Most common cause: `ANTHROPIC_API_KEY` is still the placeholder value.

**"Cannot connect to Docker daemon":**
Docker Desktop isn't running. Open it from Applications and wait for the whale to stop animating.

**Want to reset everything:**
```bash
docker compose down -v    # removes containers + volumes (deletes all uploaded files and DB data)
docker compose up --build # rebuild from scratch
```

## Making code changes

The backend mounts the source directory, so Python changes hot-reload without rebuilding. Frontend also hot-reloads. The only time you need to rebuild is when you change `pyproject.toml`, `package.json`, or a `Dockerfile`:

```bash
docker compose up --build
```

For database model changes, generate and apply a migration:

```bash
docker compose exec backend alembic revision --autogenerate -m "describe your change"
docker compose exec backend alembic upgrade head
```

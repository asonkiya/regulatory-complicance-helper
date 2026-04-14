import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.config import settings

app = FastAPI(
    title="Accessibility Copilot",
    description="Automated accessibility remediation for course materials",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/api/v1")

# Ensure storage directory exists on startup
os.makedirs(settings.storage_base_path, exist_ok=True)


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}

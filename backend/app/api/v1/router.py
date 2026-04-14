from fastapi import APIRouter

from app.api.v1 import artifacts, assets, issues, jobs, upload

router = APIRouter()

router.include_router(upload.router, tags=["upload"])
router.include_router(assets.router, tags=["assets"])
router.include_router(issues.router, tags=["issues"])
router.include_router(artifacts.router, tags=["artifacts"])
router.include_router(jobs.router, tags=["jobs"])

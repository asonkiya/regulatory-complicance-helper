import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.artifact import GeneratedArtifact
from app.models.audit import AuditEvent
from app.schemas.artifact import ArtifactApproveRequest, ArtifactResponse

router = APIRouter()


@router.get("/assets/{asset_id}/artifacts", response_model=list[ArtifactResponse])
def list_artifacts(asset_id: uuid.UUID, db: Session = Depends(get_db)) -> list[ArtifactResponse]:
    artifacts = db.scalars(
        select(GeneratedArtifact).where(GeneratedArtifact.asset_id == asset_id)
    ).all()
    return [ArtifactResponse.model_validate(a) for a in artifacts]


@router.get("/artifacts/{artifact_id}/download")
def download_artifact(artifact_id: uuid.UUID, db: Session = Depends(get_db)) -> FileResponse:
    artifact = db.get(GeneratedArtifact, artifact_id)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    if not artifact.storage_location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Artifact file not yet available"
        )

    path = Path(artifact.storage_location)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Artifact file missing from storage"
        )

    # Audit
    db.add(
        AuditEvent(
            actor="professor",
            action="DOWNLOAD_ARTIFACT",
            asset_id=artifact.asset_id,
            artifact_id=artifact_id,
        )
    )
    db.commit()

    return FileResponse(path=str(path), filename=path.name)


@router.post("/assets/{asset_id}/artifacts/approve", response_model=list[ArtifactResponse])
def bulk_approve_artifacts(
    asset_id: uuid.UUID,
    body: ArtifactApproveRequest,
    db: Session = Depends(get_db),
) -> list[ArtifactResponse]:
    artifacts = db.scalars(
        select(GeneratedArtifact).where(
            GeneratedArtifact.asset_id == asset_id,
            GeneratedArtifact.generation_status == "COMPLETE",
            GeneratedArtifact.approved_at.is_(None),
        )
    ).all()

    now = datetime.now(timezone.utc)
    for artifact in artifacts:
        artifact.approved_by = body.approved_by
        artifact.approved_at = now

    db.commit()
    return [ArtifactResponse.model_validate(a) for a in artifacts]

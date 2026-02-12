"""Worker task management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from app.db.session import get_session
from app.models.domain import Issue, Evidence, User
from app.services.minio_client import minio_client
from app.core.config import settings
from app.services.exif import ExifService
from app.services.workflow_service import WorkflowService
from uuid import UUID, uuid4
from typing import Any, List, cast
from datetime import datetime
import io

from app.api.deps import require_worker_user
from app.schemas.issue import IssueRead

router = APIRouter()


@router.get("/tasks", response_model=List[IssueRead])
def get_worker_tasks(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_worker_user),
):
    """Return tasks assigned to the current worker."""
    statement = (
        select(Issue)
        .where(Issue.worker_id == current_user.id)
        .options(
            selectinload(cast(Any, Issue.category)),
            selectinload(cast(Any, Issue.worker)),
        )
    )
    return session.exec(statement).all()


@router.post("/tasks/{issue_id}/accept")
def accept_task(
    issue_id: UUID,
    eta_date: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_worker_user),
):
    """Accept a task and set its ETA date."""
    issue = session.get(Issue, issue_id)
    if not issue or issue.worker_id != current_user.id:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        parsed_eta = datetime.fromisoformat(eta_date)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="ETA date must use YYYY-MM-DD format",
        ) from exc

    if parsed_eta.time() != datetime.min.time():
        raise HTTPException(
            status_code=400,
            detail="ETA date must be calendar-day only (YYYY-MM-DD)",
        )

    WorkflowService.accept_task(session, issue, parsed_eta, current_user.id)
    session.commit()
    return {"message": "Task accepted"}


@router.post("/tasks/{issue_id}/start")
def start_task(
    issue_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_worker_user),
):
    """Start working on a task"""
    issue = session.get(Issue, issue_id)
    if not issue or issue.worker_id != current_user.id:
        raise HTTPException(status_code=404, detail="Task not found")

    WorkflowService.start_task(session, issue, current_user.id)
    session.commit()
    return {"message": "Work started"}


@router.post("/tasks/{issue_id}/resolve")
async def resolve_task(
    issue_id: UUID,
    photo: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_worker_user),
):
    """Resolve a task with photo evidence and EXIF capture."""
    issue = session.get(Issue, issue_id)
    if not issue or issue.worker_id != current_user.id:
        raise HTTPException(status_code=404, detail="Task not found")

    photo_content = await photo.read()
    # Validation EXIF (mandatory for resolve as per spec)
    exif_data = ExifService.extract_metadata(photo_content)

    # Requirement Story 4: Resolve photo mandatory camera
    # (Enforced in UI, but we log EXIF for verification)

    # Save Photo to Minio
    file_id = str(uuid4())
    file_path = f"resolutions/{file_id}.jpg"
    minio_client.put_object(
        settings.MINIO_BUCKET,
        file_path,
        io.BytesIO(photo_content),
        len(photo_content),
        content_type="image/jpeg",
    )

    evidence = Evidence(
        issue_id=issue.id,
        type="RESOLVE",
        file_path=file_path,
        exif_timestamp=exif_data["timestamp"],
        exif_lat=exif_data["lat"],
        exif_lng=exif_data["lng"],
    )
    session.add(evidence)

    # Use workflow service for status transition
    WorkflowService.resolve_task(session, issue, current_user.id)
    session.commit()
    return {"message": "Task resolved successfully"}

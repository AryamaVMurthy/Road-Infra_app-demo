from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlmodel import Session, select
from app.db.session import get_session
from app.models.domain import Issue, Evidence, User
from app.services.minio_client import minio_client
from app.core.config import settings
from app.services.exif import ExifService
from uuid import UUID, uuid4
from typing import List, Optional
import io
from datetime import datetime
from app.api.deps import get_current_user
from app.services.audit import AuditService

from app.api.deps import get_current_user
from app.services.audit import AuditService

from app.schemas.issue import IssueRead

router = APIRouter()


@router.get("/tasks", response_model=List[IssueRead])
def get_worker_tasks(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return session.exec(select(Issue).where(Issue.worker_id == current_user.id)).all()


@router.post("/tasks/{issue_id}/accept")
def accept_task(
    issue_id: UUID,
    eta: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    issue = session.get(Issue, issue_id)
    if not issue or issue.worker_id != current_user.id:
        raise HTTPException(status_code=404, detail="Task not found")

    issue.status = "ACCEPTED"
    issue.accepted_at = datetime.utcnow()
    issue.eta_duration = eta
    session.add(issue)

    AuditService.log(
        session,
        "STATUS_CHANGE",
        "ISSUE",
        issue_id,
        current_user.id,
        "ASSIGNED",
        "ACCEPTED",
    )

    session.commit()
    return {"message": "Task accepted"}


@router.post("/tasks/{issue_id}/start")
def start_task(
    issue_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    issue = session.get(Issue, issue_id)
    if not issue or issue.worker_id != current_user.id:
        raise HTTPException(status_code=404, detail="Task not found")

    issue.status = "IN_PROGRESS"
    issue.updated_at = datetime.utcnow()
    session.add(issue)

    AuditService.log(
        session,
        "STATUS_CHANGE",
        "ISSUE",
        issue_id,
        current_user.id,
        "ACCEPTED",
        "IN_PROGRESS",
    )

    session.commit()
    return {"message": "Work started"}


@router.post("/tasks/{issue_id}/resolve")
async def resolve_task(
    issue_id: UUID,
    photo: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
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

    issue.status = "RESOLVED"
    issue.resolved_at = datetime.utcnow()
    issue.updated_at = datetime.utcnow()

    session.add(evidence)
    session.add(issue)

    AuditService.log(
        session,
        "STATUS_CHANGE",
        "ISSUE",
        issue_id,
        current_user.id,
        "IN_PROGRESS",
        "RESOLVED",
    )

    session.commit()
    return {"message": "Task resolved successfully"}

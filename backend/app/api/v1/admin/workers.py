"""Worker management and statistics endpoints."""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db.session import get_session
from app.api.deps import get_current_user
from app.models.domain import User, Invite
from app.schemas.admin import WorkerWithStats, CreateAuthorityRequest
from app.services.analytics_service import AnalyticsService
from app.services.worker_service import WorkerService
from app.services.audit import AuditService

router = APIRouter()


@router.get("/workers", response_model=List[User])
def get_workers(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all workers in the system."""
    return WorkerService.get_all_workers(session)


@router.get("/workers-with-stats", response_model=List[WorkerWithStats])
def get_workers_with_stats(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Return workers with task counts for assignment dropdowns."""
    return AnalyticsService.get_workers_with_stats(session)


@router.post("/deactivate-worker")
def deactivate_worker(
    worker_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Deactivate a worker and unassign their active tasks."""
    WorkerService.deactivate_worker(session, worker_id, current_user.id)
    session.commit()
    return {"message": "Worker deactivated and tasks reset"}


@router.post("/invite")
def invite_worker(
    email: str,
    org_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Invite a new worker"""
    from datetime import datetime, timedelta
    from uuid import uuid4

    invite = Invite(
        email=email, 
        org_id=org_id, 
        status="INVITED", 
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    session.add(invite)
    AuditService.log(
        session, "INVITE_WORKER", "USER", uuid4(), current_user.id, None, email
    )
    session.commit()
    return {"message": f"Invite sent to {email}"}


@router.post("/onboard")
def onboard_authority(
    data: CreateAuthorityRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["SYSADMIN", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    if current_user.role == "ADMIN":
        if data.role != "WORKER":
            raise HTTPException(status_code=403, detail="Authority Admins can only onboard workers")
        data.org_id = current_user.org_id

    from sqlmodel import select

    statement = select(User).where(User.email == data.email)
    user = session.exec(statement).first()

    if user:
        user.role = data.role
        user.org_id = data.org_id
        user.full_name = data.full_name
        session.add(user)
    else:
        user = User(
            email=data.email,
            full_name=data.full_name,
            role=data.role,
            org_id=data.org_id,
        )
        session.add(user)

    session.commit()
    return {"message": f"User {data.email} onboarded as {data.role}"}

"""Worker management and statistics endpoints."""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db.session import get_session
from app.api.deps import get_current_user
from app.models.domain import User, Invite
from app.schemas.admin import WorkerWithStats
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
    # TODO: Implement proper invite logic
    from uuid import uuid4

    invite = Invite(
        email=email, org_id=org_id, status="INVITED", expires_at=uuid4()
    )  # Placeholder
    session.add(invite)
    AuditService.log(
        session, "INVITE_WORKER", "USER", uuid4(), current_user.id, None, email
    )
    session.commit()
    return {"message": f"Invite sent to {email}"}

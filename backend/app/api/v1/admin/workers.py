"""Worker management and statistics endpoints."""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.api.deps import require_admin_user
from app.models.domain import User, Invite
from app.schemas.admin import (
    WorkerBulkRegisterRequest,
    WorkerBulkRegisterResult,
    WorkerWithStats,
)
from app.services.admin_analytics_service import AdminAnalyticsService
from app.services.worker_service import WorkerService
from app.services.audit import AuditService
from datetime import timedelta
from uuid import uuid4
from app.core.time import utc_now

router = APIRouter()


@router.get("/workers", response_model=List[User])
def get_workers(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin_user),
):
    """Retrieve all workers in the system."""
    org_scope = None if current_user.role == "SYSADMIN" else current_user.org_id
    return WorkerService.get_all_workers(session, org_id=org_scope)


@router.get("/workers-with-stats", response_model=List[WorkerWithStats])
def get_workers_with_stats(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin_user),
):
    """Return workers with task counts for assignment dropdowns."""
    org_scope = None if current_user.role == "SYSADMIN" else current_user.org_id
    return AdminAnalyticsService.get_workers_with_stats(session, org_id=org_scope)


@router.post("/deactivate-worker")
def deactivate_worker(
    worker_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin_user),
):
    """Deactivate a worker and unassign their active tasks."""
    WorkerService.deactivate_worker(session, worker_id, current_user.id)
    session.commit()
    return {"message": "Worker deactivated and tasks reset"}


@router.post("/activate-worker")
def activate_worker(
    worker_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin_user),
):
    """Activate an existing worker account."""
    WorkerService.activate_worker(session, worker_id, current_user.id)
    session.commit()
    return {"message": "Worker activated"}


@router.post("/bulk-register", response_model=WorkerBulkRegisterResult)
def bulk_register_workers(
    data: WorkerBulkRegisterRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin_user),
):
    """Register multiple workers from a comma separated email string."""
    raw_emails = [token.strip() for token in data.emails_csv.split(",")]
    emails = [email for email in raw_emails if email]
    result = WorkerService.bulk_register_workers(session, current_user, emails)
    session.commit()
    return WorkerBulkRegisterResult(**result)


@router.post("/invite")
def invite_worker(
    email: str,
    org_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin_user),
):
    """Invite a new worker"""
    invite = Invite(
        email=email,
        org_id=org_id,
        status="INVITED",
        expires_at=utc_now() + timedelta(days=7),
    )
    session.add(invite)
    AuditService.log(
        session, "INVITE_WORKER", "USER", uuid4(), current_user.id, None, email
    )
    session.commit()
    return {"message": f"Invite sent to {email}"}

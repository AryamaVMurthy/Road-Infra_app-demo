"""Worker management and statistics endpoints."""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db.session import get_session
from app.api.deps import require_admin_user
from app.models.domain import User, Invite
from app.schemas.admin import WorkerWithStats, BulkInviteRequest
from app.services.analytics_service import AnalyticsService
from app.services.worker_service import WorkerService
from app.services.audit import AuditService
from datetime import datetime, timedelta
from uuid import uuid4

router = APIRouter()


@router.get("/workers", response_model=List[User])
def get_workers(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin_user),
):
    """Retrieve all workers in the system."""
    org_id = current_user.org_id if current_user.role == "ADMIN" else None
    return WorkerService.get_all_workers(session, org_id=org_id)


@router.get("/workers-with-stats", response_model=List[WorkerWithStats])
def get_workers_with_stats(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin_user),
):
    """Return workers with task counts for assignment dropdowns."""
    org_id = current_user.org_id if current_user.role == "ADMIN" else None
    return AnalyticsService.get_workers_with_stats(session, org_id=org_id)


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
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    session.add(invite)
    AuditService.log(
        session, "INVITE_WORKER", "USER", uuid4(), current_user.id, None, email
    )
    session.commit()
    return {"message": f"Invite sent to {email}"}


@router.post("/bulk-invite")
def bulk_invite_workers(
    data: BulkInviteRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin_user),
):
    """Bulk invite new workers to the admin's organization."""
    if not current_user.org_id:
        raise HTTPException(
            status_code=400, detail="Admin user must belong to an organization"
        )

    invites = []
    for email in data.emails:
        email = email.strip()
        if not email:
            continue
        invite = Invite(
            email=email,
            org_id=current_user.org_id,
            status="INVITED",
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        invites.append(invite)
        session.add(invite)
        AuditService.log(
            session, "INVITE_WORKER", "USER", uuid4(), current_user.id, None, email
        )

    session.commit()
    return {"message": f"Invites sent to {len(invites)} workers"}

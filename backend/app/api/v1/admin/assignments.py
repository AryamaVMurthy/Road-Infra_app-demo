"""
Admin Assignment Routes
Endpoints for issue assignment and reassignment
"""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db.session import get_session
from app.api.deps import get_current_user
from app.models.domain import User, Issue
from app.schemas.admin import BulkAssignRequest
from app.services.admin import AdminService
from app.services.workflow_service import WorkflowService

router = APIRouter()


@router.post("/assign")
def assign_issue(
    issue_id: UUID,
    worker_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Assign a specific issue to a field worker. Validates both entities before update."""
    # Validate issue existence
    issue = session.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    # Validate worker existence
    worker = session.get(User, worker_id)
    if not worker or worker.role != "WORKER":
        raise HTTPException(status_code=404, detail="Worker not found or invalid role")

    AdminService.assign_issue(session, issue_id, worker_id, current_user.id)
    session.commit()
    return {
        "message": f"Issue assigned successfully to {worker.full_name or worker.email}"
    }


@router.post("/bulk-assign")
def bulk_assign(
    data: BulkAssignRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Bulk assign multiple issues to a worker"""
    count = AdminService.bulk_assign(
        session, data.issue_ids, data.worker_id, current_user.id
    )
    session.commit()
    return {"message": f"Assigned {count} issues"}


@router.post("/reassign")
def reassign_issue(
    issue_id: UUID,
    worker_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Reassign an issue to a different worker"""
    issue = AdminService.reassign_issue(session, issue_id, worker_id, current_user.id)
    session.commit()
    worker = session.get(User, worker_id)
    return {"message": f"Issue reassigned to {worker.full_name or worker.email}"}


@router.post("/unassign")
def unassign_issue(
    issue_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Remove worker assignment and reset issue to REPORTED"""
    issue = session.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    WorkflowService.unassign_worker(session, issue, current_user.id)
    session.commit()
    return {"message": "Issue unassigned and returned to REPORTED"}

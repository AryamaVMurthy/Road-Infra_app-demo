"""Issue assignment and reassignment endpoints."""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db.session import get_session
from app.api.deps import require_admin_user
from app.models.domain import User, Issue
from app.schemas.common import ErrorResponse, MessageResponse
from app.schemas.admin import BulkAssignRequest
from app.services.admin import AdminService
from app.services.workflow_service import WorkflowService

router = APIRouter()


@router.post(
    "/assign",
    response_model=MessageResponse,
    summary="Assign an issue to a worker",
    description="Assign a single reported issue to a worker and record the workflow transition in audit logs.",
    responses={404: {"model": ErrorResponse, "description": "Issue or worker not found"}},
)
def assign_issue(
    issue_id: UUID,
    worker_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin_user),
):
    """Assign an issue to a worker."""
    AdminService.assign_issue(session, issue_id, worker_id, current_user.id)
    session.commit()
    return {"message": "Issue assigned successfully"}


@router.post(
    "/bulk-assign",
    response_model=MessageResponse,
    summary="Bulk assign issues to a worker",
    description="Assign multiple issues to one worker in a single request and return the number of updated issues.",
)
def bulk_assign(
    data: BulkAssignRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin_user),
):
    """Bulk assign multiple issues to a worker."""
    count = AdminService.bulk_assign(
        session, data.issue_ids, data.worker_id, current_user.id
    )
    session.commit()
    return {"message": f"Assigned {count} issues"}


@router.post(
    "/reassign",
    response_model=MessageResponse,
    summary="Reassign an issue",
    description="Move an already assigned issue to a different worker and return the new assignee name in the response message.",
    responses={404: {"model": ErrorResponse, "description": "Issue or worker not found"}},
)
def reassign_issue(
    issue_id: UUID,
    worker_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin_user),
):
    """Reassign an issue to a different worker."""
    issue = AdminService.reassign_issue(session, issue_id, worker_id, current_user.id)
    session.commit()
    worker = session.get(User, worker_id)
    return {"message": f"Issue reassigned to {worker.full_name or worker.email}"}


@router.post(
    "/unassign",
    response_model=MessageResponse,
    summary="Unassign a worker from an issue",
    description="Remove the worker assignment from an issue and return it to the REPORTED state.",
    responses={404: {"model": ErrorResponse, "description": "Issue not found"}},
)
def unassign_issue(
    issue_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin_user),
):
    """Remove worker assignment and reset issue to REPORTED."""
    issue = session.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    WorkflowService.unassign_worker(session, issue, current_user.id)
    session.commit()
    return {"message": "Issue unassigned and returned to REPORTED"}

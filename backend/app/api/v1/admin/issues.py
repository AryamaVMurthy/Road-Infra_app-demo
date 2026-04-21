"""Admin issue management endpoints."""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from app.db.session import get_session
from app.api.deps import require_admin_user
from app.models.domain import User, Issue, Category
from app.schemas.common import ErrorResponse, MessageResponse
from app.schemas.issue import IssueRead, IssueCategoryAssignmentRequest
from app.services.workflow_service import WorkflowService
from app.services.audit import AuditService

router = APIRouter()


@router.get("/issues", response_model=List[IssueRead])
def get_all_issues(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin_user),
):
    """Get all issues with eager loaded relationships"""
    statement = select(Issue).options(
        selectinload(Issue.category), selectinload(Issue.worker)
    )
    if current_user.role == "ADMIN":
        statement = statement.where(Issue.org_id == current_user.org_id)
    return session.exec(statement).all()


@router.post(
    "/update-status",
    response_model=MessageResponse,
    summary="Update issue workflow status",
    description="Transition an issue to a new workflow state using the centralized workflow service and audit the change.",
    responses={404: {"model": ErrorResponse, "description": "Issue not found"}},
)
def update_issue_status(
    issue_id: UUID,
    status: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin_user),
):
    """Update issue status with proper workflow management"""
    issue = session.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    WorkflowService.update_status(session, issue, status, current_user.id)
    session.commit()
    return {"message": f"Issue status updated to {status}"}


@router.post(
    "/approve",
    response_model=MessageResponse,
    summary="Approve a resolved issue",
    description="Approve a worker resolution and close the issue as the final administrative workflow step.",
    responses={404: {"model": ErrorResponse, "description": "Issue not found"}},
)
def approve_issue(
    issue_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin_user),
):
    """Approve a resolved issue and close it"""
    issue = session.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    WorkflowService.approve_resolution(session, issue, current_user.id)
    session.commit()
    return {"message": "Issue approved and closed"}


@router.post(
    "/reject",
    response_model=MessageResponse,
    summary="Reject a resolved issue",
    description="Reject a resolution with a reason and send the issue back to the assigned worker for rework.",
    responses={404: {"model": ErrorResponse, "description": "Issue not found"}},
)
def reject_issue(
    issue_id: UUID,
    reason: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin_user),
):
    """Reject a resolved issue and return it to worker"""
    issue = session.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    WorkflowService.reject_resolution(session, issue, reason, current_user.id)
    session.commit()
    return {"message": "Issue rejected and returned to worker"}


@router.post(
    "/update-priority",
    response_model=MessageResponse,
    summary="Update issue priority",
    description="Set the issue priority band used for operational triage and record the change in the audit trail.",
    responses={
        400: {"model": ErrorResponse, "description": "Priority is invalid"},
        404: {"model": ErrorResponse, "description": "Issue not found"},
    },
)
def update_issue_priority(
    issue_id: UUID,
    priority: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin_user),
):
    """Update issue priority and audit the change."""
    if priority not in ["P1", "P2", "P3", "P4"]:
        raise HTTPException(
            status_code=400, detail="Invalid priority. Must be P1, P2, P3, or P4"
        )

    issue = session.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    old_priority = issue.priority
    issue.priority = priority
    session.add(issue)

    AuditService.log(
        session,
        "PRIORITY_CHANGE",
        "ISSUE",
        issue_id,
        current_user.id,
        old_priority,
        priority,
    )
    session.commit()
    return {"message": f"Issue priority updated to {priority}"}


@router.post(
    "/issues/{issue_id}/assign-category",
    response_model=MessageResponse,
    summary="Assign or reassign an issue category",
    description="Allow admin or sysadmin users to manually assign the category for uncategorized issues and later correct it if needed.",
)
def assign_issue_category(
    issue_id: UUID,
    data: IssueCategoryAssignmentRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin_user),
):
    issue = session.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    if current_user.role == "ADMIN" and issue.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Issue not found")

    category = session.get(Category, data.category_id)
    if not category or not category.is_active:
        raise HTTPException(status_code=404, detail="Issue category not found")

    old_category_id = issue.category_id
    issue.category_id = category.id
    session.add(issue)
    AuditService.log(
        session,
        "CATEGORY_ASSIGNED" if old_category_id is None else "CATEGORY_REASSIGNED",
        "ISSUE",
        issue.id,
        current_user.id,
        str(old_category_id) if old_category_id is not None else None,
        str(category.id),
    )
    session.commit()
    return {"message": "Issue category updated"}

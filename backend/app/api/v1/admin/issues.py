"""Admin issue management endpoints."""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from app.db.session import get_session
from app.api.deps import require_admin_user
from app.models.domain import User, Issue
from app.schemas.issue import IssueRead
from app.services.workflow_service import WorkflowService

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


@router.post("/update-status")
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


@router.post("/approve")
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


@router.post("/reject")
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


@router.post("/update-priority")
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

    from app.services.audit import AuditService

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

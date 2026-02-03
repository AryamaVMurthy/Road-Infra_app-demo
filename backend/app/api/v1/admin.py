from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, col
from app.db.session import get_session
from app.models.domain import Issue, User, Organization, Category, Invite
from typing import List
from uuid import UUID, uuid4
from app.api.deps import get_current_user
from app.services.audit import AuditService
from app.services.admin import AdminService
from app.schemas.admin import BulkAssignRequest
from app.schemas.issue import IssueRead

router = APIRouter()


@router.get("/issues", response_model=List[IssueRead])
def get_all_issues(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return session.exec(select(Issue)).all()


@router.get("/workers", response_model=List[User])
def get_workers(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return session.exec(select(User).where(User.role == "WORKER")).all()


@router.post("/invite-worker")
def invite_worker(
    email: str,
    org_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    invite = Invite(
        email=email, org_id=org_id, status="INVITED", expires_at=uuid4()
    )  # Placeholder
    session.add(invite)
    AuditService.log(
        session, "INVITE_WORKER", "USER", uuid4(), current_user.id, None, email
    )
    session.commit()
    return {"message": f"Invite sent to {email}"}


@router.post("/deactivate-worker")
def deactivate_worker(
    worker_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    AdminService.deactivate_worker(session, worker_id, current_user.id)
    session.commit()
    return {"message": "Worker deactivated and tasks reset"}


@router.post("/bulk-assign")
def bulk_assign(
    data: BulkAssignRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    count = AdminService.bulk_assign(
        session, data.issue_ids, data.worker_id, current_user.id
    )
    session.commit()
    return {"message": f"Assigned {count} issues"}


@router.get("/categories", response_model=List[Category])
def get_categories(session: Session = Depends(get_session)):
    return session.exec(select(Category).where(Category.is_active == True)).all()


@router.post("/assign")
def assign_issue(
    issue_id: UUID,
    worker_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    issue = session.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    old_worker = str(issue.worker_id)
    issue.worker_id = worker_id
    issue.status = "ASSIGNED"
    session.add(issue)
    AuditService.log(
        session,
        "ASSIGNMENT",
        "ISSUE",
        issue_id,
        current_user.id,
        old_worker,
        str(worker_id),
    )
    session.commit()
    return {"message": "Issue assigned successfully"}


@router.post("/approve")
def approve_issue(
    issue_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    issue = session.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    old_status = issue.status
    issue.status = "CLOSED"
    session.add(issue)
    AuditService.log(
        session,
        "STATUS_CHANGE",
        "ISSUE",
        issue_id,
        current_user.id,
        old_status,
        "CLOSED",
    )
    session.commit()
    return {"message": "Issue approved and closed"}


@router.post("/reject")
def reject_issue(
    issue_id: UUID,
    reason: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    issue = session.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    old_status = issue.status
    issue.status = "IN_PROGRESS"
    issue.rejection_reason = reason
    session.add(issue)
    AuditService.log(
        session,
        "STATUS_CHANGE",
        "ISSUE",
        issue_id,
        current_user.id,
        old_status,
        "IN_PROGRESS",
    )
    session.commit()
    return {"message": "Issue rejected and returned to worker"}

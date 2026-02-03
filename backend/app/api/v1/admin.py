from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, col, func
from sqlalchemy.orm import selectinload
from app.db.session import get_session
from app.models.domain import Issue, User, Organization, Category, Invite
from typing import List
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from app.api.deps import get_current_user
from app.services.audit import AuditService
from app.services.admin import AdminService
from app.schemas.admin import (
    BulkAssignRequest,
    WorkerWithStats,
    WorkerPerformance,
    WorkerAnalyticsResponse,
)
from app.schemas.issue import IssueRead

router = APIRouter()


@router.get("/issues", response_model=List[IssueRead])
def get_all_issues(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    # Eagerly load relationships for worker_name and category_name
    statement = select(Issue).options(
        selectinload(Issue.category), selectinload(Issue.worker)
    )
    return session.exec(statement).all()


@router.get("/workers", response_model=List[User])
def get_workers(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return session.exec(select(User).where(User.role == "WORKER")).all()


@router.get("/workers-with-stats", response_model=List[WorkerWithStats])
def get_workers_with_stats(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get all workers with their current task counts for assignment dropdown"""
    workers = session.exec(select(User).where(User.role == "WORKER")).all()

    result = []
    for worker in workers:
        # Count active tasks (not RESOLVED or CLOSED)
        active_count = session.exec(
            select(func.count(Issue.id)).where(
                Issue.worker_id == worker.id,
                Issue.status.in_(["ASSIGNED", "ACCEPTED", "IN_PROGRESS"]),
            )
        ).one()

        # Count total assigned
        total_assigned = session.exec(
            select(func.count(Issue.id)).where(Issue.worker_id == worker.id)
        ).one()

        # Count resolved
        resolved_count = session.exec(
            select(func.count(Issue.id)).where(
                Issue.worker_id == worker.id, Issue.status.in_(["RESOLVED", "CLOSED"])
            )
        ).one()

        result.append(
            WorkerWithStats(
                id=worker.id,
                email=worker.email,
                full_name=worker.full_name,
                status=worker.status,
                active_task_count=active_count,
                total_assigned=total_assigned,
                resolved_count=resolved_count,
            )
        )

    # Sort by active task count (least busy first)
    result.sort(key=lambda w: w.active_task_count)
    return result


@router.get("/worker-analytics", response_model=WorkerAnalyticsResponse)
def get_worker_analytics(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get detailed worker analytics for dashboard"""
    workers = session.exec(select(User).where(User.role == "WORKER")).all()

    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    worker_stats = []
    total_active = 0
    total_resolved = 0

    for worker in workers:
        # Pending acceptance (ASSIGNED)
        pending = session.exec(
            select(func.count(Issue.id)).where(
                Issue.worker_id == worker.id, Issue.status == "ASSIGNED"
            )
        ).one()

        # In progress (ACCEPTED or IN_PROGRESS)
        in_progress = session.exec(
            select(func.count(Issue.id)).where(
                Issue.worker_id == worker.id,
                Issue.status.in_(["ACCEPTED", "IN_PROGRESS"]),
            )
        ).one()

        # Resolved
        resolved = session.exec(
            select(func.count(Issue.id)).where(
                Issue.worker_id == worker.id, Issue.status == "RESOLVED"
            )
        ).one()

        # Closed
        closed = session.exec(
            select(func.count(Issue.id)).where(
                Issue.worker_id == worker.id, Issue.status == "CLOSED"
            )
        ).one()

        # Tasks this week
        tasks_week = session.exec(
            select(func.count(Issue.id)).where(
                Issue.worker_id == worker.id,
                Issue.status.in_(["RESOLVED", "CLOSED"]),
                Issue.resolved_at >= week_ago,
            )
        ).one()

        # Tasks this month
        tasks_month = session.exec(
            select(func.count(Issue.id)).where(
                Issue.worker_id == worker.id,
                Issue.status.in_(["RESOLVED", "CLOSED"]),
                Issue.resolved_at >= month_ago,
            )
        ).one()

        # Calculate average resolution time (hours)
        resolved_issues = session.exec(
            select(Issue).where(
                Issue.worker_id == worker.id,
                Issue.status.in_(["RESOLVED", "CLOSED"]),
                Issue.accepted_at.isnot(None),
                Issue.resolved_at.isnot(None),
            )
        ).all()

        avg_hours = None
        if resolved_issues:
            total_hours = sum(
                (i.resolved_at - i.accepted_at).total_seconds() / 3600
                for i in resolved_issues
                if i.accepted_at and i.resolved_at
            )
            avg_hours = (
                round(total_hours / len(resolved_issues), 1)
                if resolved_issues
                else None
            )

        active = pending + in_progress
        total_active += active
        total_resolved += resolved + closed

        worker_stats.append(
            WorkerPerformance(
                worker_id=worker.id,
                worker_name=worker.full_name or worker.email,
                email=worker.email,
                active_tasks=active,
                pending_acceptance=pending,
                in_progress=in_progress,
                total_resolved=resolved,
                total_closed=closed,
                avg_resolution_hours=avg_hours,
                tasks_this_week=tasks_week,
                tasks_this_month=tasks_month,
            )
        )

    # Sort by tasks this week (most productive first)
    worker_stats.sort(key=lambda w: w.tasks_this_week, reverse=True)

    return WorkerAnalyticsResponse(
        workers=worker_stats,
        summary={
            "total_workers": len(workers),
            "total_active_tasks": total_active,
            "total_resolved": total_resolved,
            "avg_tasks_per_worker": round(total_active / len(workers), 1)
            if workers
            else 0,
        },
    )


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


VALID_STATUSES = [
    "REPORTED",
    "ASSIGNED",
    "ACCEPTED",
    "IN_PROGRESS",
    "RESOLVED",
    "CLOSED",
]


@router.post("/update-status")
def update_issue_status(
    issue_id: UUID,
    status: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400, detail=f"Invalid status. Must be one of: {VALID_STATUSES}"
        )

    issue = session.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    old_status = issue.status
    issue.status = status

    if status == "REPORTED":
        issue.worker_id = None
        issue.accepted_at = None
        issue.started_at = None
        issue.resolved_at = None
        issue.eta_hours = None
    elif status in ["ASSIGNED"]:
        issue.accepted_at = None
        issue.started_at = None
        issue.resolved_at = None
    elif status == "ACCEPTED":
        if not issue.accepted_at:
            issue.accepted_at = datetime.utcnow()
        issue.started_at = None
        issue.resolved_at = None
    elif status == "IN_PROGRESS":
        if not issue.started_at:
            issue.started_at = datetime.utcnow()
        issue.resolved_at = None
    elif status == "RESOLVED":
        if not issue.resolved_at:
            issue.resolved_at = datetime.utcnow()

    session.add(issue)
    AuditService.log(
        session,
        "STATUS_CHANGE",
        "ISSUE",
        issue_id,
        current_user.id,
        old_status,
        status,
    )
    session.commit()
    return {"message": f"Issue status updated to {status}"}


@router.post("/unassign")
def unassign_issue(
    issue_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    issue = session.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    old_worker = str(issue.worker_id) if issue.worker_id else None
    old_status = issue.status

    issue.worker_id = None
    issue.status = "REPORTED"
    issue.accepted_at = None
    issue.started_at = None
    issue.resolved_at = None
    issue.eta_hours = None

    session.add(issue)
    AuditService.log(
        session,
        "UNASSIGNMENT",
        "ISSUE",
        issue_id,
        current_user.id,
        f"worker:{old_worker},status:{old_status}",
        "unassigned,REPORTED",
    )
    session.commit()
    return {"message": "Issue unassigned and returned to REPORTED"}


@router.post("/reassign")
def reassign_issue(
    issue_id: UUID,
    worker_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    issue = session.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    worker = session.get(User, worker_id)
    if not worker or worker.role != "WORKER":
        raise HTTPException(status_code=404, detail="Worker not found")

    old_worker = str(issue.worker_id) if issue.worker_id else None
    old_status = issue.status

    issue.worker_id = worker_id
    issue.status = "ASSIGNED"
    issue.accepted_at = None
    issue.started_at = None
    issue.resolved_at = None

    session.add(issue)
    AuditService.log(
        session,
        "REASSIGNMENT",
        "ISSUE",
        issue_id,
        current_user.id,
        f"worker:{old_worker},status:{old_status}",
        f"worker:{worker_id},status:ASSIGNED",
    )
    session.commit()
    return {"message": f"Issue reassigned to {worker.full_name or worker.email}"}

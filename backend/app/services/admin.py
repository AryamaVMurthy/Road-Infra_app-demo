"""
Admin Service - Handles assignment and administrative operations
"""

from sqlmodel import Session
from app.models.domain import Issue, User
from app.services.audit import AuditService
from uuid import UUID
from typing import List
from fastapi import HTTPException


class AdminService:
    """Service for administrative operations like assignments"""

    @staticmethod
    def assign_issue(
        session: Session, issue_id: UUID, worker_id: UUID, actor_id: UUID
    ) -> Issue:
        """Assign a single issue to a worker"""
        issue = session.get(Issue, issue_id)
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found")

        worker = session.get(User, worker_id)
        if not worker or worker.status != "ACTIVE":
            raise HTTPException(status_code=400, detail="Invalid or inactive worker")

        old_worker = str(issue.worker_id) if issue.worker_id else None
        issue.worker_id = worker_id
        issue.status = "ASSIGNED"
        session.add(issue)

        AuditService.log(
            session,
            "ASSIGNMENT",
            "ISSUE",
            issue_id,
            actor_id,
            old_worker or "NONE",
            str(worker_id),
        )

        return issue

    @staticmethod
    def bulk_assign(
        session: Session, issue_ids: List[UUID], worker_id: UUID, actor_id: UUID
    ) -> int:
        """Bulk assign multiple issues to a worker. Returns count of assigned issues."""
        worker = session.get(User, worker_id)
        if not worker or worker.status != "ACTIVE":
            raise HTTPException(status_code=400, detail="Invalid or inactive worker")

        count = 0
        for issue_id in issue_ids:
            issue = session.get(Issue, issue_id)
            if issue and issue.status == "REPORTED":
                issue.worker_id = worker_id
                issue.status = "ASSIGNED"
                session.add(issue)
                AuditService.log(
                    session,
                    "ASSIGNMENT",
                    "ISSUE",
                    issue_id,
                    actor_id,
                    "NONE",
                    str(worker_id),
                )
                count += 1
        return count

    @staticmethod
    def reassign_issue(
        session: Session, issue_id: UUID, new_worker_id: UUID, actor_id: UUID
    ) -> Issue:
        """Reassign an issue to a different worker"""
        issue = session.get(Issue, issue_id)
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found")

        new_worker = session.get(User, new_worker_id)
        if not new_worker or new_worker.role != "WORKER":
            raise HTTPException(status_code=404, detail="Worker not found")

        old_worker = str(issue.worker_id) if issue.worker_id else None
        old_status = issue.status

        issue.worker_id = new_worker_id
        issue.status = "ASSIGNED"
        issue.accepted_at = None
        issue.resolved_at = None

        session.add(issue)
        AuditService.log(
            session,
            "REASSIGNMENT",
            "ISSUE",
            issue_id,
            actor_id,
            f"worker:{old_worker},status:{old_status}",
            f"worker:{new_worker_id},status:ASSIGNED",
        )

        return issue

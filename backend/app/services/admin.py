from sqlmodel import Session, select, col
from app.models.domain import Issue, User, AuditLog
from app.services.audit import AuditService
from uuid import UUID
from typing import List, Optional
from fastapi import HTTPException


class AdminService:
    @staticmethod
    def bulk_assign(
        session: Session, issue_ids: List[UUID], worker_id: UUID, actor_id: UUID
    ) -> int:
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
    def deactivate_worker(session: Session, worker_id: UUID, actor_id: UUID):
        worker = session.get(User, worker_id)
        if not worker:
            raise HTTPException(status_code=404, detail="Worker not found")

        worker.status = "INACTIVE"
        session.add(worker)

        statement = select(Issue).where(
            Issue.worker_id == worker_id,
            col(Issue.status).in_(["ASSIGNED", "IN_PROGRESS"]),
        )
        active_tasks = session.exec(statement).all()
        for task in active_tasks:
            AuditService.log(
                session,
                "AUTO_UNASSIGN",
                "ISSUE",
                task.id,
                actor_id,
                str(worker_id),
                "NONE",
            )
            task.worker_id = None
            task.status = "REPORTED"
            session.add(task)

        AuditService.log(
            session,
            "DEACTIVATE_WORKER",
            "USER",
            worker_id,
            actor_id,
            "ACTIVE",
            "INACTIVE",
        )

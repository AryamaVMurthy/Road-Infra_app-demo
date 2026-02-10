"""
Worker Service - Handles worker management and operations
"""

from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException
from sqlmodel import Session, select, col

from app.models.domain import Issue, User
from app.services.audit import AuditService

class WorkerService:
    """Service for managing workers and their tasks"""

    @staticmethod
    def get_all_workers(session: Session, org_id: Optional[UUID] = None) -> List[User]:
        """Get all workers, optionally filtered by organization"""
        statement = select(User).where(User.role == "WORKER")
        if org_id is not None:
            statement = statement.where(User.org_id == org_id)
        return list(session.exec(statement).all())

    @staticmethod
    def bulk_register_workers(
        session: Session,
        actor: User,
        emails: List[str],
    ) -> dict:
        if actor.role != "SYSADMIN" and actor.org_id is None:
            raise HTTPException(
                status_code=400,
                detail="Admin account must be linked to an authority before onboarding workers",
            )

        created: List[str] = []
        reactivated: List[str] = []
        skipped: List[str] = []

        for raw_email in emails:
            email = raw_email.strip().lower()
            if not email:
                continue

            existing = session.exec(select(User).where(User.email == email)).first()
            if existing and existing.role not in {"WORKER", "ADMIN"}:
                skipped.append(email)
                continue

            if existing:
                if existing.role == "ADMIN":
                    skipped.append(email)
                    continue
                existing.role = "WORKER"
                existing.org_id = actor.org_id
                if existing.status != "ACTIVE":
                    existing.status = "ACTIVE"
                    reactivated.append(email)
                else:
                    skipped.append(email)
                session.add(existing)
                continue

            worker = User(
                email=email,
                role="WORKER",
                org_id=actor.org_id,
                status="ACTIVE",
            )
            session.add(worker)
            created.append(email)

        AuditService.log(
            session,
            "WORKER_BULK_REGISTER",
            "USER",
            actor.id,
            actor.id,
            None,
            f"created={len(created)},reactivated={len(reactivated)},skipped={len(skipped)}",
        )
        return {"created": created, "reactivated": reactivated, "skipped": skipped}

    @staticmethod
    def get_worker_by_id(session: Session, worker_id: UUID) -> User:
        """Get a specific worker by ID"""
        worker = session.get(User, worker_id)
        if not worker or worker.role != "WORKER":
            raise HTTPException(status_code=404, detail="Worker not found")
        return worker

    @staticmethod
    def deactivate_worker(session: Session, worker_id: UUID, actor_id: UUID) -> User:
        """
        Deactivate a worker and unassign their active tasks.
        Returns the deactivated worker.
        """
        worker = session.get(User, worker_id)
        if not worker:
            raise HTTPException(status_code=404, detail="Worker not found")

        worker.status = "INACTIVE"
        session.add(worker)

        # Unassign active tasks
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

        return worker

    @staticmethod
    def activate_worker(session: Session, worker_id: UUID, actor_id: UUID) -> User:
        worker = session.get(User, worker_id)
        if not worker or worker.role != "WORKER":
            raise HTTPException(status_code=404, detail="Worker not found")

        old_status = worker.status
        worker.status = "ACTIVE"
        session.add(worker)
        AuditService.log(
            session,
            "ACTIVATE_WORKER",
            "USER",
            worker_id,
            actor_id,
            old_status,
            "ACTIVE",
        )
        return worker

    @staticmethod
    def get_worker_tasks(session: Session, worker_id: UUID) -> List[Issue]:
        """Get all tasks assigned to a worker"""
        return list(
            session.exec(select(Issue).where(Issue.worker_id == worker_id)).all()
        )

    @staticmethod
    def get_active_tasks(session: Session, worker_id: UUID) -> List[Issue]:
        """Get active tasks (not RESOLVED or CLOSED) for a worker"""
        return list(
            session.exec(
                select(Issue).where(
                    Issue.worker_id == worker_id,
                    col(Issue.status).in_(["ASSIGNED", "ACCEPTED", "IN_PROGRESS"]),
                )
            ).all()
        )

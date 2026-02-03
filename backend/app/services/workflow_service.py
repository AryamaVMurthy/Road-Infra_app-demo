"""
Workflow Service - Manages issue lifecycle and status transitions
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from fastapi import HTTPException
from sqlmodel import Session

from app.models.domain import Issue
from app.services.audit import AuditService


# Valid status transitions
VALID_STATUSES = [
    "REPORTED",
    "ASSIGNED",
    "ACCEPTED",
    "IN_PROGRESS",
    "RESOLVED",
    "CLOSED",
]


class WorkflowService:
    """Service for managing issue workflow and status transitions"""

    @staticmethod
    def validate_status(status: str) -> None:
        """Validate that a status is valid"""
        if status not in VALID_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {VALID_STATUSES}",
            )

    @staticmethod
    def update_status(
        session: Session,
        issue: Issue,
        new_status: str,
        actor_id: UUID,
        rejection_reason: Optional[str] = None,
    ) -> Issue:
        """
        Update issue status with proper state management.
        Handles timestamp updates and field resets based on status.
        """
        WorkflowService.validate_status(new_status)

        old_status = issue.status
        issue.status = new_status

        # Reset or set fields based on new status
        if new_status == "REPORTED":
            issue.worker_id = None
            issue.accepted_at = None
            issue.resolved_at = None
            issue.eta_duration = None
        elif new_status in ["ASSIGNED"]:
            issue.accepted_at = None
            issue.resolved_at = None
        elif new_status == "ACCEPTED":
            if not issue.accepted_at:
                issue.accepted_at = datetime.utcnow()
            issue.resolved_at = None
        elif new_status == "IN_PROGRESS":
            issue.resolved_at = None
        elif new_status == "RESOLVED":
            if not issue.resolved_at:
                issue.resolved_at = datetime.utcnow()

        # Handle rejection reason
        if rejection_reason:
            issue.rejection_reason = rejection_reason

        session.add(issue)

        # Log the status change
        AuditService.log(
            session,
            "STATUS_CHANGE",
            "ISSUE",
            issue.id,
            actor_id,
            old_status,
            new_status,
        )

        return issue

    @staticmethod
    def approve_resolution(
        session: Session,
        issue: Issue,
        actor_id: UUID,
    ) -> Issue:
        """Approve a resolved issue and move it to CLOSED status"""
        old_status = issue.status
        issue.status = "CLOSED"
        session.add(issue)

        AuditService.log(
            session,
            "STATUS_CHANGE",
            "ISSUE",
            issue.id,
            actor_id,
            old_status,
            "CLOSED",
        )

        return issue

    @staticmethod
    def reject_resolution(
        session: Session,
        issue: Issue,
        reason: str,
        actor_id: UUID,
    ) -> Issue:
        """Reject a resolved issue and return it to IN_PROGRESS"""
        old_status = issue.status
        issue.status = "IN_PROGRESS"
        issue.rejection_reason = reason
        session.add(issue)

        AuditService.log(
            session,
            "STATUS_CHANGE",
            "ISSUE",
            issue.id,
            actor_id,
            old_status,
            "IN_PROGRESS",
        )

        return issue

    @staticmethod
    def unassign_worker(
        session: Session,
        issue: Issue,
        actor_id: UUID,
    ) -> Issue:
        """Remove worker assignment and reset to REPORTED status"""
        old_worker = str(issue.worker_id) if issue.worker_id else None
        old_status = issue.status

        issue.worker_id = None
        issue.status = "REPORTED"
        issue.accepted_at = None
        issue.resolved_at = None
        issue.eta_duration = None

        session.add(issue)

        AuditService.log(
            session,
            "UNASSIGNMENT",
            "ISSUE",
            issue.id,
            actor_id,
            f"worker:{old_worker},status:{old_status}",
            "unassigned,REPORTED",
        )

        return issue

    @staticmethod
    def accept_task(
        session: Session,
        issue: Issue,
        eta_duration: str,
        worker_id: UUID,
    ) -> Issue:
        """Worker accepts a task with ETA"""
        issue.status = "ACCEPTED"
        issue.eta_duration = eta_duration
        issue.accepted_at = datetime.utcnow()
        session.add(issue)

        AuditService.log(
            session,
            "STATUS_CHANGE",
            "ISSUE",
            issue.id,
            worker_id,
            "ASSIGNED",
            "ACCEPTED",
        )

        return issue

    @staticmethod
    def start_task(
        session: Session,
        issue: Issue,
        worker_id: UUID,
    ) -> Issue:
        """Worker starts working on a task"""
        old_status = issue.status
        issue.status = "IN_PROGRESS"
        session.add(issue)

        AuditService.log(
            session,
            "STATUS_CHANGE",
            "ISSUE",
            issue.id,
            worker_id,
            old_status,
            "IN_PROGRESS",
        )

        return issue

    @staticmethod
    def resolve_task(
        session: Session,
        issue: Issue,
        worker_id: UUID,
    ) -> Issue:
        """Worker marks task as resolved"""
        old_status = issue.status
        issue.status = "RESOLVED"
        issue.resolved_at = datetime.utcnow()
        session.add(issue)

        AuditService.log(
            session,
            "STATUS_CHANGE",
            "ISSUE",
            issue.id,
            worker_id,
            old_status,
            "RESOLVED",
        )

        return issue

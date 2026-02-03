"""
Analytics Service - Handles all analytics and statistics calculations
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlmodel import Session, select, func
from uuid import UUID

from app.models.domain import Issue, User


class AnalyticsService:
    """Service for computing analytics and statistics"""

    @staticmethod
    def get_worker_analytics(session: Session) -> Dict[str, Any]:
        """
        Get comprehensive analytics for all workers.
        Returns worker stats with task counts and performance metrics.
        """
        workers = session.exec(select(User).where(User.role == "WORKER")).all()

        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        worker_stats = []
        total_active = 0
        total_resolved = 0

        for worker in workers:
            stats = AnalyticsService._compute_worker_stats(
                session, worker, week_ago, month_ago
            )
            worker_stats.append(stats)

            total_active += stats["active_tasks"]
            total_resolved += stats["total_resolved"] + stats["total_closed"]

        # Sort by tasks this week (most productive first)
        worker_stats.sort(key=lambda w: w["tasks_this_week"], reverse=True)

        return {
            "workers": worker_stats,
            "summary": {
                "total_workers": len(workers),
                "total_active_tasks": total_active,
                "total_resolved": total_resolved,
                "avg_tasks_per_worker": round(total_active / len(workers), 1)
                if workers
                else 0,
            },
        }

    @staticmethod
    def _compute_worker_stats(
        session: Session, worker: User, week_ago: datetime, month_ago: datetime
    ) -> Dict[str, Any]:
        """Compute statistics for a single worker"""
        worker_id = worker.id

        # Pending acceptance (ASSIGNED)
        pending = session.exec(
            select(func.count(Issue.id)).where(
                Issue.worker_id == worker_id, Issue.status == "ASSIGNED"
            )
        ).one()

        # In progress (ACCEPTED or IN_PROGRESS)
        in_progress = session.exec(
            select(func.count(Issue.id)).where(
                Issue.worker_id == worker_id,
                Issue.status.in_(["ACCEPTED", "IN_PROGRESS"]),
            )
        ).one()

        # Resolved
        resolved = session.exec(
            select(func.count(Issue.id)).where(
                Issue.worker_id == worker_id, Issue.status == "RESOLVED"
            )
        ).one()

        # Closed
        closed = session.exec(
            select(func.count(Issue.id)).where(
                Issue.worker_id == worker_id, Issue.status == "CLOSED"
            )
        ).one()

        # Tasks this week
        tasks_week = session.exec(
            select(func.count(Issue.id)).where(
                Issue.worker_id == worker_id,
                Issue.status.in_(["RESOLVED", "CLOSED"]),
                Issue.resolved_at >= week_ago,
            )
        ).one()

        # Tasks this month
        tasks_month = session.exec(
            select(func.count(Issue.id)).where(
                Issue.worker_id == worker_id,
                Issue.status.in_(["RESOLVED", "CLOSED"]),
                Issue.resolved_at >= month_ago,
            )
        ).one()

        # Calculate average resolution time
        avg_hours = AnalyticsService._compute_avg_resolution_time(session, worker_id)

        return {
            "worker_id": worker_id,
            "worker_name": worker.full_name or worker.email,
            "email": worker.email,
            "active_tasks": pending + in_progress,
            "pending_acceptance": pending,
            "in_progress": in_progress,
            "total_resolved": resolved,
            "total_closed": closed,
            "avg_resolution_hours": avg_hours,
            "tasks_this_week": tasks_week,
            "tasks_this_month": tasks_month,
        }

    @staticmethod
    def _compute_avg_resolution_time(
        session: Session, worker_id: UUID
    ) -> Optional[float]:
        """Calculate average resolution time in hours for a worker"""
        resolved_issues = session.exec(
            select(Issue).where(
                Issue.worker_id == worker_id,
                Issue.status.in_(["RESOLVED", "CLOSED"]),
                Issue.accepted_at.isnot(None),
                Issue.resolved_at.isnot(None),
            )
        ).all()

        if not resolved_issues:
            return None

        total_hours = sum(
            (issue.resolved_at - issue.accepted_at).total_seconds() / 3600
            for issue in resolved_issues
            if issue.accepted_at and issue.resolved_at
        )

        return round(total_hours / len(resolved_issues), 1) if resolved_issues else None

    @staticmethod
    def get_workers_with_stats(session: Session) -> List[Dict[str, Any]]:
        """
        Get all workers with their current task counts for assignment dropdown.
        Returns workers sorted by workload (least busy first).
        """
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
                    Issue.worker_id == worker.id,
                    Issue.status.in_(["RESOLVED", "CLOSED"]),
                )
            ).one()

            result.append(
                {
                    "id": worker.id,
                    "email": worker.email,
                    "full_name": worker.full_name,
                    "status": worker.status,
                    "active_task_count": active_count,
                    "total_assigned": total_assigned,
                    "resolved_count": resolved_count,
                }
            )

        # Sort by active task count (least busy first)
        result.sort(key=lambda w: w["active_task_count"])
        return result

    @staticmethod
    def get_dashboard_stats(session: Session) -> Dict[str, int]:
        """Get quick dashboard statistics"""
        return {
            "reported": session.exec(
                select(func.count(Issue.id)).where(Issue.status == "REPORTED")
            ).one(),
            "in_progress": session.exec(
                select(func.count(Issue.id)).where(
                    Issue.status.in_(["ASSIGNED", "ACCEPTED", "IN_PROGRESS"])
                )
            ).one(),
            "resolved": session.exec(
                select(func.count(Issue.id)).where(
                    Issue.status.in_(["RESOLVED", "CLOSED"])
                )
            ).one(),
        }

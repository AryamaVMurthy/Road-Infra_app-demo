"""Admin analytics service for worker and dashboard metrics."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlmodel import Session, col, func, select

from app.models.domain import Issue, User
from app.core.time import utc_now


class AdminAnalyticsService:
    """Service for computing admin analytics and statistics."""

    @staticmethod
    def get_worker_analytics(
        session: Session, org_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive analytics for all workers.
        Returns worker stats with task counts and performance metrics.
        """
        statement = select(User).where(col(User.role) == "WORKER")
        if org_id is not None:
            statement = statement.where(col(User.org_id) == org_id)
        workers = session.exec(statement).all()

        now = utc_now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        worker_stats: List[Dict[str, Any]] = []
        total_active = 0
        total_resolved = 0

        for worker in workers:
            stats = AdminAnalyticsService._compute_worker_stats(
                session, worker, week_ago, month_ago
            )
            worker_stats.append(stats)
            total_active += stats["active_tasks"]
            total_resolved += stats["total_resolved"] + stats["total_closed"]

        worker_stats.sort(
            key=lambda worker_stat: worker_stat["tasks_this_week"], reverse=True
        )

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
    def _count_worker_issues(
        session: Session,
        worker_id: UUID,
        statuses: Optional[List[str]] = None,
        resolved_after: Optional[datetime] = None,
    ) -> int:
        statement = (
            select(func.count())
            .select_from(Issue)
            .where(col(Issue.worker_id) == worker_id)
        )

        if statuses is not None:
            statement = statement.where(col(Issue.status).in_(statuses))

        if resolved_after is not None:
            statement = statement.where(col(Issue.resolved_at) >= resolved_after)

        return session.exec(statement).one()

    @staticmethod
    def _compute_worker_stats(
        session: Session, worker: User, week_ago: datetime, month_ago: datetime
    ) -> Dict[str, Any]:
        """Compute statistics for a single worker"""
        worker_id = worker.id

        pending = AdminAnalyticsService._count_worker_issues(
            session, worker_id, statuses=["ASSIGNED"]
        )
        in_progress = AdminAnalyticsService._count_worker_issues(
            session, worker_id, statuses=["ACCEPTED", "IN_PROGRESS"]
        )
        resolved = AdminAnalyticsService._count_worker_issues(
            session, worker_id, statuses=["RESOLVED"]
        )
        closed = AdminAnalyticsService._count_worker_issues(
            session, worker_id, statuses=["CLOSED"]
        )
        tasks_week = AdminAnalyticsService._count_worker_issues(
            session,
            worker_id,
            statuses=["RESOLVED", "CLOSED"],
            resolved_after=week_ago,
        )
        tasks_month = AdminAnalyticsService._count_worker_issues(
            session,
            worker_id,
            statuses=["RESOLVED", "CLOSED"],
            resolved_after=month_ago,
        )

        avg_hours = AdminAnalyticsService._compute_avg_resolution_time(
            session, worker_id
        )

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
                col(Issue.worker_id) == worker_id,
                col(Issue.status).in_(["RESOLVED", "CLOSED"]),
                col(Issue.accepted_at).is_not(None),
                col(Issue.resolved_at).is_not(None),
            )
        ).all()

        if not resolved_issues:
            return None

        total_hours = sum(
            (issue.resolved_at - issue.accepted_at).total_seconds() / 3600
            for issue in resolved_issues
            if issue.accepted_at and issue.resolved_at
        )

        return round(total_hours / len(resolved_issues), 1)

    @staticmethod
    def get_workers_with_stats(
        session: Session, org_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all workers with their current task counts for assignment dropdown.
        Returns workers sorted by workload (least busy first).
        """
        statement = select(User).where(col(User.role) == "WORKER")
        if org_id is not None:
            statement = statement.where(col(User.org_id) == org_id)
        workers = session.exec(statement).all()

        result: List[Dict[str, Any]] = []
        for worker in workers:
            active_count = AdminAnalyticsService._count_worker_issues(
                session,
                worker.id,
                statuses=["ASSIGNED", "ACCEPTED", "IN_PROGRESS"],
            )
            total_assigned = AdminAnalyticsService._count_worker_issues(
                session, worker.id
            )
            resolved_count = AdminAnalyticsService._count_worker_issues(
                session,
                worker.id,
                statuses=["RESOLVED", "CLOSED"],
            )

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

        result.sort(key=lambda worker_stat: worker_stat["active_task_count"])
        return result

    @staticmethod
    def get_dashboard_stats(session: Session) -> Dict[str, int]:
        """Get quick dashboard statistics"""
        return {
            "reported": session.exec(
                select(func.count())
                .select_from(Issue)
                .where(col(Issue.status) == "REPORTED")
            ).one(),
            "in_progress": session.exec(
                select(func.count())
                .select_from(Issue)
                .where(col(Issue.status).in_(["ASSIGNED", "ACCEPTED", "IN_PROGRESS"]))
            ).one(),
            "resolved": session.exec(
                select(func.count())
                .select_from(Issue)
                .where(col(Issue.status).in_(["RESOLVED", "CLOSED"]))
            ).one(),
        }

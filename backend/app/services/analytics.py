from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlmodel import Session, select, func, col, asc
from uuid import UUID
from app.models.domain import Issue, User, AuditLog, Category

class AnalyticsService:
    @staticmethod
    def get_heatmap_data(session: Session) -> List[dict]:
        try:
            statement = select(Issue).where(Issue.status != "CLOSED")
            issues = session.exec(statement).all()
            data = [{"lat": i.lat, "lng": i.lng, "intensity": 0.5} for i in issues]
            return data
        except Exception as e:
            print(f"Error in get_heatmap_data: {e}")
            return []

    @staticmethod
    def get_audit_trail(session: Session, entity_id: UUID) -> List[AuditLog]:
        statement = (
            select(AuditLog)
            .where(col(AuditLog.entity_id) == entity_id)
            .order_by(col(AuditLog.created_at).asc())
        )
        return list(session.exec(statement).all())

    @staticmethod
    def get_global_stats(session: Session) -> Dict[str, Any]:
        total_reported = session.exec(select(func.count(col(Issue.id)))).one()
        active_workers = session.exec(
            select(func.count(col(User.id))).where(
                col(User.role) == "WORKER", col(User.status) == "ACTIVE"
            )
        ).one()
        resolved_count = session.exec(
            select(func.count(col(Issue.id))).where(col(Issue.status) == "CLOSED")
        ).one()

        categories = session.exec(select(Category)).all()
        category_split = []
        for cat in categories:
            count = session.exec(
                select(func.count(col(Issue.id))).where(col(Issue.category_id) == cat.id)
            ).one()
            category_split.append({"name": cat.name, "value": count})

        statuses = ["REPORTED", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED"]
        status_split = []
        for s in statuses:
            count = session.exec(
                select(func.count(col(Issue.id))).where(col(Issue.status) == s)
            ).one()
            status_split.append({"name": s, "value": count})

        total_issues = session.exec(select(func.count(col(Issue.id)))).one()
        if total_issues > 0:
            compliant_issues = session.exec(
                select(func.count(col(Issue.id))).where(
                    col(Issue.status).in_(["RESOLVED", "CLOSED"])
                )
            ).one()
            compliance_rate = (compliant_issues / total_issues) * 100
            compliance_str = f"{compliance_rate:.1f}%"
        else:
            compliance_str = "N/A"

        trend_data = AnalyticsService._get_trend_data(session)

        return {
            "summary": {
                "reported": total_reported,
                "workers": active_workers,
                "resolved": resolved_count,
                "compliance": compliance_str,
            },
            "category_split": category_split,
            "status_split": status_split,
            "trend": trend_data,
        }

    @staticmethod
    def _get_trend_data(session: Session) -> List[Dict[str, Any]]:
        trend = []
        today = datetime.now().date()
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        for i in range(6, -1, -1):
            target_date = today - timedelta(days=i)
            day_name = day_names[target_date.weekday()]

            reports_count = session.exec(
                select(func.count(col(Issue.id))).where(
                    func.date(col(Issue.created_at)) == target_date
                )
            ).one()

            resolved_count = session.exec(
                select(func.count(col(Issue.id))).where(
                    func.date(col(Issue.updated_at)) == target_date,
                    col(Issue.status).in_(["RESOLVED", "CLOSED"]),
                )
            ).one()

            trend.append(
                {"name": day_name, "reports": reports_count, "resolved": resolved_count}
            )

        return trend

    @staticmethod
    def get_worker_analytics(
        session: Session, org_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        stmt = select(User).where(col(User.role) == "WORKER")
        if org_id:
            stmt = stmt.where(col(User.org_id) == org_id)
        workers = session.exec(stmt).all()

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
        worker_id = worker.id

        pending = session.exec(
            select(func.count(col(Issue.id))).where(
                col(Issue.worker_id) == worker_id, col(Issue.status) == "ASSIGNED"
            )
        ).one()

        in_progress = session.exec(
            select(func.count(col(Issue.id))).where(
                col(Issue.worker_id) == worker_id,
                col(Issue.status).in_(["ACCEPTED", "IN_PROGRESS"]),
            )
        ).one()

        resolved = session.exec(
            select(func.count(col(Issue.id))).where(
                col(Issue.worker_id) == worker_id, col(Issue.status) == "RESOLVED"
            )
        ).one()

        closed = session.exec(
            select(func.count(col(Issue.id))).where(
                col(Issue.worker_id) == worker_id, col(Issue.status) == "CLOSED"
            )
        ).one()

        tasks_week = session.exec(
            select(func.count(col(Issue.id))).where(
                col(Issue.worker_id) == worker_id,
                col(Issue.status).in_(["RESOLVED", "CLOSED"]),
                col(Issue.resolved_at) >= week_ago,
            )
        ).one()

        tasks_month = session.exec(
            select(func.count(col(Issue.id))).where(
                col(Issue.worker_id) == worker_id,
                col(Issue.status).in_(["RESOLVED", "CLOSED"]),
                col(Issue.resolved_at) >= month_ago,
            )
        ).one()

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
        resolved_issues = session.exec(
            select(Issue).where(
                col(Issue.worker_id) == worker_id,
                col(Issue.status).in_(["RESOLVED", "CLOSED"]),
                col(Issue.accepted_at) != None,
                col(Issue.resolved_at) != None,
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
    def get_workers_with_stats(
        session: Session, org_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        stmt = select(User).where(col(User.role) == "WORKER")
        if org_id:
            stmt = stmt.where(col(User.org_id) == org_id)
        workers = session.exec(stmt).all()

        result = []
        for worker in workers:
            active_count = session.exec(
                select(func.count(col(Issue.id))).where(
                    col(Issue.worker_id) == worker.id,
                    col(Issue.status).in_(["ASSIGNED", "ACCEPTED", "IN_PROGRESS"]),
                )
            ).one()

            total_assigned = session.exec(
                select(func.count(col(Issue.id))).where(col(Issue.worker_id) == worker.id)
            ).one()

            resolved_count = session.exec(
                select(func.count(col(Issue.id))).where(
                    col(Issue.worker_id) == worker.id,
                    col(Issue.status).in_(["RESOLVED", "CLOSED"]),
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

        result.sort(key=lambda w: w["active_task_count"])
        return result

    @staticmethod
    def get_dashboard_stats(
        session: Session, org_id: Optional[UUID] = None
    ) -> Dict[str, int]:
        reported_stmt = select(func.count(col(Issue.id))).where(col(Issue.status) == "REPORTED")
        in_progress_stmt = select(func.count(col(Issue.id))).where(
            col(Issue.status).in_(["ASSIGNED", "ACCEPTED", "IN_PROGRESS"])
        )
        resolved_stmt = select(func.count(col(Issue.id))).where(
            col(Issue.status).in_(["RESOLVED", "CLOSED"])
        )

        if org_id:
            reported_stmt = reported_stmt.where(col(Issue.org_id) == org_id)
            in_progress_stmt = in_progress_stmt.where(col(Issue.org_id) == org_id)
            resolved_stmt = resolved_stmt.where(col(Issue.org_id) == org_id)

        return {
            "reported": session.exec(reported_stmt).one(),
            "in_progress": session.exec(in_progress_stmt).one(),
            "resolved": session.exec(resolved_stmt).one(),
        }

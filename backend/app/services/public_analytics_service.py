import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List
from uuid import UUID

from sqlmodel import Session, asc, col, func, select

from app.models.domain import AuditLog, Category, Issue, User

logger = logging.getLogger(__name__)

class PublicAnalyticsService:
    @staticmethod
    def get_heatmap_data(session: Session) -> List[dict]:
        try:
            statement = select(Issue).where(Issue.status != "CLOSED")
            issues = session.exec(statement).all()
            data = [{"lat": i.lat, "lng": i.lng, "intensity": 0.5} for i in issues]
            logger.debug("Heatmap data generated with %s points", len(data))
            return data
        except Exception as e:
            logger.exception("Failed to generate heatmap data")
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

        trend_data = PublicAnalyticsService._get_trend_data(session)

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

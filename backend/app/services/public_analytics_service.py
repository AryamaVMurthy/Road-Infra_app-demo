import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlmodel import Session, asc, col, func, select

from app.models.domain import AuditLog, Category, Issue, User

logger = logging.getLogger(__name__)

class PublicAnalyticsService:
    @staticmethod
    def get_heatmap_data(
        session: Session, org_id: Optional[UUID] = None
    ) -> List[dict]:
        try:
            statement = select(Issue).where(Issue.status != "CLOSED")
            if org_id is not None:
                statement = statement.where(col(Issue.org_id) == org_id)
            issues = session.exec(statement).all()
            data = [{"lat": i.lat, "lng": i.lng, "intensity": 0.5} for i in issues]
            logger.debug("Heatmap data generated with %s points", len(data))
            return data
        except Exception as e:
            logger.exception("Failed to generate heatmap data")
            return []

    @staticmethod
    def get_public_issues(
        session: Session, org_id: Optional[UUID] = None
    ) -> List[dict]:
        issues_statement = select(Issue)
        if org_id is not None:
            issues_statement = issues_statement.where(col(Issue.org_id) == org_id)

        issues = session.exec(issues_statement).all()
        result = []
        for issue in issues:
            cat_name = "Unknown"
            if issue.category_id:
                cat = session.get(Category, issue.category_id)
                cat_name = cat.name if cat else "Unknown"

            result.append(
                {
                    "id": str(issue.id),
                    "lat": issue.lat,
                    "lng": issue.lng,
                    "status": issue.status,
                    "category_name": cat_name,
                    "created_at": issue.created_at.isoformat()
                    if issue.created_at
                    else None,
                }
            )
        return result

    @staticmethod
    def get_audit_trail(session: Session, entity_id: UUID) -> List[AuditLog]:
        statement = (
            select(AuditLog)
            .where(col(AuditLog.entity_id) == entity_id)
            .order_by(col(AuditLog.created_at).asc())
        )
        return list(session.exec(statement).all())

    @staticmethod
    def get_global_stats(
        session: Session, org_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        issue_count_statement = select(func.count(col(Issue.id)))
        active_workers_statement = select(func.count(col(User.id))).where(
            col(User.role) == "WORKER", col(User.status) == "ACTIVE"
        )
        resolved_statement = select(func.count(col(Issue.id))).where(
            col(Issue.status) == "CLOSED"
        )

        if org_id is not None:
            issue_count_statement = issue_count_statement.where(col(Issue.org_id) == org_id)
            active_workers_statement = active_workers_statement.where(
                col(User.org_id) == org_id
            )
            resolved_statement = resolved_statement.where(col(Issue.org_id) == org_id)

        total_reported = session.exec(issue_count_statement).one()
        active_workers = session.exec(active_workers_statement).one()
        resolved_count = session.exec(resolved_statement).one()

        categories = session.exec(select(Category)).all()
        category_split = []
        for cat in categories:
            category_statement = select(func.count(col(Issue.id))).where(
                col(Issue.category_id) == cat.id
            )
            if org_id is not None:
                category_statement = category_statement.where(col(Issue.org_id) == org_id)
            count = session.exec(category_statement).one()
            category_split.append({"name": cat.name, "value": count})

        statuses = ["REPORTED", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED"]
        status_split = []
        for s in statuses:
            status_statement = select(func.count(col(Issue.id))).where(col(Issue.status) == s)
            if org_id is not None:
                status_statement = status_statement.where(col(Issue.org_id) == org_id)
            count = session.exec(status_statement).one()
            status_split.append({"name": s, "value": count})

        total_issues_statement = select(func.count(col(Issue.id)))
        if org_id is not None:
            total_issues_statement = total_issues_statement.where(col(Issue.org_id) == org_id)
        total_issues = session.exec(total_issues_statement).one()
        if total_issues > 0:
            compliance_statement = select(func.count(col(Issue.id))).where(
                col(Issue.status).in_(["RESOLVED", "CLOSED"])
            )
            if org_id is not None:
                compliance_statement = compliance_statement.where(col(Issue.org_id) == org_id)
            compliant_issues = session.exec(compliance_statement).one()
            compliance_rate = (compliant_issues / total_issues) * 100
            compliance_str = f"{compliance_rate:.1f}%"
        else:
            compliance_str = "N/A"

        trend_data = PublicAnalyticsService._get_trend_data(session, org_id=org_id)

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
    def _get_trend_data(
        session: Session, org_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        trend = []
        today = datetime.now().date()
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        for i in range(6, -1, -1):
            target_date = today - timedelta(days=i)
            day_name = day_names[target_date.weekday()]

            reports_statement = select(func.count(col(Issue.id))).where(
                func.date(col(Issue.created_at)) == target_date
            )
            resolved_statement = select(func.count(col(Issue.id))).where(
                func.date(col(Issue.updated_at)) == target_date,
                col(Issue.status).in_(["RESOLVED", "CLOSED"]),
            )

            if org_id is not None:
                reports_statement = reports_statement.where(col(Issue.org_id) == org_id)
                resolved_statement = resolved_statement.where(col(Issue.org_id) == org_id)

            reports_count = session.exec(reports_statement).one()

            resolved_count = session.exec(resolved_statement).one()

            trend.append(
                {"name": day_name, "reports": reports_count, "resolved": resolved_count}
            )

        return trend

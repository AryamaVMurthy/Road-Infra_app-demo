from sqlmodel import Session, select, func, col, asc, desc
from app.models.domain import Issue, AuditLog, Category, User
from typing import List, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta


class AnalyticsService:
    @staticmethod
    def get_heatmap_data(session: Session) -> List[dict]:
        try:
            statement = select(Issue).where(Issue.status != "CLOSED")
            issues = session.exec(statement).all()
            data = [{"lat": i.lat, "lng": i.lng, "intensity": 0.5} for i in issues]
            print(f"Heatmap data generated: {len(data)} points")
            return data
        except Exception as e:
            print(f"Error in get_heatmap_data: {e}")
            return []

    @staticmethod
    def get_audit_trail(session: Session, entity_id: UUID) -> List[AuditLog]:
        statement = (
            select(AuditLog)
            .where(AuditLog.entity_id == entity_id)
            .order_by(asc(AuditLog.created_at))
        )
        return session.exec(statement).all()

    @staticmethod
    def get_all_audits(session: Session, limit: int = 100) -> List[AuditLog]:
        statement = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit)
        return session.exec(statement).all()

    @staticmethod
    def get_global_stats(session: Session) -> Dict[str, Any]:
        total_reported = session.exec(select(func.count(Issue.id))).one()
        active_workers = session.exec(
            select(func.count(User.id)).where(
                User.role == "WORKER", User.status == "ACTIVE"
            )
        ).one()
        resolved_count = session.exec(
            select(func.count(Issue.id)).where(Issue.status == "CLOSED")
        ).one()

        categories = session.exec(select(Category)).all()
        category_split = []
        for cat in categories:
            count = session.exec(
                select(func.count(Issue.id)).where(Issue.category_id == cat.id)
            ).one()
            category_split.append({"name": cat.name, "value": count})

        statuses = ["REPORTED", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED"]
        status_split = []
        for s in statuses:
            count = session.exec(
                select(func.count(Issue.id)).where(Issue.status == s)
            ).one()
            status_split.append({"name": s, "value": count})

        total_issues = session.exec(select(func.count(Issue.id))).one()
        if total_issues > 0:
            compliant_issues = session.exec(
                select(func.count(Issue.id)).where(
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
        """Get actual trend data for last 7 days from database."""
        trend = []
        today = datetime.now().date()
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        for i in range(6, -1, -1):
            target_date = today - timedelta(days=i)
            day_name = day_names[target_date.weekday()]

            reports_count = session.exec(
                select(func.count(Issue.id)).where(
                    func.date(Issue.created_at) == target_date
                )
            ).one()

            resolved_count = session.exec(
                select(func.count(Issue.id)).where(
                    func.date(Issue.updated_at) == target_date,
                    col(Issue.status).in_(["RESOLVED", "CLOSED"]),
                )
            ).one()

            trend.append(
                {"name": day_name, "reports": reports_count, "resolved": resolved_count}
            )

        return trend

    @staticmethod
    def run_diagnostics(session: Session) -> Dict[str, Any]:
        results = []
        # 1. Database & PostGIS Check
        try:
            session.exec(select(func.ST_AsText(func.ST_Point(0, 0)))).one()
            results.append({"name": "PostGIS Engine", "status": "HEALTHY", "message": "Operational"})
        except Exception as e:
            results.append({"name": "PostGIS Engine", "status": "ERROR", "message": str(e)})

        # 2. MinIO Check
        from app.services.minio_client import minio_client
        try:
            minio_client.list_buckets()
            results.append({"name": "MinIO Storage", "status": "HEALTHY", "message": "Reachable"})
        except Exception:
            results.append({"name": "MinIO Storage", "status": "ERROR", "message": "Auth/Conn Failed"})

        return {"timestamp": datetime.utcnow().isoformat(), "results": results}

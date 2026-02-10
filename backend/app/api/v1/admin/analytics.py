"""
Admin Analytics Routes
Endpoints for analytics and statistics
"""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.api.deps import require_admin_user
from app.models.domain import User
from app.services.admin_analytics_service import AdminAnalyticsService

router = APIRouter()


@router.get("/worker-analytics")
def get_worker_analytics(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin_user),
):
    """Get detailed worker analytics for dashboard"""
    org_scope = None if current_user.role == "SYSADMIN" else current_user.org_id
    return AdminAnalyticsService.get_worker_analytics(session, org_id=org_scope)


@router.get("/dashboard-stats")
def get_dashboard_stats(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin_user),
):
    """Get quick dashboard statistics"""
    return AdminAnalyticsService.get_dashboard_stats(session)

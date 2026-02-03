"""
Admin Analytics Routes
Endpoints for analytics and statistics
"""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.api.deps import get_current_user
from app.models.domain import User
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/worker-analytics")
def get_worker_analytics(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get detailed worker analytics for dashboard"""
    return AnalyticsService.get_worker_analytics(session)


@router.get("/dashboard-stats")
def get_dashboard_stats(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get quick dashboard statistics"""
    return AnalyticsService.get_dashboard_stats(session)

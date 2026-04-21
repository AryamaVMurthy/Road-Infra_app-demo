"""
Admin Analytics Routes
Endpoints for analytics and statistics
"""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.api.deps import require_admin_user
from app.models.domain import User
from app.schemas.admin import DashboardStatsResponse, WorkerAnalyticsResponse
from app.schemas.analytics import GlobalStatsResponse, HeatmapPoint, PublicIssueMapItem
from app.services.admin_analytics_service import AdminAnalyticsService

router = APIRouter()


@router.get(
    "/worker-analytics",
    response_model=WorkerAnalyticsResponse,
    summary="Get worker analytics",
    description="Return workload, throughput, and performance metrics for workers visible to the current administrator.",
)
def get_worker_analytics(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin_user),
):
    """Get detailed worker analytics for dashboard"""
    org_id = None if current_user.role == "SYSADMIN" else current_user.org_id
    return AdminAnalyticsService.get_worker_analytics(session, org_id=org_id)


@router.get(
    "/dashboard-stats",
    response_model=DashboardStatsResponse,
    summary="Get dashboard issue counts",
    description="Return headline counts for reported, in-progress, and resolved issues in the current administrative scope.",
)
def get_dashboard_stats(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin_user),
):
    """Get quick dashboard statistics"""
    org_id = None if current_user.role == "SYSADMIN" else current_user.org_id
    return AdminAnalyticsService.get_dashboard_stats(session, org_id=org_id)


@router.get(
    "/heatmap",
    response_model=list[HeatmapPoint],
    summary="Get scoped issue heatmap data",
    description="Return issue heatmap points scoped to the current admin's authority, or global points for sysadmin.",
)
def get_scoped_heatmap(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin_user),
):
    org_id = None if current_user.role == "SYSADMIN" else current_user.org_id
    return AdminAnalyticsService.get_heatmap_data(session, org_id=org_id)


@router.get(
    "/issues-map",
    response_model=list[PublicIssueMapItem],
    summary="Get scoped issue marker data",
    description="Return map issue records scoped to the current admin's authority, or global issue records for sysadmin.",
)
def get_scoped_map_issues(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin_user),
):
    org_id = None if current_user.role == "SYSADMIN" else current_user.org_id
    return AdminAnalyticsService.get_map_issues(session, org_id=org_id)


@router.get(
    "/stats",
    response_model=GlobalStatsResponse,
    summary="Get scoped analytics stats",
    description="Return analytics summary, category/status split, and trend data scoped to the current admin's authority, or global analytics for sysadmin.",
)
def get_scoped_stats(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin_user),
):
    org_id = None if current_user.role == "SYSADMIN" else current_user.org_id
    return AdminAnalyticsService.get_global_stats(session, org_id=org_id)

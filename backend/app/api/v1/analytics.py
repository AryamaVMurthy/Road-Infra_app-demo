from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, col

from app.db.session import get_session
from app.api.deps import require_admin_user
from app.models.domain import User, AuditLog
from app.schemas.analytics import (
    GlobalStatsResponse,
    HeatmapPoint,
    PublicIssueMapItem,
)
from app.services.public_analytics_service import PublicAnalyticsService

router = APIRouter()

@router.get(
    "/heatmap",
    response_model=List[HeatmapPoint],
    summary="Get public issue heatmap data",
    description="Return geospatial heatmap points for all non-closed issues for use in public and admin map views.",
)
def get_heatmap(
    session: Session = Depends(get_session),
):
    """Public endpoint - returns heatmap data for all issues"""
    return PublicAnalyticsService.get_heatmap_data(session)

@router.get(
    "/stats",
    response_model=GlobalStatsResponse,
    summary="Get public aggregate analytics",
    description="Return dashboard summary metrics, breakdown charts, and seven-day trend data for the public analytics view.",
)
def get_global_stats(
    session: Session = Depends(get_session),
):
    """Public endpoint - returns aggregate statistics"""
    return PublicAnalyticsService.get_global_stats(session)

@router.get(
    "/issues-public",
    response_model=List[PublicIssueMapItem],
    summary="Get public map issues",
    description="Return simplified public issue records for map rendering without exposing internal assignment details.",
)
def get_public_issues(
    session: Session = Depends(get_session),
):
    """Public endpoint - returns all issues for map display"""
    return PublicAnalyticsService.get_public_issues(session)

@router.get(
    "/audit/{entity_id}",
    response_model=List[AuditLog],
    summary="Get audit trail for one entity",
    description="Return chronological audit log entries for a single entity such as an issue or user.",
)
def get_entity_audit(entity_id: UUID, session: Session = Depends(get_session)):
    # Anyone can see the audit trail for an issue they have access to
    return PublicAnalyticsService.get_audit_trail(session, entity_id)

@router.get(
    "/audit-all",
    response_model=List[AuditLog],
    summary="Query the full audit log",
    description="Return a filtered slice of audit events for administrators, with pagination and date-range filters.",
)
def get_all_audit_logs(
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    action: Optional[str] = Query(default=None),
    actor_id: Optional[UUID] = Query(default=None),
    entity_id: Optional[UUID] = Query(default=None),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin_user),
):
    statement = select(AuditLog)

    if action:
        statement = statement.where(AuditLog.action == action)
    if actor_id:
        statement = statement.where(AuditLog.actor_id == actor_id)
    if entity_id:
        statement = statement.where(AuditLog.entity_id == entity_id)
    if start_date:
        statement = statement.where(AuditLog.created_at >= start_date)
    if end_date:
        statement = statement.where(AuditLog.created_at <= end_date)

    statement = (
        statement.order_by(col(AuditLog.created_at).desc()).offset(offset).limit(limit)
    )
    return session.exec(statement).all()

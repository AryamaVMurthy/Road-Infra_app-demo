from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.db.session import get_session
from app.api.deps import get_current_user
from app.models.domain import User, AuditLog, Issue
from app.services.analytics import AnalyticsService
from typing import List, Optional
from uuid import UUID

router = APIRouter()


@router.get("/heatmap")
def get_heatmap(
    session: Session = Depends(get_session),
):
    """Public endpoint - returns heatmap data for all issues"""
    return AnalyticsService.get_heatmap_data(session)


@router.get("/stats")
def get_global_stats(
    session: Session = Depends(get_session),
):
    """Public endpoint - returns aggregate statistics"""
    return AnalyticsService.get_global_stats(session)


@router.get("/issues-public")
def get_public_issues(
    session: Session = Depends(get_session),
):
    """Public endpoint - returns all issues for map display"""
    from app.models.domain import Category

    issues = session.exec(select(Issue)).all()
    result = []
    for issue in issues:
        cat_name = "Unknown"
        if issue.category_id:
            cat = session.get(Category, issue.category_id)
            cat_name = cat.name if cat else "Unknown"

        result.append(
            {
                "id": str(issue.id),
                "lat": issue.lat,  # Use the property which handles to_shape
                "lng": issue.lng,  # Use the property which handles to_shape
                "status": issue.status,
                "category_name": cat_name,
                "created_at": issue.created_at.isoformat()
                if issue.created_at
                else None,
            }
        )
    return result


@router.get("/audit/{entity_id}", response_model=List[AuditLog])
def get_entity_audit(entity_id: UUID, session: Session = Depends(get_session)):
    # Anyone can see the audit trail for an issue they have access to
    return AnalyticsService.get_audit_trail(session, entity_id)


@router.get("/audit-all", response_model=List[AuditLog])
def get_all_audits(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Admin endpoint - returns all system audits"""
    if current_user.role != "SYSADMIN":
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Only SysAdmins can see global audits")
    return AnalyticsService.get_all_audits(session)

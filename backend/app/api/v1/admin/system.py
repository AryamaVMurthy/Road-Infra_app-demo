from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.api.deps import require_roles
from app.db.session import get_session
from app.models.domain import Category, User
from app.schemas.system_admin import (
    AuthorityCreateRequest,
    AuthorityRead,
    AuthorityUpdateRequest,
    IssueTypeCreateRequest,
    IssueTypeUpdateRequest,
    ManualIssueCreateRequest,
    ManualIssueCreateResponse,
)
from app.services.system_admin_service import SystemAdminService

router = APIRouter()
require_sysadmin_user = require_roles("SYSADMIN")


@router.get("/authorities", response_model=List[AuthorityRead])
def list_authorities(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    return SystemAdminService.list_authorities(session)


@router.post("/authorities", response_model=AuthorityRead)
def create_authority(
    data: AuthorityCreateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    organization = SystemAdminService.create_authority(
        session,
        name=data.name,
        admin_email=str(data.admin_email),
        jurisdiction_points=data.jurisdiction_points,
        actor_id=current_user.id,
        zone_name=data.zone_name,
    )
    session.commit()

    return next(
        auth
        for auth in SystemAdminService.list_authorities(session)
        if auth["org_id"] == organization.id
    )


@router.put("/authorities/{org_id}", response_model=AuthorityRead)
def update_authority(
    org_id: UUID,
    data: AuthorityUpdateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    organization = SystemAdminService.update_authority(
        session,
        org_id=org_id,
        actor_id=current_user.id,
        name=data.name,
        jurisdiction_points=data.jurisdiction_points,
        zone_name=data.zone_name,
    )
    session.commit()
    return next(
        auth
        for auth in SystemAdminService.list_authorities(session)
        if auth["org_id"] == organization.id
    )


@router.delete("/authorities/{org_id}")
def delete_authority(
    org_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    SystemAdminService.delete_authority(
        session, org_id=org_id, actor_id=current_user.id
    )
    session.commit()
    return {"message": "Authority deleted"}


@router.get("/issue-types", response_model=List[Category])
def list_issue_types(
    include_inactive: bool = Query(default=True),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    statement = select(Category)
    if not include_inactive:
        statement = statement.where(Category.is_active == True)
    return session.exec(statement).all()


@router.post("/issue-types", response_model=Category)
def create_issue_type(
    data: IssueTypeCreateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    category = SystemAdminService.create_issue_type(
        session,
        name=data.name,
        expected_sla_days=data.expected_sla_days,
        actor_id=current_user.id,
    )
    session.commit()
    session.refresh(category)
    return category


@router.put("/issue-types/{category_id}", response_model=Category)
def update_issue_type(
    category_id: UUID,
    data: IssueTypeUpdateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    category = SystemAdminService.update_issue_type(
        session,
        category_id=category_id,
        actor_id=current_user.id,
        name=data.name,
        expected_sla_days=data.expected_sla_days,
        is_active=data.is_active,
    )
    session.commit()
    session.refresh(category)
    return category


@router.delete("/issue-types/{category_id}", response_model=Category)
def delete_issue_type(
    category_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    category = SystemAdminService.deactivate_issue_type(
        session,
        category_id=category_id,
        actor_id=current_user.id,
    )
    session.commit()
    session.refresh(category)
    return category


@router.post("/manual-issues", response_model=ManualIssueCreateResponse)
def create_manual_issue(
    data: ManualIssueCreateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    issue = SystemAdminService.create_manual_issue(
        session,
        actor=current_user,
        category_id=data.category_id,
        lat=data.lat,
        lng=data.lng,
        address=data.address,
        org_id=data.org_id,
    )
    session.commit()
    session.refresh(issue)
    return ManualIssueCreateResponse(
        issue_id=issue.id,
        message="Manual issue created",
        created_at=issue.created_at,
    )

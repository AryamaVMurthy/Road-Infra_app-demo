from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.db.session import get_session
from app.api.deps import require_sysadmin_user
from app.models.domain import User, Organization, Zone, Category
from app.schemas.sysadmin import (
    ZoneCreate,
    ZoneRead,
    OrganizationCreate,
    OrganizationRead,
    CategoryCreate,
    CategoryUpdate,
    CategoryRead,
)
from app.services.audit import AuditService
from shapely.geometry import shape
import json

router = APIRouter()


@router.get("/zones", response_model=List[ZoneRead])
def get_zones(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    """Retrieve all zones."""
    return session.exec(select(Zone)).all()


@router.post("/zones", response_model=ZoneRead)
def create_zone(
    data: ZoneCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    """Create a new zone with a boundary polygon."""
    geom = shape(data.boundary_geojson)
    zone = Zone(name=data.name, boundary=geom.wkt)
    session.add(zone)
    session.commit()
    session.refresh(zone)
    return zone


@router.get("/organizations", response_model=List[OrganizationRead])
def get_organizations(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    """Retrieve all organizations/authorities."""
    orgs = session.exec(select(Organization)).all()
    result = []
    for org in orgs:
        result.append(
            OrganizationRead(
                id=org.id,
                name=org.name,
                zone_id=org.zone_id,
                zone_name=org.zone.name if org.zone else None,
            )
        )
    return result


@router.post("/organizations", response_model=OrganizationRead)
def create_organization(
    data: OrganizationCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    """Create a new organization and link it to a zone."""
    org = Organization(name=data.name, zone_id=data.zone_id)
    session.add(org)
    session.commit()
    session.refresh(org)
    return OrganizationRead(
        id=org.id,
        name=org.name,
        zone_id=org.zone_id,
        zone_name=org.zone.name if org.zone else None,
    )


@router.get("/categories", response_model=List[CategoryRead])
def get_all_categories(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    """Retrieve all issue categories."""
    return session.exec(select(Category)).all()


@router.post("/categories", response_model=CategoryRead)
def create_category(
    data: CategoryCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    """Create a new issue category."""
    cat = Category(**data.model_dump())
    session.add(cat)
    session.commit()
    session.refresh(cat)
    return cat


@router.put("/categories/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: UUID,
    data: CategoryUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    """Update an existing issue category."""
    cat = session.get(Category, category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(cat, key, value)

    session.add(cat)
    session.commit()
    session.refresh(cat)
    return cat


@router.delete("/categories/{category_id}")
def delete_category(
    category_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    """Deactivate an issue category."""
    cat = session.get(Category, category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    cat.is_active = False
    session.add(cat)
    session.commit()
    return {"message": "Category deactivated"}

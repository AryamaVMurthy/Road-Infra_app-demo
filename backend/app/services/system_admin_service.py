from __future__ import annotations

from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException
from geoalchemy2.shape import to_shape
from shapely.geometry import Polygon
from sqlmodel import Session, col, select, func

from app.models.domain import Category, Issue, Organization, User, Zone
from app.services.audit import AuditService

LngLat = Tuple[float, float]


class SystemAdminService:
    @staticmethod
    def _polygon_wkt(points: List[LngLat]) -> str:
        if len(points) < 3:
            raise HTTPException(
                status_code=400,
                detail="Jurisdiction polygon requires at least 3 points",
            )

        polygon = Polygon(points)
        if not polygon.is_valid:
            raise HTTPException(status_code=400, detail="Invalid jurisdiction polygon")

        return f"SRID=4326;{polygon.wkt}"

    @staticmethod
    def list_authorities(session: Session) -> List[dict]:
        authorities = session.exec(select(Organization)).all()
        result: List[dict] = []
        for authority in authorities:
            zone = session.get(Zone, authority.zone_id)
            admin_count = session.exec(
                select(func.count())
                .select_from(User)
                .where(
                    col(User.org_id) == authority.id,
                    col(User.role) == "ADMIN",
                )
            ).one()
            worker_count = session.exec(
                select(func.count())
                .select_from(User)
                .where(
                    col(User.org_id) == authority.id,
                    col(User.role) == "WORKER",
                )
            ).one()
            jurisdiction_wkt = (
                to_shape(zone.boundary).wkt
                if zone and zone.boundary is not None
                else None
            )
            jurisdiction_points = []
            if zone and zone.boundary is not None:
                shape = to_shape(zone.boundary)
                if isinstance(shape, Polygon):
                    jurisdiction_points = list(shape.exterior.coords)

            result.append(
                {
                    "org_id": authority.id,
                    "name": authority.name,
                    "zone_id": authority.zone_id,
                    "zone_name": zone.name if zone else "Unknown",
                    "admin_count": admin_count,
                    "worker_count": worker_count,
                    "jurisdiction_wkt": jurisdiction_wkt,
                    "jurisdiction_points": jurisdiction_points,
                }
            )
        return result

    @staticmethod
    def create_authority(
        session: Session,
        name: str,
        admin_email: str,
        jurisdiction_points: List[LngLat],
        actor_id: UUID,
        zone_name: Optional[str] = None,
    ) -> Organization:
        existing_admin = session.exec(
            select(User).where(User.email == admin_email)
        ).first()
        if existing_admin and existing_admin.role != "ADMIN":
            raise HTTPException(
                status_code=400,
                detail="Admin email already exists with a non-admin role",
            )

        boundary_wkt = SystemAdminService._polygon_wkt(jurisdiction_points)
        zone = Zone(name=zone_name or f"{name} Zone", boundary=boundary_wkt)
        session.add(zone)
        session.flush()

        organization = Organization(name=name, zone_id=zone.id)
        session.add(organization)
        session.flush()

        if existing_admin:
            existing_admin.org_id = organization.id
            existing_admin.status = "ACTIVE"
            session.add(existing_admin)
        else:
            session.add(
                User(
                    email=admin_email,
                    role="ADMIN",
                    org_id=organization.id,
                    status="ACTIVE",
                )
            )

        AuditService.log(
            session,
            "CREATE_AUTHORITY",
            "ORGANIZATION",
            organization.id,
            actor_id,
            None,
            name,
        )

        return organization

    @staticmethod
    def update_authority(
        session: Session,
        org_id: UUID,
        actor_id: UUID,
        name: Optional[str] = None,
        jurisdiction_points: Optional[List[LngLat]] = None,
        zone_name: Optional[str] = None,
    ) -> Organization:
        organization = session.get(Organization, org_id)
        if not organization:
            raise HTTPException(status_code=404, detail="Authority not found")

        old_value = organization.name
        if name:
            organization.name = name

        zone = session.get(Zone, organization.zone_id)
        if not zone:
            raise HTTPException(status_code=500, detail="Authority zone missing")

        if zone_name:
            zone.name = zone_name
            session.add(zone)

        if jurisdiction_points is not None:
            zone.boundary = SystemAdminService._polygon_wkt(jurisdiction_points)
            session.add(zone)

        session.add(organization)
        AuditService.log(
            session,
            "UPDATE_AUTHORITY",
            "ORGANIZATION",
            organization.id,
            actor_id,
            old_value,
            organization.name,
        )
        return organization

    @staticmethod
    def delete_authority(session: Session, org_id: UUID, actor_id: UUID) -> None:
        organization = session.get(Organization, org_id)
        if not organization:
            raise HTTPException(status_code=404, detail="Authority not found")

        users = session.exec(select(User).where(User.org_id == org_id)).all()
        if users:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete authority with linked users",
            )

        zone = session.get(Zone, organization.zone_id)

        AuditService.log(
            session,
            "DELETE_AUTHORITY",
            "ORGANIZATION",
            organization.id,
            actor_id,
            organization.name,
            None,
        )

        session.delete(organization)
        if zone:
            session.delete(zone)

    @staticmethod
    def create_issue_type(
        session: Session,
        name: str,
        default_priority: str,
        expected_sla_days: int,
        actor_id: UUID,
    ) -> Category:
        existing = session.exec(
            select(Category).where(func.lower(Category.name) == name.strip().lower())
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Issue type already exists")

        category = Category(
            name=name.strip(),
            default_priority=default_priority,
            expected_sla_days=expected_sla_days,
            is_active=True,
        )
        session.add(category)
        session.flush()

        AuditService.log(
            session,
            "CREATE_ISSUE_TYPE",
            "CATEGORY",
            category.id,
            actor_id,
            None,
            category.name,
        )
        return category

    @staticmethod
    def update_issue_type(
        session: Session,
        category_id: UUID,
        actor_id: UUID,
        name: Optional[str] = None,
        default_priority: Optional[str] = None,
        expected_sla_days: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> Category:
        category = session.get(Category, category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Issue type not found")

        old_name = category.name
        if name is not None:
            category.name = name.strip()
        if default_priority is not None:
            category.default_priority = default_priority
        if expected_sla_days is not None:
            category.expected_sla_days = expected_sla_days
        if is_active is not None:
            category.is_active = is_active

        session.add(category)
        AuditService.log(
            session,
            "UPDATE_ISSUE_TYPE",
            "CATEGORY",
            category.id,
            actor_id,
            old_name,
            category.name,
        )
        return category

    @staticmethod
    def deactivate_issue_type(
        session: Session,
        category_id: UUID,
        actor_id: UUID,
    ) -> Category:
        category = session.get(Category, category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Issue type not found")

        category.is_active = False
        session.add(category)
        AuditService.log(
            session,
            "DEACTIVATE_ISSUE_TYPE",
            "CATEGORY",
            category.id,
            actor_id,
            category.name,
            f"{category.name} (inactive)",
        )
        return category

    @staticmethod
    def create_manual_issue(
        session: Session,
        actor: User,
        category_id: UUID,
        lat: float,
        lng: float,
        address: Optional[str],
        priority: Optional[str],
        org_id: Optional[UUID],
    ) -> Issue:
        category = session.get(Category, category_id)
        if not category or not category.is_active:
            raise HTTPException(status_code=400, detail="Invalid issue type")

        issue = Issue(
            category_id=category_id,
            status="REPORTED",
            location=f"SRID=4326;POINT({lng} {lat})",
            address=address,
            reporter_id=actor.id,
            org_id=org_id,
            priority=priority or category.default_priority,
            report_count=1,
        )
        session.add(issue)
        session.flush()

        AuditService.log(
            session,
            "MANUAL_ISSUE_CREATE",
            "ISSUE",
            issue.id,
            actor.id,
            None,
            issue.status,
        )
        return issue

from datetime import datetime
from typing import Optional, List, Any
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Relationship, Column
from geoalchemy2 import Geometry
from shapely.wkt import loads


class UserBase(SQLModel):
    email: str = Field(unique=True, index=True)
    full_name: Optional[str] = None
    role: str  # CITIZEN, ADMIN, WORKER, SYSADMIN
    org_id: Optional[UUID] = Field(default=None, foreign_key="organization.id")
    status: str = "ACTIVE"
    last_login_at: Optional[datetime] = None


class User(UserBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    hashed_password: Optional[str] = None

    organization: Optional["Organization"] = Relationship(back_populates="users")
    reported_issues: List["Issue"] = Relationship(
        back_populates="reporter",
        sa_relationship_kwargs={"foreign_keys": "[Issue.reporter_id]"},
    )
    assigned_tasks: List["Issue"] = Relationship(
        back_populates="worker",
        sa_relationship_kwargs={"foreign_keys": "[Issue.worker_id]"},
    )


class OrganizationBase(SQLModel):
    name: str
    zone_id: UUID = Field(foreign_key="zone.id")


class Organization(OrganizationBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    zone: "Zone" = Relationship(back_populates="organizations")
    users: List[User] = Relationship(back_populates="organization")
    issues: List["Issue"] = Relationship(back_populates="organization")


class ZoneBase(SQLModel):
    name: str
    boundary: Any = Field(
        sa_column=Column(Geometry(geometry_type="POLYGON", srid=4326))
    )


class Zone(ZoneBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    organizations: List[Organization] = Relationship(back_populates="zone")


class CategoryBase(SQLModel):
    name: str
    default_priority: str = "P3"
    expected_sla_days: int = 7
    is_active: bool = True


class Category(CategoryBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    issues: List["Issue"] = Relationship(back_populates="category")


class IssueBase(SQLModel):
    category_id: UUID = Field(foreign_key="category.id")
    status: str = "REPORTED"
    # PostGIS point: SRID 4326 (WGS84)
    location: Any = Field(sa_column=Column(Geometry(geometry_type="POINT", srid=4326)))
    address: Optional[str] = None
    reporter_id: UUID = Field(foreign_key="user.id")
    worker_id: Optional[UUID] = Field(default=None, foreign_key="user.id")
    org_id: Optional[UUID] = Field(default=None, foreign_key="organization.id")
    priority: Optional[str] = "P3"
    report_count: int = 1
    rejection_reason: Optional[str] = None
    eta_duration: Optional[str] = None
    accepted_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


from geoalchemy2.shape import to_shape


class Issue(IssueBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def location_wkt(self) -> str:
        if self.location is None:
            return ""
        return to_shape(self.location).wkt

    @property
    def lat(self) -> float:
        if self.location is None:
            return 0.0
        return to_shape(self.location).y

    @property
    def lng(self) -> float:
        if self.location is None:
            return 0.0
        return to_shape(self.location).x

    @property
    def worker_name(self) -> Optional[str]:
        return self.worker.full_name if self.worker else None

    @property
    def category_name(self) -> str:
        return self.category.name if self.category else "Uncategorized"

    category: Category = Relationship(back_populates="issues")
    reporter: User = Relationship(
        back_populates="reported_issues",
        sa_relationship_kwargs={"foreign_keys": "[Issue.reporter_id]"},
    )
    worker: Optional[User] = Relationship(
        back_populates="assigned_tasks",
        sa_relationship_kwargs={"foreign_keys": "[Issue.worker_id]"},
    )
    organization: Optional[Organization] = Relationship(back_populates="issues")
    evidence: List["Evidence"] = Relationship(back_populates="issue")


class EvidenceBase(SQLModel):
    issue_id: UUID = Field(foreign_key="issue.id")
    type: str  # REPORT, RESOLVE
    file_path: str
    reporter_id: Optional[UUID] = Field(default=None, foreign_key="user.id")
    exif_timestamp: Optional[datetime] = None
    exif_lat: Optional[float] = None
    exif_lng: Optional[float] = None


class Evidence(EvidenceBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    issue: Issue = Relationship(back_populates="evidence")


class InviteBase(SQLModel):
    email: str
    org_id: UUID = Field(foreign_key="organization.id")
    status: str = "INVITED"
    expires_at: datetime


class Invite(InviteBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FeedbackBase(SQLModel):
    issue_id: UUID = Field(foreign_key="issue.id")
    user_id: UUID = Field(foreign_key="user.id")
    vote: int  # 1 or -1


class Feedback(FeedbackBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Otp(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True)
    code: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AuditLog(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    action: str  # e.g., STATUS_CHANGE, ASSIGNMENT, PRIORITY_CHANGE
    entity_type: str  # e.g., ISSUE, USER, CATEGORY
    entity_id: UUID
    actor_id: UUID
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

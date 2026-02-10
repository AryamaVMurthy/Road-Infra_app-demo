from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from uuid import UUID
from datetime import datetime


class BulkAssignRequest(BaseModel):
    issue_ids: List[UUID]
    worker_id: UUID


class BulkInviteRequest(BaseModel):
    emails: List[str]


class WorkerWithStats(BaseModel):
    """Worker info with task statistics for assignment dropdown"""

    id: UUID
    email: str
    full_name: Optional[str] = None
    status: str
    active_task_count: int = 0  # ASSIGNED, ACCEPTED, IN_PROGRESS
    total_assigned: int = 0  # All tasks ever assigned
    resolved_count: int = 0  # RESOLVED or CLOSED

    model_config = ConfigDict(from_attributes=True)


class WorkerPerformance(BaseModel):
    """Detailed worker performance analytics"""

    worker_id: UUID
    worker_name: str
    email: str

    # Current workload
    active_tasks: int = 0
    pending_acceptance: int = 0  # ASSIGNED status
    in_progress: int = 0  # ACCEPTED or IN_PROGRESS

    # Historical metrics
    total_resolved: int = 0
    total_closed: int = 0

    # Performance
    avg_resolution_hours: Optional[float] = None
    tasks_this_week: int = 0
    tasks_this_month: int = 0

    model_config = ConfigDict(from_attributes=True)


class WorkerAnalyticsResponse(BaseModel):
    """Full worker analytics for dashboard"""

    workers: List[WorkerPerformance]
    summary: dict  # totals, averages


class WorkerBulkRegisterRequest(BaseModel):
    emails_csv: str


class WorkerBulkRegisterResult(BaseModel):
    created: List[str]
    reactivated: List[str]
    skipped: List[str]

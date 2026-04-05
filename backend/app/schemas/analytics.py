from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class HeatmapPoint(BaseModel):
    lat: float
    lng: float
    intensity: float


class AnalyticsBreakdownItem(BaseModel):
    name: str
    value: int


class TrendPoint(BaseModel):
    name: str
    reports: int
    resolved: int


class GlobalStatsSummary(BaseModel):
    reported: int
    workers: int
    resolved: int
    compliance: str


class GlobalStatsResponse(BaseModel):
    summary: GlobalStatsSummary
    category_split: List[AnalyticsBreakdownItem]
    status_split: List[AnalyticsBreakdownItem]
    trend: List[TrendPoint]


class PublicIssueMapItem(BaseModel):
    id: UUID
    lat: float
    lng: float
    status: str
    category_name: str
    created_at: Optional[datetime] = None

from pydantic import BaseModel, ConfigDict
from uuid import UUID
from typing import Optional, List, Any
from datetime import datetime


class ZoneCreate(BaseModel):
    name: str
    boundary_geojson: dict  # GeoJSON Polygon


class ZoneRead(BaseModel):
    id: UUID
    name: str
    boundary_wkt: str
    boundary_geojson: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class OrganizationCreate(BaseModel):
    name: str
    zone_id: UUID


class OrganizationRead(BaseModel):
    id: UUID
    name: str
    zone_id: UUID
    zone_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CategoryCreate(BaseModel):
    name: str


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


class CategoryRead(BaseModel):
    id: UUID
    name: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

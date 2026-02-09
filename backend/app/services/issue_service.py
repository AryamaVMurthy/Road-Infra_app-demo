"""Issue service helpers for reporting flow and evidence."""

from __future__ import annotations

import io
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Session, select, func

from app.core.config import settings
from app.models.domain import Evidence, Issue
from app.services.exif import ExifService
from app.services.minio_client import minio_client


class IssueService:
    """Service for issue reporting and evidence creation."""

    @staticmethod
    def build_point_wkt(lat: float, lng: float) -> str:
        return f"SRID=4326;POINT({lng} {lat})"

    @staticmethod
    def find_duplicate_issue(session: Session, point_wkt: str) -> Optional[Issue]:
        statement = select(Issue).where(
            Issue.status != "CLOSED",
            func.ST_DWithin(
                Issue.location, func.ST_GeomFromText(point_wkt), 5.0 / 111320.0
            ),
        )
        return session.exec(statement).first()

    @staticmethod
    def extract_exif(photo_content: bytes) -> dict:
        return ExifService.extract_metadata(photo_content)

    @staticmethod
    def store_issue_photo(photo_content: bytes, prefix: str = "issues") -> str:
        file_id = str(uuid4())
        file_path = f"{prefix}/{file_id}.jpg"
        minio_client.put_object(
            settings.MINIO_BUCKET,
            file_path,
            io.BytesIO(photo_content),
            len(photo_content),
            content_type="image/jpeg",
        )
        return file_path

    @staticmethod
    def build_evidence(
        issue_id: UUID,
        reporter_id: UUID,
        file_path: str,
        exif_data: dict,
        evidence_type: str = "REPORT",
    ) -> Evidence:
        return Evidence(
            issue_id=issue_id,
            type=evidence_type,
            file_path=file_path,
            reporter_id=reporter_id,
            exif_timestamp=exif_data.get("timestamp"),
            exif_lat=exif_data.get("lat"),
            exif_lng=exif_data.get("lng"),
        )

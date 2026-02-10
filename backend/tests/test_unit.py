import pytest
from datetime import datetime, timedelta
from app.core.time import utc_now
from app.services.exif import ExifService
from app.services.audit import AuditService
from app.models.domain import AuditLog
from uuid import uuid4
from sqlmodel import select


def test_audit_log_creation(session):
    actor_id = uuid4()
    entity_id = uuid4()

    AuditService.log(
        session=session,
        action="TEST_ACTION",
        entity_type="ISSUE",
        entity_id=entity_id,
        actor_id=actor_id,
        old_value="A",
        new_value="B",
    )

    # Query back
    log = session.exec(select(AuditLog)).first()
    assert log is not None
    assert log.action == "TEST_ACTION"
    assert log.actor_id == actor_id
    assert log.old_value == "A"
    assert log.new_value == "B"


def test_exif_proximity_edge_cases():
    # Coordinates roughly 17.4N, 78.4E
    # 1 degree lat is ~111km. 1m is ~0.000009 degrees.
    lat1, lng1 = 17.444700, 78.348300

    # 4.5m away (Should pass)
    lat2, lng2 = 17.444700 + (4.5 / 111320.0), 78.348300
    assert (
        ExifService.validate_proximity(lat1, lng1, lat2, lng2, threshold_m=5.0) is True
    )

    # 5.5m away (Should fail)
    lat3, lng3 = 17.444700 + (5.5 / 111320.0), 78.348300
    assert (
        ExifService.validate_proximity(lat1, lng1, lat3, lng3, threshold_m=5.0) is False
    )


def test_exif_metadata_missing_tags():
    # Test with empty or corrupt bytes (should handle gracefully)
    metadata = ExifService.extract_metadata(b"not-an-image")
    assert metadata["lat"] is None
    assert metadata["lng"] is None
    assert isinstance(metadata["timestamp"], datetime)


def test_exif_timestamp_boundary():
    now = utc_now()

    # 6 days, 23 hours (Pass)
    recent = now - timedelta(days=6, hours=23)
    assert ExifService.validate_timestamp(recent, threshold_days=7) is True

    # 7 days, 1 hour (Fail)
    old = now - timedelta(days=7, hours=1)
    assert ExifService.validate_timestamp(old, threshold_days=7) is False

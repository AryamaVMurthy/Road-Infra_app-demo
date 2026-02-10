"""
Media & Evidence Tests

Tests media retrieval endpoints, evidence creation through report/resolve flows,
and EXIF metadata extraction service.

Covers:
  1. ExifService unit tests (metadata extraction, proximity, timestamp validation)
  2. Evidence record creation during report and resolve
  3. GET /api/v1/media/{issue_id}/{type} endpoint
  4. Evidence integrity across duplicate reports and reject/re-resolve cycles
"""

import pytest
import io
from datetime import datetime, timedelta
from app.core.time import utc_now
from uuid import uuid4
from PIL import Image
from sqlmodel import Session, select, desc

from app.models.domain import Category, User, Issue, Evidence, Otp
from app.services.exif import ExifService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed(session: Session):
    cat = Category(name="Pothole", default_priority="P2", expected_sla_days=7)
    session.add(cat)
    citizen = User(email="citizen@test.com", role="CITIZEN")
    admin = User(email="admin@authority.gov.in", role="ADMIN")
    worker = User(email="worker@authority.gov.in", role="WORKER")
    for u in (citizen, admin, worker):
        session.add(u)
    session.commit()
    for obj in (cat, citizen, admin, worker):
        session.refresh(obj)
    return cat, citizen, admin, worker


def _create_issue(session: Session, cat, reporter, status="REPORTED", worker=None):
    issue = Issue(
        category_id=cat.id,
        status=status,
        location="SRID=4326;POINT(78.35 17.44)",
        reporter_id=reporter.id,
        worker_id=worker.id if worker else None,
    )
    session.add(issue)
    session.commit()
    session.refresh(issue)
    return issue


def _login(client, session: Session, email: str):
    client.post("/api/v1/auth/otp-request", json={"email": email})
    otp = (
        session.exec(
            select(Otp).where(Otp.email == email).order_by(desc(Otp.created_at))
        )
        .first()
    )
    assert otp is not None
    resp = client.post("/api/v1/auth/login", json={"email": email, "otp": otp.code})
    assert resp.status_code == 200


def _make_jpeg(width=100, height=100, color=(0, 128, 0)):
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# ===========================================================================
# 1. EXIF SERVICE UNIT TESTS
# ===========================================================================


class TestExifServiceUnit:
    """Direct tests of ExifService methods."""

    def test_extract_metadata_no_exif(self, client, session):
        """Plain JPEG with no EXIF returns default values."""
        photo = _make_jpeg()
        meta = ExifService.extract_metadata(photo)
        assert meta["lat"] is None
        assert meta["lng"] is None
        # timestamp should be approximately now
        assert abs((utc_now() - meta["timestamp"]).total_seconds()) < 5

    def test_validate_proximity_same_point(self, client, session):
        result = ExifService.validate_proximity(17.44, 78.35, 17.44, 78.35)
        assert result is True

    def test_validate_proximity_far_away(self, client, session):
        # Hyderabad vs Delhi — hundreds of km
        result = ExifService.validate_proximity(17.44, 78.35, 28.6, 77.2)
        assert result is False

    def test_validate_proximity_none_coords(self, client, session):
        result = ExifService.validate_proximity(17.44, 78.35, None, None)
        assert result is False

    def test_validate_timestamp_recent(self, client, session):
        recent = utc_now() - timedelta(hours=1)
        assert ExifService.validate_timestamp(recent) is True

    def test_validate_timestamp_old(self, client, session):
        old = utc_now() - timedelta(days=30)
        assert ExifService.validate_timestamp(old) is False


# ===========================================================================
# 2. EVIDENCE CREATION
# ===========================================================================


class TestEvidenceCreation:
    """Evidence records created during report and resolve flows."""

    def test_report_creates_evidence_record(self, client, session):
        cat, citizen, _, _ = _seed(session)
        photo = _make_jpeg()
        _login(client, session, citizen.email)

        resp = client.post(
            "/api/v1/issues/report",
            data={
                "category_id": str(cat.id),
                "lat": "17.44",
                "lng": "78.35",
            },
            files={"photo": ("test.jpg", photo, "image/jpeg")},
        )
        assert resp.status_code == 200
        issue_id = resp.json()["issue_id"]

        from uuid import UUID

        session.expire_all()
        evidences = session.exec(
            select(Evidence).where(Evidence.issue_id == UUID(issue_id))
        ).all()
        assert len(evidences) == 1
        assert evidences[0].type == "REPORT"
        assert evidences[0].file_path.startswith("issues/")
        assert evidences[0].reporter_id == citizen.id

    def test_resolve_creates_evidence_record(self, client, session):
        cat, citizen, admin, worker = _seed(session)
        issue = _create_issue(session, cat, citizen, status="ASSIGNED", worker=worker)

        _login(client, session, worker.email)
        eta = (utc_now() + timedelta(hours=4)).isoformat() + "Z"
        client.post(f"/api/v1/worker/tasks/{issue.id}/accept?eta_date={eta}")

        client.post(f"/api/v1/worker/tasks/{issue.id}/start")

        photo = _make_jpeg(color=(255, 0, 0))
        resp = client.post(
            f"/api/v1/worker/tasks/{issue.id}/resolve",
            files={"photo": ("after.jpg", photo, "image/jpeg")},
        )
        assert resp.status_code == 200

        session.expire_all()
        evidences = session.exec(
            select(Evidence).where(
                Evidence.issue_id == issue.id, Evidence.type == "RESOLVE"
            )
        ).all()
        assert len(evidences) == 1
        assert evidences[0].file_path.startswith("resolutions/")


# ===========================================================================
# 3. MEDIA ENDPOINT
# ===========================================================================


class TestMediaEndpoint:
    """GET /api/v1/media/{issue_id}/{type}"""

    def test_get_before_image_returns_jpeg(self, client, session):
        cat, citizen, _, _ = _seed(session)
        photo = _make_jpeg()
        _login(client, session, citizen.email)

        # Report issue (creates REPORT evidence in MinIO)
        resp = client.post(
            "/api/v1/issues/report",
            data={
                "category_id": str(cat.id),
                "lat": "17.44",
                "lng": "78.35",
            },
            files={"photo": ("test.jpg", photo, "image/jpeg")},
        )
        assert resp.status_code == 200
        issue_id = resp.json()["issue_id"]

        # Retrieve before image
        resp = client.get(f"/api/v1/media/{issue_id}/before")
        assert resp.status_code == 200
        assert "image/jpeg" in resp.headers.get("content-type", "")
        assert len(resp.content) > 0

    def test_get_after_image_returns_jpeg(self, client, session):
        cat, citizen, admin, worker = _seed(session)
        issue = _create_issue(session, cat, citizen, status="ASSIGNED", worker=worker)

        _login(client, session, worker.email)
        eta = (utc_now() + timedelta(hours=4)).isoformat() + "Z"
        client.post(f"/api/v1/worker/tasks/{issue.id}/accept?eta_date={eta}")
        client.post(f"/api/v1/worker/tasks/{issue.id}/start")

        photo = _make_jpeg(color=(0, 0, 255))
        resp = client.post(
            f"/api/v1/worker/tasks/{issue.id}/resolve",
            files={"photo": ("after.jpg", photo, "image/jpeg")},
        )
        assert resp.status_code == 200

        # Retrieve after image
        resp = client.get(f"/api/v1/media/{issue.id}/after")
        assert resp.status_code == 200
        assert "image/jpeg" in resp.headers.get("content-type", "")

    def test_get_media_404_when_no_evidence(self, client, session):
        cat, citizen, _, _ = _seed(session)
        issue = _create_issue(session, cat, citizen)

        resp = client.get(f"/api/v1/media/{issue.id}/before")
        assert resp.status_code == 404

    def test_get_media_404_for_nonexistent_issue(self, client, session):
        _seed(session)
        fake_id = uuid4()
        resp = client.get(f"/api/v1/media/{fake_id}/before")
        assert resp.status_code == 404


# ===========================================================================
# 4. EVIDENCE INTEGRITY
# ===========================================================================


class TestEvidenceIntegrity:
    """Evidence accumulation across duplicate reports and reject cycles."""

    def test_duplicate_report_creates_additional_evidence(self, client, session):
        cat, citizen, _, _ = _seed(session)
        photo = _make_jpeg()
        _login(client, session, citizen.email)

        resp1 = client.post(
            "/api/v1/issues/report",
            data={
                "category_id": str(cat.id),
                "lat": "17.44",
                "lng": "78.35",
            },
            files={"photo": ("test1.jpg", photo, "image/jpeg")},
        )
        assert resp1.status_code == 200
        issue_id = resp1.json()["issue_id"]

        resp2 = client.post(
            "/api/v1/issues/report",
            data={
                "category_id": str(cat.id),
                "lat": "17.44",
                "lng": "78.35",
            },
            files={"photo": ("test2.jpg", photo, "image/jpeg")},
        )
        assert resp2.status_code == 200
        assert resp2.json()["issue_id"] == issue_id

        from uuid import UUID

        session.expire_all()
        evidences = session.exec(
            select(Evidence).where(
                Evidence.issue_id == UUID(issue_id), Evidence.type == "REPORT"
            )
        ).all()
        assert len(evidences) == 2

    def test_resolve_reject_reresolve_creates_two_resolve_evidences(
        self, client, session
    ):
        cat, citizen, admin, worker = _seed(session)
        issue = _create_issue(session, cat, citizen, status="ASSIGNED", worker=worker)

        _login(client, session, worker.email)
        eta = (utc_now() + timedelta(hours=4)).isoformat() + "Z"
        client.post(f"/api/v1/worker/tasks/{issue.id}/accept?eta_date={eta}")
        client.post(f"/api/v1/worker/tasks/{issue.id}/start")

        photo = _make_jpeg(color=(255, 0, 0))
        resp = client.post(
            f"/api/v1/worker/tasks/{issue.id}/resolve",
            files={"photo": ("after1.jpg", photo, "image/jpeg")},
        )
        assert resp.status_code == 200

        _login(client, session, admin.email)
        resp = client.post(f"/api/v1/admin/reject?issue_id={issue.id}&reason=Bad photo")
        assert resp.status_code == 200

        _login(client, session, worker.email)
        photo2 = _make_jpeg(color=(0, 0, 255))
        resp = client.post(
            f"/api/v1/worker/tasks/{issue.id}/resolve",
            files={"photo": ("after2.jpg", photo2, "image/jpeg")},
        )
        assert resp.status_code == 200

        session.expire_all()
        evidences = session.exec(
            select(Evidence).where(
                Evidence.issue_id == issue.id, Evidence.type == "RESOLVE"
            )
        ).all()
        assert len(evidences) == 2

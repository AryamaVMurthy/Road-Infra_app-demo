import io

from PIL import Image
from sqlmodel import select

from app.core.config import settings
from app.models.domain import Category, Evidence, Issue
from app.services.minio_client import minio_client
from conftest import login_via_otp


def _make_test_image_bytes() -> bytes:
    img = Image.new("RGB", (64, 64), color="blue")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format="JPEG")
    return img_buffer.getvalue()


def test_report_issue_uploads_to_minio(client, session):
    if not minio_client.bucket_exists(settings.MINIO_BUCKET):
        minio_client.make_bucket(settings.MINIO_BUCKET)

    category = Category(name="Pothole", default_priority="P2")
    session.add(category)
    session.commit()
    session.refresh(category)
    login_via_otp(client, session, "storage@test.com")

    file_content = _make_test_image_bytes()
    response = client.post(
        "/api/v1/issues/report",
        data={
            "category_id": str(category.id),
            "lat": 17.4447,
            "lng": 78.3483,
            "address": "Storage Avenue",
        },
        files={"photo": ("test.jpg", file_content, "image/jpeg")},
    )

    assert response.status_code == 200
    issue_id = response.json()["issue_id"]
    issue = session.get(Issue, issue_id)
    assert issue is not None

    evidence = session.exec(
        select(Evidence).where(Evidence.issue_id == issue.id)
    ).first()
    assert evidence is not None
    assert evidence.file_path

    result = minio_client.stat_object(settings.MINIO_BUCKET, evidence.file_path)
    assert result.object_name == evidence.file_path

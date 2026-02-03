from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select
from app.db.session import get_session
from app.models.domain import Evidence
from app.services.minio_client import minio_client
from app.core.config import settings
from uuid import UUID

router = APIRouter()


@router.get("/{issue_id}/{type}")
def get_media(issue_id: UUID, type: str, session: Session = Depends(get_session)):
    # type is 'before' (REPORT) or 'after' (RESOLVE)
    evidence_type = "REPORT" if type == "before" else "RESOLVE"

    statement = (
        select(Evidence)
        .where(Evidence.issue_id == issue_id, Evidence.type == evidence_type)
        .order_by(Evidence.created_at.desc())
    )

    evidence = session.exec(statement).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Media not found")

    try:
        response = minio_client.get_object(settings.MINIO_BUCKET, evidence.file_path)
        return Response(content=response.read(), media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve storage object")

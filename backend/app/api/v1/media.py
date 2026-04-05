from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select
from app.db.session import get_session
from app.models.domain import Evidence
from app.services.minio_client import minio_client
from app.core.config import settings
from uuid import UUID
from app.schemas.common import ErrorResponse

router = APIRouter()


@router.get(
    "/{issue_id}/{type}",
    summary="Fetch issue media",
    description="Return the latest before or after JPEG evidence image for an issue from object storage.",
    responses={
        200: {
            "description": "JPEG issue evidence image",
            "content": {
                "image/jpeg": {
                    "schema": {"type": "string", "format": "binary"}
                }
            },
        },
        400: {"model": ErrorResponse, "description": "Media type is invalid"},
        404: {"model": ErrorResponse, "description": "Media not found"},
        500: {"model": ErrorResponse, "description": "Media retrieval failed"},
    },
)
def get_media(issue_id: UUID, type: str, session: Session = Depends(get_session)):
    # type is 'before' (REPORT) or 'after' (RESOLVE)
    if type not in {"before", "after"}:
        raise HTTPException(
            status_code=400,
            detail="Media type must be either 'before' or 'after'",
        )

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

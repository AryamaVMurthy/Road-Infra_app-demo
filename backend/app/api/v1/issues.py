import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlmodel import Session, select, col
from app.db.session import get_session
from app.models.domain import Category, Issue, Evidence, User
from app.schemas.common import ErrorResponse
from app.schemas.issue import IssueRead, IssueReportRejectedResponse, IssueReportResponse
from app.services.issue_service import IssueService
from app.api.deps import get_vlm_gateway_client, require_citizen_user
from app.services.report_intake_service import ReportIntakeService
from app.services.vlm_client import VLMGatewayClient
from uuid import UUID
from typing import Any, List, Optional, cast

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/report",
    response_model=IssueReportResponse | IssueReportRejectedResponse,
    summary="Report a road issue",
    description="Create a new citizen issue report or merge it into an existing nearby report when the location is a duplicate.",
    responses={
        404: {"model": ErrorResponse, "description": "Issue category not found"},
        422: {"model": ErrorResponse, "description": "No authority jurisdiction covers the supplied coordinates"},
    },
)
async def report_issue(
    category_id: Optional[UUID] = Form(None),
    lat: float = Form(...),
    lng: float = Form(...),
    address: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    photo: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_citizen_user),
    vlm_client: VLMGatewayClient = Depends(get_vlm_gateway_client),
):
    outcome = ReportIntakeService.submit_citizen_report(
        session=session,
        reporter=current_user,
        lat=lat,
        lng=lng,
        address=address,
        reporter_notes=description,
        photo_content=await photo.read(),
        mime_type=photo.content_type or "image/jpeg",
        vlm_client=vlm_client,
    )
    if outcome.accepted:
        return outcome.response
    return JSONResponse(status_code=outcome.status_code, content=outcome.response.model_dump(mode="json"))


@router.get(
    "/my-reports",
    response_model=List[IssueRead],
    summary="List reports created by the current user",
    description="Return all issues reported by the current user, including duplicate reports linked through evidence records.",
)
def get_my_reports(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_citizen_user),
):
    # Get all issues where user is the reporter OR has provided evidence
    # (Handling duplicates where reporter_id might be different but evidence exists)
    from sqlalchemy import or_
    from sqlalchemy.orm import selectinload

    statement = (
        select(Issue)
        .join(Evidence, isouter=True)
        .where(
            or_(
                col(Issue.reporter_id) == current_user.id,
                col(Evidence.reporter_id) == current_user.id,
            )
        )
        .distinct()
        .options(
            selectinload(cast(Any, Issue.category)),
            selectinload(cast(Any, Issue.worker)),
        )
    )

    return session.exec(statement).all()

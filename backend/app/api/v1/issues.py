import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, select, col
from app.db.session import get_session
from app.models.domain import Category, Issue, Evidence, User
from app.schemas.common import ErrorResponse
from app.schemas.issue import IssueRead, IssueReportResponse
from app.services.issue_service import IssueService
from app.api.deps import require_citizen_user
from uuid import UUID
from typing import Any, List, Optional, cast

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/report",
    response_model=IssueReportResponse,
    summary="Report a road issue",
    description="Create a new citizen issue report or merge it into an existing nearby report when the location is a duplicate.",
    responses={
        404: {"model": ErrorResponse, "description": "Issue category not found"},
        422: {"model": ErrorResponse, "description": "No authority jurisdiction covers the supplied coordinates"},
    },
)
async def report_issue(
    category_id: UUID = Form(...),
    lat: float = Form(...),
    lng: float = Form(...),
    address: Optional[str] = Form(None),
    photo: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_citizen_user),
):
    reporter = current_user
    category = session.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Issue category not found")

    point_wkt = IssueService.build_point_wkt(lat, lng)
    duplicate_issue = IssueService.find_duplicate_issue(session, point_wkt)

    if duplicate_issue:
        photo_content = await photo.read()
        exif_data = IssueService.extract_exif(photo_content)
        file_path = IssueService.store_issue_photo(photo_content)
        duplicate_issue.report_count += 1
        evidence = IssueService.build_evidence(
            duplicate_issue.id, reporter.id, file_path, exif_data
        )
        session.add(duplicate_issue)
        session.add(evidence)
        session.commit()
        return IssueReportResponse(
            message="Report submitted successfully",
            issue_id=duplicate_issue.id,
        )

    org_id = IssueService.find_org_for_location(session, point_wkt)
    if org_id is None:
        logger.warning(
            "Rejected issue report outside configured jurisdiction for reporter=%s lat=%s lng=%s",
            reporter.email,
            lat,
            lng,
        )
        raise HTTPException(
            status_code=422,
            detail=(
                f"No authority jurisdiction covers coordinates lat={lat}, lng={lng}. "
                "Ask a system administrator to configure coverage for this area."
            ),
        )

    photo_content = await photo.read()
    exif_data = IssueService.extract_exif(photo_content)
    file_path = IssueService.store_issue_photo(photo_content)

    new_issue = Issue(
        category_id=category_id,
        status="REPORTED",
        location=point_wkt,
        address=address,
        reporter_id=reporter.id,
        org_id=org_id,
        priority=None,
        report_count=1,
    )
    session.add(new_issue)
    session.commit()
    session.refresh(new_issue)

    evidence = IssueService.build_evidence(
        new_issue.id, reporter.id, file_path, exif_data
    )
    session.add(evidence)
    session.commit()
    return IssueReportResponse(
        message="Report submitted successfully",
        issue_id=new_issue.id,
    )


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

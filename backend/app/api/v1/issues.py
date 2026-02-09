from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlmodel import Session, select, col
from app.db.session import get_session
from app.models.domain import Issue, Evidence, User
from app.schemas.issue import IssueRead
from app.services.issue_service import IssueService
from app.api.deps import require_citizen_user
from uuid import UUID
from typing import List, Optional

router = APIRouter()


@router.post("/report")
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
    point_wkt = IssueService.build_point_wkt(lat, lng)
    duplicate_issue = IssueService.find_duplicate_issue(session, point_wkt)

    photo_content = await photo.read()
    exif_data = IssueService.extract_exif(photo_content)
    file_path = IssueService.store_issue_photo(photo_content)

    if duplicate_issue:
        duplicate_issue.report_count += 1
        evidence = IssueService.build_evidence(
            duplicate_issue.id, reporter.id, file_path, exif_data
        )
        session.add(duplicate_issue)
        session.add(evidence)
        session.commit()
        return {
            "message": "Report submitted successfully",
            "issue_id": str(duplicate_issue.id),
        }
    else:
        new_issue = Issue(
            category_id=category_id,
            status="REPORTED",
            location=point_wkt,
            address=address,
            reporter_id=reporter.id,
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
        return {
            "message": "Report submitted successfully",
            "issue_id": str(new_issue.id),
        }


@router.get("/my-reports", response_model=List[IssueRead])
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
        .options(selectinload(Issue.category), selectinload(Issue.worker))
    )

    return session.exec(statement).all()

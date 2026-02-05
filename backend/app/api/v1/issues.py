from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlmodel import Session, select, func, col
from app.db.session import get_session
from app.models.domain import Issue, Evidence, User, Category
from app.schemas.issue import IssueRead
from app.services.issue_service import IssueService
from uuid import UUID
from typing import List, Optional

router = APIRouter()


@router.post("/report")
async def report_issue(
    category_id: UUID = Form(...),
    lat: float = Form(...),
    lng: float = Form(...),
    address: Optional[str] = Form(None),
    reporter_email: str = Form(...),
    photo: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    reporter = IssueService.get_or_create_reporter(session, reporter_email)
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
def get_my_reports(email: str, session: Session = Depends(get_session)):
    statement = select(User).where(User.email == email)
    user = session.exec(statement).first()
    if not user:
        return []

    # Get all issues where user is the reporter OR has provided evidence
    # (Handling duplicates where reporter_id might be different but evidence exists)
    from sqlalchemy import or_
    from sqlalchemy.orm import selectinload

    statement = (
        select(Issue)
        .join(Evidence, isouter=True)
        .where(
            or_(
                col(Issue.reporter_id) == user.id,
                col(Evidence.reporter_id) == user.id,
            )
        )
        .distinct()
    )

    return session.exec(statement).all()

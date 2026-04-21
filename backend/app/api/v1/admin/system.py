from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import Session, select

from app.api.deps import require_admin_user, require_roles
from app.db.session import get_session
from app.models.domain import Category, Issue, ReportIntakeSubmission, User
from app.schemas.common import MessageResponse
from app.schemas.system_admin import (
    AuthorityCreateRequest,
    AuthorityRead,
    AuthorityUpdateRequest,
    IssueTypeCreateRequest,
    IssueTypeUpdateRequest,
    ManualIssueCreateRequest,
    ManualIssueCreateResponse,
)
from app.schemas.issue import (
    IntakeArchiveDetailRead,
    IntakeArchiveRead,
    IntakeSpamOverrideRequest,
)
from app.services.minio_client import minio_client
from app.core.config import settings
from app.services.system_admin_service import SystemAdminService
from app.services.issue_service import IssueService
from app.services.audit import AuditService

router = APIRouter()
require_sysadmin_user = require_roles("SYSADMIN")


@router.get(
    "/authorities",
    response_model=List[AuthorityRead],
    summary="List authorities",
    description="Return all configured authority organizations with linked zone metadata and user counts.",
)
def list_authorities(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    return SystemAdminService.list_authorities(session)


@router.post(
    "/authorities",
    response_model=AuthorityRead,
    summary="Create an authority",
    description="Create a new authority organization, provision its admin account, and attach a jurisdiction polygon.",
)
def create_authority(
    data: AuthorityCreateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    organization = SystemAdminService.create_authority(
        session,
        name=data.name,
        admin_email=str(data.admin_email),
        jurisdiction_points=data.jurisdiction_points,
        actor_id=current_user.id,
        zone_name=data.zone_name,
    )
    session.commit()

    return next(
        auth
        for auth in SystemAdminService.list_authorities(session)
        if auth["org_id"] == organization.id
    )


@router.put(
    "/authorities/{org_id}",
    response_model=AuthorityRead,
    summary="Update an authority",
    description="Update an existing authority organization, including its name and jurisdiction polygon.",
)
def update_authority(
    org_id: UUID,
    data: AuthorityUpdateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    organization = SystemAdminService.update_authority(
        session,
        org_id=org_id,
        actor_id=current_user.id,
        name=data.name,
        jurisdiction_points=data.jurisdiction_points,
        zone_name=data.zone_name,
    )
    session.commit()
    return next(
        auth
        for auth in SystemAdminService.list_authorities(session)
        if auth["org_id"] == organization.id
    )


@router.delete(
    "/authorities/{org_id}",
    response_model=MessageResponse,
    summary="Delete an authority",
    description="Delete an authority organization and its related configuration after system-admin validation passes.",
)
def delete_authority(
    org_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    SystemAdminService.delete_authority(
        session, org_id=org_id, actor_id=current_user.id
    )
    session.commit()
    return {"message": "Authority deleted"}


@router.get(
    "/issue-types",
    response_model=List[Category],
    summary="List issue types",
    description="Return all issue categories, optionally including inactive categories used for historical records.",
)
def list_issue_types(
    include_inactive: bool = Query(default=True),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    statement = select(Category)
    if not include_inactive:
        statement = statement.where(Category.is_active == True)
    return session.exec(statement).all()


@router.post(
    "/issue-types",
    response_model=Category,
    summary="Create an issue type",
    description="Create a new issue category that citizens and administrators can use when creating reports.",
)
def create_issue_type(
    data: IssueTypeCreateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    category = SystemAdminService.create_issue_type(
        session,
        name=data.name,
        actor_id=current_user.id,
        classification_guidance=data.classification_guidance,
    )
    session.commit()
    session.refresh(category)
    return category


@router.put(
    "/issue-types/{category_id}",
    response_model=Category,
    summary="Update an issue type",
    description="Update the display name or activation status for an existing issue category.",
)
def update_issue_type(
    category_id: UUID,
    data: IssueTypeUpdateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    category = SystemAdminService.update_issue_type(
        session,
        category_id=category_id,
        actor_id=current_user.id,
        name=data.name,
        is_active=data.is_active,
        classification_guidance=data.classification_guidance,
    )
    session.commit()
    session.refresh(category)
    return category


@router.delete(
    "/issue-types/{category_id}",
    response_model=Category,
    summary="Deactivate an issue type",
    description="Soft-delete an issue category by marking it inactive while preserving historical issue references.",
)
def delete_issue_type(
    category_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    category = SystemAdminService.deactivate_issue_type(
        session,
        category_id=category_id,
        actor_id=current_user.id,
    )
    session.commit()
    session.refresh(category)
    return category


@router.post(
    "/manual-issues",
    response_model=ManualIssueCreateResponse,
    summary="Create a manual issue",
    description="Create an issue directly from the administrative console, optionally targeting a specific authority organization.",
)
def create_manual_issue(
    data: ManualIssueCreateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    issue = SystemAdminService.create_manual_issue(
        session,
        actor=current_user,
        category_id=data.category_id,
        lat=data.lat,
        lng=data.lng,
        address=data.address,
        org_id=data.org_id,
    )
    session.commit()
    session.refresh(issue)
    return ManualIssueCreateResponse(
        issue_id=issue.id,
        message="Manual issue created",
        created_at=issue.created_at,
    )


@router.get(
    "/intake-archive",
    response_model=List[IntakeArchiveRead],
    summary="List rejected/system-error intake submissions",
    description="Return rejected or system-error intake submissions for sysadmin review and fraud analysis.",
)
def list_intake_archive(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    statement = select(ReportIntakeSubmission).where(
        ReportIntakeSubmission.status.in_(
            ["REJECTED_SPAM", "SYSTEM_ERROR", "ACCEPTED_UNCATEGORIZED", "OVERRIDDEN_TO_ACCEPTED"]
        )
    )
    statement = statement.order_by(ReportIntakeSubmission.created_at.desc())
    return session.exec(statement).all()


@router.get(
    "/intake-archive/{submission_id}",
    response_model=IntakeArchiveDetailRead,
    summary="Get an intake submission archive record",
    description="Return a single rejected or system-error intake submission with full VLM outputs for sysadmin review.",
)
def get_intake_archive_submission(
    submission_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    submission = session.get(ReportIntakeSubmission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Archive submission not found")

    archive_detail = IntakeArchiveDetailRead.model_validate(submission)
    archive_detail.image_url = (
        f"{settings.API_V1_STR}/admin/intake-archive/{submission.id}/image"
    )
    return archive_detail


@router.get(
    "/intake-archive/{submission_id}/image",
    summary="Fetch the archived submission image",
    description="Return the original archived intake image for a rejected or system-error submission.",
    responses={
        200: {
            "description": "Archived submission image",
            "content": {
                "image/jpeg": {
                    "schema": {"type": "string", "format": "binary"}
                }
            },
        }
    },
)
def get_intake_archive_image(
    submission_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    submission = session.get(ReportIntakeSubmission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Archive submission not found")

    try:
        response = minio_client.get_object(settings.MINIO_BUCKET, submission.file_path)
        return Response(content=response.read(), media_type=submission.mime_type)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500, detail="Failed to retrieve archived submission image"
        ) from exc


@router.post(
    "/intake-archive/{submission_id}/mark-not-spam",
    response_model=MessageResponse,
    summary="Override a spam decision and create an uncategorized issue",
    description="Convert a spam-rejected intake submission into an uncategorized issue after manual admin review confirms it is a valid civic report.",
)
def mark_submission_not_spam(
    submission_id: UUID,
    data: IntakeSpamOverrideRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_sysadmin_user),
):
    submission = session.get(ReportIntakeSubmission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Archive submission not found")
    if submission.issue_id is not None:
        raise HTTPException(status_code=409, detail="Archive submission is already linked to an issue")
    if submission.status != "REJECTED_SPAM":
        raise HTTPException(status_code=409, detail="Only spam-rejected submissions can be overridden")

    issue = Issue(
        category_id=None,
        status="REPORTED",
        location=IssueService.build_point_wkt(submission.lat, submission.lng),
        address=submission.address,
        reporter_id=submission.reporter_id,
        org_id=submission.org_id,
        priority="P3",
        report_count=1,
        intake_submission_id=submission.id,
        classification_source=submission.classification_source,
        classification_confidence=submission.selected_category_confidence,
        classification_model_id=submission.model_id,
        classification_model_quantization=submission.model_quantization,
        classification_prompt_version=submission.prompt_version,
        reporter_notes=submission.reporter_notes,
    )
    session.add(issue)
    session.commit()
    session.refresh(issue)

    evidence = IssueService.build_evidence(
        issue.id,
        submission.reporter_id,
        submission.file_path,
        {},
    )
    submission.issue_id = issue.id
    submission.status = "ACCEPTED_UNCATEGORIZED"
    submission.reason_code = "OVERRIDDEN_NOT_SPAM"
    session.add(evidence)
    session.add(submission)
    AuditService.log(
        session,
        "INTAKE_OVERRIDE_TO_ACCEPTED",
        "INTAKE_SUBMISSION",
        submission.id,
        current_user.id,
        "REJECTED_SPAM",
        "ACCEPTED_UNCATEGORIZED",
    )
    session.commit()
    return {"message": "Submission converted into an uncategorized issue"}

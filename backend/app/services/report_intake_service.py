"""Citizen report intake orchestration for AI-backed spam gating."""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from io import BytesIO
from typing import Optional

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError
from sqlmodel import Session, select

from app.models.domain import Category, Issue, ReportIntakeSubmission, User
from app.schemas.issue import IssueReportRejectedResponse, IssueReportResponse
from app.services.issue_service import IssueService
from app.services.audit import AuditService
from app.services.vlm_client import (
    VLMClassificationResult,
    VLMGatewayClient,
    VLMGatewayError,
)


@dataclass(slots=True)
class ReportIntakeOutcome:
    accepted: bool
    response: IssueReportResponse | IssueReportRejectedResponse
    status_code: int


class ReportIntakeService:
    @staticmethod
    def submit_citizen_report(
        *,
        session: Session,
        reporter: User,
        lat: float,
        lng: float,
        address: Optional[str],
        reporter_notes: Optional[str],
        photo_content: bytes,
        mime_type: str,
        vlm_client: VLMGatewayClient,
    ) -> ReportIntakeOutcome:
        normalized_photo = ReportIntakeService._validate_and_normalize_image(photo_content)
        point_wkt = IssueService.build_point_wkt(lat, lng)
        org_id = IssueService.find_org_for_location(session, point_wkt)
        if org_id is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"No authority jurisdiction covers coordinates lat={lat}, lng={lng}. "
                    "Ask a system administrator to configure coverage for this area."
                ),
            )

        active_categories = session.exec(
            select(Category).where(Category.is_active == True)
        ).all()
        if not active_categories:
            raise HTTPException(
                status_code=500,
                detail="No active issue types are configured for spam gating",
            )

        exif_data = IssueService.extract_exif(normalized_photo)
        file_path = IssueService.store_issue_photo(normalized_photo, prefix="issues")
        submission = ReportIntakeSubmission(
            reporter_id=reporter.id,
            org_id=org_id,
            status="PENDING",
            reporter_notes=reporter_notes,
            address=address,
            lat=lat,
            lng=lng,
            file_path=file_path,
            mime_type=mime_type,
            image_sha256=hashlib.sha256(normalized_photo).hexdigest(),
            prompt_version="v1",
        )
        session.add(submission)
        session.commit()
        session.refresh(submission)

        try:
            classification = vlm_client.classify_intake(
                submission_id=str(submission.id),
                image_base64=base64.b64encode(normalized_photo).decode("ascii"),
                mime_type=mime_type,
                reporter_notes=reporter_notes,
                active_categories={
                    category.name: category.classification_guidance or category.name
                    for category in active_categories
                },
                prompt_version="v1",
            )
        except VLMGatewayError as exc:
            submission.status = "SYSTEM_ERROR"
            submission.reason_code = "VLM_GATEWAY_ERROR"
            AuditService.log(
                session,
                "INTAKE_SYSTEM_ERROR",
                "INTAKE_SUBMISSION",
                submission.id,
                reporter.id,
                None,
                submission.reason_code,
            )
            session.add(submission)
            session.commit()
            raise HTTPException(
                status_code=503,
                detail=str(exc),
            ) from exc

        ReportIntakeService._apply_classification_metadata(
            submission=submission,
            classification=classification,
        )

        if classification.decision == "REJECTED":
            submission.status = "REJECTED_SPAM"
            submission.reason_code = "SPAM_REJECTED"
            AuditService.log(
                session,
                "INTAKE_REJECTED_SPAM",
                "INTAKE_SUBMISSION",
                submission.id,
                reporter.id,
                None,
                "REJECTED_SPAM",
            )
            session.add(submission)
            session.commit()
            return ReportIntakeOutcome(
                accepted=False,
                status_code=422,
                response=IssueReportRejectedResponse(
                    message="Report rejected by intake screening",
                    submission_id=submission.id,
                ),
            )
        if classification.decision != "IN_SCOPE":
            submission.status = "SYSTEM_ERROR"
            submission.reason_code = "UNKNOWN_GATEWAY_DECISION"
            session.add(submission)
            session.commit()
            raise HTTPException(
                status_code=503,
                detail="VLM gateway returned an unsupported spam-gating decision",
            )

        duplicate_issue = IssueService.find_duplicate_issue(session, point_wkt)
        if duplicate_issue is not None:
            duplicate_issue.report_count += 1
            evidence = IssueService.build_evidence(
                duplicate_issue.id,
                reporter.id,
                file_path,
                exif_data,
            )
            submission.status = "ACCEPTED_UNCATEGORIZED"
            submission.reason_code = "IN_SCOPE"
            submission.issue_id = duplicate_issue.id
            AuditService.log(
                session,
                "INTAKE_ACCEPTED_UNCATEGORIZED",
                "INTAKE_SUBMISSION",
                submission.id,
                reporter.id,
                None,
                str(duplicate_issue.id),
            )
            session.add(duplicate_issue)
            session.add(evidence)
            session.add(submission)
            session.commit()
            return ReportIntakeOutcome(
                accepted=True,
                status_code=200,
                response=IssueReportResponse(
                    message="Report submitted successfully",
                    issue_id=duplicate_issue.id,
                    submission_id=submission.id,
                    category_id=duplicate_issue.category_id,
                    category_name=duplicate_issue.category_name if duplicate_issue.category_id else None,
                    duplicate_merged=True,
                    requires_admin_category_assignment=duplicate_issue.category_id is None,
                ),
            )

        new_issue = Issue(
            category_id=None,
            status="REPORTED",
            location=point_wkt,
            address=address,
            reporter_id=reporter.id,
            org_id=org_id,
            priority="P3",
            report_count=1,
            intake_submission_id=submission.id,
            classification_source="vlm_gateway",
            classification_confidence=classification.confidence,
            classification_model_id=classification.model_id,
            classification_model_quantization=classification.model_quantization,
            classification_prompt_version=classification.prompt_version,
            reporter_notes=reporter_notes,
        )
        session.add(new_issue)
        session.commit()
        session.refresh(new_issue)

        evidence = IssueService.build_evidence(
            new_issue.id,
            reporter.id,
            file_path,
            exif_data,
        )
        submission.status = "ACCEPTED_UNCATEGORIZED"
        submission.reason_code = "IN_SCOPE"
        submission.issue_id = new_issue.id
        AuditService.log(
            session,
            "INTAKE_ACCEPTED_UNCATEGORIZED",
            "INTAKE_SUBMISSION",
            submission.id,
            reporter.id,
            None,
            str(new_issue.id),
        )
        session.add(evidence)
        session.add(submission)
        session.commit()

        return ReportIntakeOutcome(
            accepted=True,
            status_code=200,
            response=IssueReportResponse(
                message="Report submitted successfully",
                issue_id=new_issue.id,
                submission_id=submission.id,
                category_id=None,
                category_name=None,
                duplicate_merged=False,
                requires_admin_category_assignment=True,
            ),
        )

    @staticmethod
    def _apply_classification_metadata(
        *,
        submission: ReportIntakeSubmission,
        classification: VLMClassificationResult,
    ) -> None:
        submission.reason_code = "IN_SCOPE" if classification.decision == "IN_SCOPE" else "SPAM_REJECTED"
        submission.selected_category_id = None
        submission.selected_category_name_snapshot = None
        submission.selected_category_confidence = None
        submission.classification_source = "vlm_gateway"
        submission.model_id = classification.model_id
        submission.model_quantization = classification.model_quantization
        submission.prompt_version = classification.prompt_version
        submission.raw_primary_result = classification.raw_primary_result
        submission.raw_evaluator_result = classification.raw_evaluator_result
        submission.latency_ms = classification.latency_ms

    @staticmethod
    def _validate_and_normalize_image(photo_content: bytes) -> bytes:
        try:
            with Image.open(BytesIO(photo_content)) as image:
                image.load()
                normalized = image.convert("RGB")
        except UnidentifiedImageError as exc:
            raise HTTPException(status_code=422, detail="Uploaded file is not a valid image") from exc

        output = BytesIO()
        normalized.save(output, format="JPEG")
        return output.getvalue()

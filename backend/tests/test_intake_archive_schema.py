from app.models.domain import Category, Issue, ReportIntakeSubmission, User


def test_intake_submission_row_can_be_created(session):
    citizen = User(email="archive-citizen@example.com", role="CITIZEN")
    session.add(citizen)
    session.commit()
    session.refresh(citizen)

    submission = ReportIntakeSubmission(
        reporter_id=citizen.id,
        status="PENDING",
        reporter_notes="possible pothole near divider",
        address="Main Road",
        lat=17.4447,
        lng=78.3483,
        file_path="intake/submission.jpg",
        mime_type="image/jpeg",
        image_sha256="abc123",
        prompt_version="v1",
    )
    session.add(submission)
    session.commit()
    session.refresh(submission)

    assert submission.id is not None
    assert submission.status == "PENDING"
    assert submission.issue_id is None


def test_accepted_submission_can_link_to_uncategorized_issue(session):
    citizen = User(email="accepted-citizen@example.com", role="CITIZEN")
    category = Category(
        name="Pothole",
        classification_guidance="Road-surface cavity or collapse",
    )
    session.add(citizen)
    session.add(category)
    session.commit()
    session.refresh(citizen)
    session.refresh(category)

    issue = Issue(
        category_id=None,
        status="REPORTED",
        location="SRID=4326;POINT(78.3483 17.4447)",
        reporter_id=citizen.id,
        org_id=None,
        report_count=1,
        classification_source="vlm_gateway",
        classification_confidence=0.93,
        classification_model_id="LiquidAI/LFM2.5-VL-1.6B-GGUF",
        classification_model_quantization="Q8_0",
        classification_prompt_version="v1",
        reporter_notes="possible pothole near divider",
    )
    session.add(issue)
    session.commit()
    session.refresh(issue)

    submission = ReportIntakeSubmission(
        reporter_id=citizen.id,
        issue_id=issue.id,
        status="ACCEPTED_UNCATEGORIZED",
        reason_code="IN_SCOPE",
        classification_source="vlm_gateway",
        model_id="LiquidAI/LFM2.5-VL-1.6B-GGUF",
        model_quantization="Q8_0",
        prompt_version="v1",
        reporter_notes="possible pothole near divider",
        lat=17.4447,
        lng=78.3483,
        file_path="intake/submission.jpg",
        mime_type="image/jpeg",
        image_sha256="abc123",
        raw_primary_result={"decision": "IN_SCOPE"},
        raw_evaluator_result={"status": "pass"},
        latency_ms=900,
    )
    session.add(submission)
    session.commit()
    session.refresh(submission)

    assert submission.issue_id == issue.id
    assert submission.selected_category_id is None
    assert submission.selected_category_name_snapshot is None


def test_rejected_submission_does_not_require_issue_link(session):
    citizen = User(email="rejected-citizen@example.com", role="CITIZEN")
    session.add(citizen)
    session.commit()
    session.refresh(citizen)

    submission = ReportIntakeSubmission(
        reporter_id=citizen.id,
        status="REJECTED_SPAM",
        reason_code="SPAM_REJECTED",
        classification_source="vlm_gateway",
        model_id="LiquidAI/LFM2.5-VL-1.6B-GGUF",
        model_quantization="Q8_0",
        prompt_version="v1",
        lat=17.4447,
        lng=78.3483,
        file_path="intake/rejected.jpg",
        mime_type="image/jpeg",
        image_sha256="def456",
        raw_primary_result={"decision": "REJECTED"},
        raw_evaluator_result={"status": "skipped"},
        latency_ms=850,
    )
    session.add(submission)
    session.commit()
    session.refresh(submission)

    assert submission.issue_id is None
    assert submission.reason_code == "SPAM_REJECTED"

from pathlib import Path
import sys

import dspy
import pytest


sys.path.append(str(Path(__file__).resolve().parents[2]))


def _load_metrics_module():
    import importlib.util

    spec = importlib.util.find_spec("tools.dspy_intake.metrics")
    assert spec is not None, "Expected tools.dspy_intake.metrics to exist for the DSPy intake slice."
    return __import__("tools.dspy_intake.metrics", fromlist=["placeholder"])


def _level1_example(*, decision: str, category_name: str | None):
    return dspy.Example(
        image="unused",
        category_catalog="pothole|damaged_road|damaged_road_sign|garbage_litter",
        decision=decision,
        category_name=category_name,
    ).with_inputs("image", "category_catalog")


def _level2_example(*, category_name: str):
    return dspy.Example(
        image="unused",
        category_catalog="pothole|damaged_road|damaged_road_sign|garbage_litter",
        category_name=category_name,
    ).with_inputs("image", "category_catalog")


def test_level1_metric_penalizes_false_rejects_heavily():
    metrics = _load_metrics_module()

    in_scope_example = _level1_example(decision="IN_SCOPE", category_name="pothole")
    reject_example = _level1_example(decision="REJECT", category_name=None)

    false_reject = dspy.Prediction(
        decision="REJECT",
        best_matching_category_hint="",
        rationale="Rejecting an image that actually fits the pothole category.",
    )
    false_accept = dspy.Prediction(
        decision="IN_SCOPE",
        best_matching_category_hint="pothole",
        rationale="Treating an out-of-scope image as pothole damage.",
    )

    false_reject_result = metrics.score_level1_prediction(in_scope_example, false_reject)
    false_accept_result = metrics.score_level1_prediction(reject_example, false_accept)

    assert false_reject_result.score < false_accept_result.score


def test_level1_metric_penalizes_wrong_allowed_hint_on_in_scope_examples():
    metrics = _load_metrics_module()

    example = _level1_example(decision="IN_SCOPE", category_name="pothole")
    correct_hint = dspy.Prediction(
        decision="IN_SCOPE",
        best_matching_category_hint="pothole",
        rationale="Correct pothole match.",
    )
    wrong_hint = dspy.Prediction(
        decision="IN_SCOPE",
        best_matching_category_hint="garbage_litter",
        rationale="Decision is right but hint is wrong.",
    )

    correct_result = metrics.score_level1_prediction(example, correct_hint)
    wrong_result = metrics.score_level1_prediction(example, wrong_hint)

    assert wrong_result.score < correct_result.score
    assert "incorrectly suggests" in wrong_result.feedback


@pytest.mark.parametrize(
    ("example", "prediction", "expected_phrase"),
    [
        (
            _level1_example(decision="IN_SCOPE", category_name="damaged_road_sign"),
            dspy.Prediction(
                decision="REJECT",
                best_matching_category_hint="",
                rationale="Looks unrelated.",
            ),
            "category fit",
        ),
        (
            _level1_example(decision="REJECT", category_name=None),
            dspy.Prediction(
                decision="IN_SCOPE",
                best_matching_category_hint="garbage_litter",
                rationale="Looks like roadside trash.",
            ),
            "out-of-scope",
        ),
    ],
)
def test_level1_metric_feedback_references_category_fit_or_out_of_scope(
    example,
    prediction,
    expected_phrase,
):
    metrics = _load_metrics_module()

    result = metrics.score_level1_prediction(example, prediction)

    assert expected_phrase in result.feedback.lower()


def test_level2_metric_penalizes_pothole_collapse_more_than_other_wrong_label():
    metrics = _load_metrics_module()
    assert hasattr(
        metrics,
        "score_level2_prediction",
    ), "Expected score_level2_prediction to exist for the DSPy Level 2 slice."

    example = _level2_example(category_name="pothole")
    collapse_prediction = dspy.Prediction(
        category_name="damaged_road",
        rationale="Looks like general road-surface damage.",
    )
    other_wrong_prediction = dspy.Prediction(
        category_name="garbage_litter",
        rationale="Looks like trash near the roadway.",
    )

    collapse_result = metrics.score_level2_prediction(example, collapse_prediction)
    other_wrong_result = metrics.score_level2_prediction(example, other_wrong_prediction)

    assert collapse_result.score < other_wrong_result.score


def test_level2_metric_penalizes_non_surface_category_collapse_into_damaged_road():
    metrics = _load_metrics_module()

    example = _level2_example(category_name="garbage_litter")
    collapse_prediction = dspy.Prediction(
        category_name="damaged_road",
        rationale="Collapsed into generic surface damage.",
    )
    other_wrong_prediction = dspy.Prediction(
        category_name="damaged_road_sign",
        rationale="Wrong but not a surface-collapse label.",
    )

    collapse_result = metrics.score_level2_prediction(example, collapse_prediction)
    other_wrong_result = metrics.score_level2_prediction(example, other_wrong_prediction)

    assert collapse_result.score < other_wrong_result.score


def test_level2_metric_feedback_explains_pothole_vs_damaged_road_boundary():
    metrics = _load_metrics_module()

    example = _level2_example(category_name="damaged_road")
    prediction = dspy.Prediction(
        category_name="pothole",
        rationale="Looks like a pothole.",
    )

    result = metrics.score_level2_prediction(example, prediction)

    assert "discrete cavity" in result.feedback.lower()
    assert "damaged_road" in result.feedback
    assert "pothole" in result.feedback


def test_level2_metric_feedback_explains_garbage_vs_surface_confusion():
    metrics = _load_metrics_module()

    example = _level2_example(category_name="garbage_litter")
    prediction = dspy.Prediction(
        category_name="damaged_road",
        rationale="Collapsed into surface damage.",
    )

    result = metrics.score_level2_prediction(example, prediction)

    assert "trash" in result.feedback.lower() or "litter" in result.feedback.lower()
    assert "road surface" in result.feedback.lower()


def test_level1_metric_fails_fast_on_malformed_in_scope_gold_example():
    metrics = _load_metrics_module()

    malformed_example = _level1_example(decision="IN_SCOPE", category_name=None)
    prediction = dspy.Prediction(
        decision="IN_SCOPE",
        best_matching_category_hint="pothole",
        rationale="Predicting pothole.",
    )

    with pytest.raises(ValueError, match="category_name"):
        metrics.score_level1_prediction(malformed_example, prediction)


def test_level1_metric_fails_fast_on_malformed_reject_gold_example():
    metrics = _load_metrics_module()

    malformed_example = _level1_example(decision="REJECT", category_name="pothole")
    prediction = dspy.Prediction(
        decision="REJECT",
        best_matching_category_hint="",
        rationale="Correct reject.",
    )

    with pytest.raises(ValueError, match="category_name"):
        metrics.score_level1_prediction(malformed_example, prediction)


def test_level1_metric_fails_fast_when_prediction_hint_is_outside_active_subset():
    metrics = _load_metrics_module()

    example = dspy.Example(
        image="unused",
        category_catalog="pothole",
        decision="IN_SCOPE",
        category_name="pothole",
    ).with_inputs("image", "category_catalog")
    prediction = dspy.Prediction(
        decision="IN_SCOPE",
        best_matching_category_hint="garbage_litter",
        rationale="Wrong hint outside active subset.",
    )

    with pytest.raises(ValueError, match="active category subset|best_matching_category_hint"):
        metrics.score_level1_prediction(example, prediction)


def test_level1_metric_fails_fast_on_reject_prediction_with_non_empty_hint():
    metrics = _load_metrics_module()

    example = _level1_example(decision="IN_SCOPE", category_name="pothole")
    prediction = dspy.Prediction(
        decision="REJECT",
        best_matching_category_hint="pothole",
        rationale="Malformed reject prediction.",
    )

    with pytest.raises(ValueError, match="best_matching_category_hint"):
        metrics.score_level1_prediction(example, prediction)


@pytest.mark.parametrize("invalid_hint", [[], {}])
def test_level1_metric_fails_fast_on_non_string_hint_types(invalid_hint):
    metrics = _load_metrics_module()

    example = _level1_example(decision="IN_SCOPE", category_name="pothole")
    prediction = dspy.Prediction(
        decision="IN_SCOPE",
        best_matching_category_hint=invalid_hint,
        rationale="Malformed hint type.",
    )

    with pytest.raises(ValueError, match="best_matching_category_hint"):
        metrics.score_level1_prediction(example, prediction)


def test_level1_metric_accepts_multiline_guidance_with_pipe_characters():
    metrics = _load_metrics_module()

    example = dspy.Example(
        image="unused",
        category_catalog=(
            "pothole: Broken | missing surface.\n"
            "damaged_road: Road cracks or surface breakup."
        ),
        decision="IN_SCOPE",
        category_name="pothole",
    ).with_inputs("image", "category_catalog")
    prediction = dspy.Prediction(
        decision="IN_SCOPE",
        best_matching_category_hint="pothole",
        rationale="Correct pothole hint.",
    )

    result = metrics.score_level1_prediction(example, prediction)

    assert result.score == 1.0


@pytest.mark.parametrize(
    ("metric_name", "example", "prediction", "expected_phrase"),
    [
        (
            "level1_metric",
            _level1_example(decision="IN_SCOPE", category_name="pothole"),
            dspy.Prediction(
                decision="REJECT",
                best_matching_category_hint="",
                rationale="Incorrect reject.",
            ),
            "category fit",
        ),
        (
            "level2_metric",
            _level2_example(category_name="pothole"),
            dspy.Prediction(
                category_name="damaged_road",
                rationale="Collapsed into generic road damage.",
            ),
            "pothole",
        ),
    ],
)
def test_metric_wrappers_still_return_plain_score_for_normal_calls(
    metric_name,
    example,
    prediction,
    expected_phrase,
):
    metrics = _load_metrics_module()

    result = getattr(metrics, metric_name)(example, prediction)

    assert isinstance(result, float)
    assert expected_phrase not in str(result)


@pytest.mark.parametrize(
    ("metric_name", "score_fn_name", "example", "prediction", "pred_name", "expected_phrase"),
    [
        (
            "level1_metric",
            "score_level1_prediction",
            _level1_example(decision="IN_SCOPE", category_name="damaged_road_sign"),
            dspy.Prediction(
                decision="REJECT",
                best_matching_category_hint="",
                rationale="Incorrect reject.",
            ),
            "level1_scope_classifier.predict",
            "category fit",
        ),
        (
            "level2_metric",
            "score_level2_prediction",
            _level2_example(category_name="pothole"),
            dspy.Prediction(
                category_name="damaged_road",
                rationale="Collapsed into generic road damage.",
            ),
            "level2_category_classifier.predict",
            "macro recall",
        ),
    ],
)
def test_metric_wrappers_support_gepa_feedback_call_shape(
    metric_name,
    score_fn_name,
    example,
    prediction,
    pred_name,
    expected_phrase,
):
    metrics = _load_metrics_module()
    score_result = getattr(metrics, score_fn_name)(example, prediction)

    result = getattr(metrics, metric_name)(
        example,
        prediction,
        trace=[("program", {}, prediction)],
        pred_name=pred_name,
        pred_trace=[("predictor", {}, prediction)],
    )

    assert isinstance(result, dspy.Prediction)
    assert float(result) == score_result.score
    assert expected_phrase in result.feedback.lower()


def test_level2_metric_fails_fast_when_prediction_category_is_outside_active_subset():
    metrics = _load_metrics_module()

    example = dspy.Example(
        image="unused",
        category_catalog="pothole",
        category_name="pothole",
    ).with_inputs("image", "category_catalog")
    prediction = dspy.Prediction(
        category_name="garbage_litter",
        rationale="Wrong category outside active subset.",
    )

    with pytest.raises(ValueError, match="active category subset"):
        metrics.score_level2_prediction(example, prediction)

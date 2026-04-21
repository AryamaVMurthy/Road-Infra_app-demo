"""Inspectible metrics for the DSPy intake classification stages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from dspy import Prediction

from tools.dspy_intake.signatures import (
    LEVEL1_ALLOWED_DECISIONS,
    LEVEL2_ALLOWED_CATEGORIES,
)


@dataclass(frozen=True, slots=True)
class MetricResult:
    score: float
    feedback: str


def _read_field(value: object, field_name: str) -> object:
    if hasattr(value, field_name):
        return getattr(value, field_name)
    raise ValueError(
        f"DSPy metric input is missing required field `{field_name}`."
    )


def _normalize_decision(value: object, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(
            f"DSPy metric field `{field_name}` must be a string, got {value!r}."
        )
    normalized_value = value.strip()
    if normalized_value not in LEVEL1_ALLOWED_DECISIONS:
        raise ValueError(
            f"DSPy metric field `{field_name}` must be one of {LEVEL1_ALLOWED_DECISIONS}, "
            f"got {normalized_value!r}."
        )
    return normalized_value


def _normalize_category(value: object, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(
            f"DSPy metric field `{field_name}` must be a string, got {value!r}."
        )
    normalized_value = value.strip()
    if normalized_value not in LEVEL2_ALLOWED_CATEGORIES:
        raise ValueError(
            f"DSPy metric field `{field_name}` must be one of {LEVEL2_ALLOWED_CATEGORIES}, "
            f"got {normalized_value!r}."
        )
    return normalized_value


def _normalize_optional_hint(value: object, *, field_name: str) -> str:
    if value is None:
        return ""
    if value == "":
        return ""
    return _normalize_category(value, field_name=field_name)


def _parse_catalog_names(category_catalog: object) -> tuple[str, ...]:
    if isinstance(category_catalog, str):
        normalized_catalog = category_catalog.strip()
        if not normalized_catalog:
            raise ValueError("DSPy metric `category_catalog` must not be empty.")
        if "\n" in normalized_catalog or "\r" in normalized_catalog:
            raw_names = normalized_catalog.splitlines()
        elif "|" in normalized_catalog and ":" not in normalized_catalog:
            raw_names = normalized_catalog.split("|")
        else:
            raw_names = normalized_catalog.splitlines()
        names = []
        for raw_name in raw_names:
            line = raw_name.strip()
            if not line:
                continue
            if ":" in line:
                candidate = line.split(":", 1)[0].strip()
                if candidate:
                    names.append(candidate)
                continue
            if line in LEVEL2_ALLOWED_CATEGORIES:
                names.append(line)
        return _validate_allowed_categories(tuple(names), field_name="category_catalog")

    if isinstance(category_catalog, Mapping):
        return _validate_allowed_categories(
            tuple(sorted(str(name).strip() for name in category_catalog if str(name).strip())),
            field_name="category_catalog",
        )

    if isinstance(category_catalog, Iterable):
        return _validate_allowed_categories(
            tuple(str(item).strip() for item in category_catalog if str(item).strip()),
            field_name="category_catalog",
        )

    raise ValueError(
        "DSPy metric `category_catalog` must be a non-empty string, iterable, or mapping."
    )


def _validate_allowed_categories(
    allowed_categories: tuple[str, ...],
    *,
    field_name: str,
) -> tuple[str, ...]:
    if not allowed_categories:
        raise ValueError(f"DSPy metric `{field_name}` must contain at least one category.")
    invalid_categories = [
        category for category in allowed_categories if category not in LEVEL2_ALLOWED_CATEGORIES
    ]
    if invalid_categories:
        raise ValueError(
            f"DSPy metric `{field_name}` contains unsupported categories "
            f"{invalid_categories!r}; allowed categories are {LEVEL2_ALLOWED_CATEGORIES}."
        )
    return allowed_categories


def score_level1_prediction(example: object, prediction: object) -> MetricResult:
    allowed_categories = _parse_catalog_names(_read_field(example, "category_catalog"))
    expected_decision = _normalize_decision(
        _read_field(example, "decision"),
        field_name="decision",
    )
    predicted_decision = _normalize_decision(
        _read_field(prediction, "decision"),
        field_name="decision",
    )
    category_name_raw = _read_field(example, "category_name")
    predicted_hint = _normalize_optional_hint(
        _read_field(prediction, "best_matching_category_hint"),
        field_name="best_matching_category_hint",
    )
    if expected_decision == "REJECT" and category_name_raw is not None:
        raise ValueError(
            "DSPy metric gold `category_name` must be null when decision is `REJECT`."
        )
    if predicted_hint and predicted_hint not in allowed_categories:
        raise ValueError(
            "DSPy metric prediction `best_matching_category_hint` must be empty or one of "
            f"{allowed_categories}, got {predicted_hint!r}."
        )
    if predicted_decision == "REJECT" and predicted_hint:
        raise ValueError(
            "DSPy metric prediction `best_matching_category_hint` must be empty when "
            "decision is `REJECT`."
        )

    if expected_decision == predicted_decision == "IN_SCOPE":
        expected_category = _normalize_category(
            category_name_raw,
            field_name="category_name",
        )
        if expected_category not in allowed_categories:
            raise ValueError(
                "DSPy metric gold `category_name` must be one of the active category subset "
                f"{allowed_categories}, got {expected_category!r}."
            )
        if predicted_hint == expected_category:
            return MetricResult(
                score=1.0,
                feedback=(
                    f"Correct in-scope decision. The image has category fit for "
                    f"`{expected_category}` and the hint matches."
                ),
            )
        if not predicted_hint:
            return MetricResult(
                score=0.75,
                feedback=(
                    f"Correct in-scope decision, but the image has category fit for "
                    f"`{expected_category}` and the hint was omitted."
                ),
            )
        return MetricResult(
            score=0.35,
            feedback=(
                f"Correct in-scope decision, but the image has category fit for "
                f"`{expected_category}` while the hint incorrectly suggests "
                f"`{predicted_hint}`."
            ),
        )

    if expected_decision == predicted_decision == "REJECT":
        return MetricResult(
            score=1.0,
            feedback="Correct reject. The image is out-of-scope for the allowed catalog.",
        )

    if expected_decision == "IN_SCOPE":
        expected_category = _normalize_category(
            category_name_raw,
            field_name="category_name",
        )
        if expected_category not in allowed_categories:
            raise ValueError(
                "DSPy metric gold `category_name` must be one of the active category subset "
                f"{allowed_categories}, got {expected_category!r}."
            )
        return MetricResult(
            score=-1.0,
            feedback=(
                f"False reject. This image has category fit for `{expected_category}` and should "
                "not be marked out-of-scope."
            ),
        )

    return MetricResult(
        score=-0.35,
        feedback=(
            "False accept. This image should remain out-of-scope instead of being routed into "
            "a catalog category."
        ),
    )


def _wrap_metric_result(
    result: MetricResult,
    *,
    pred_name: str | None,
    pred_trace,
) -> float | Prediction:
    if pred_name is None and pred_trace is None:
        return result.score
    return Prediction(score=result.score, feedback=result.feedback)


def level1_metric(
    gold: object,
    pred: object,
    trace=None,
    pred_name: str | None = None,
    pred_trace=None,
) -> float | Prediction:
    del trace
    return _wrap_metric_result(
        score_level1_prediction(gold, pred),
        pred_name=pred_name,
        pred_trace=pred_trace,
    )


def score_level2_prediction(example: object, prediction: object) -> MetricResult:
    allowed_categories = _parse_catalog_names(_read_field(example, "category_catalog"))
    expected_category = _normalize_category(
        _read_field(example, "category_name"),
        field_name="category_name",
    )
    predicted_category = _normalize_category(
        _read_field(prediction, "category_name"),
        field_name="category_name",
    )
    if expected_category not in allowed_categories:
        raise ValueError(
            "DSPy metric gold `category_name` must be one of the active category subset "
            f"{allowed_categories}, got {expected_category!r}."
        )
    if predicted_category not in allowed_categories:
        raise ValueError(
            "DSPy metric prediction `category_name` must be one of the active category subset "
            f"{allowed_categories}, got {predicted_category!r}."
        )

    if expected_category == predicted_category:
        return MetricResult(
            score=1.0,
            feedback=f"Correct category fit for `{expected_category}`.",
        )

    if expected_category == "damaged_road" and predicted_category == "pothole":
        return MetricResult(
            score=-1.0,
            feedback=(
                "Severe category-fit error. Expected `damaged_road`, not `pothole`. "
                "A pothole requires a discrete cavity or open hole in the road surface; "
                "general cracking, erosion, or broken pavement without that discrete cavity "
                "belongs to `damaged_road`. This kind of collapse harms macro recall."
            ),
        )

    if expected_category == "pothole" and predicted_category == "damaged_road":
        return MetricResult(
            score=-1.0,
            feedback=(
                "Severe category-fit error. Expected `pothole`, not `damaged_road`. "
                "When the image shows a discrete cavity or open hole in the pavement, "
                "it must stay in `pothole` instead of being collapsed into generic road damage. "
                "This kind of collapse harms macro recall."
            ),
        )

    if expected_category == "garbage_litter" and predicted_category in {
        "pothole",
        "damaged_road",
    }:
        return MetricResult(
            score=-1.0,
            feedback=(
                "Severe category-fit error. Expected `garbage_litter`, not "
                f"`{predicted_category}`. Visible trash or litter in the scene should remain "
                "a waste category; do not collapse trash, dumped bags, or scattered litter into "
                "road surface damage. This kind of collapse harms macro recall."
            ),
        )

    severe_collapse_targets = {"pothole", "damaged_road"}
    if predicted_category in severe_collapse_targets and predicted_category != expected_category:
        return MetricResult(
            score=-1.0,
            feedback=(
                "Severe category-fit error. Do not collapse other issue categories into "
                "`pothole` or `damaged_road`; this harms macro recall for critical surface defects."
            ),
        )

    return MetricResult(
        score=-0.4,
        feedback=(
            f"Wrong category fit. Expected `{expected_category}` but predicted "
            f"`{predicted_category}`."
        ),
    )


def level2_metric(
    gold: object,
    pred: object,
    trace=None,
    pred_name: str | None = None,
    pred_trace=None,
) -> float | Prediction:
    del trace
    return _wrap_metric_result(
        score_level2_prediction(gold, pred),
        pred_name=pred_name,
        pred_trace=pred_trace,
    )

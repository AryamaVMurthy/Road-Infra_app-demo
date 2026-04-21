"""Minimal DSPy modules for two-stage intake classification."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

import dspy

from tools.dspy_intake.signatures import (
    LEVEL1_ALLOWED_DECISIONS,
    LEVEL2_ALLOWED_CATEGORIES,
    Level1ScopeSignature,
    Level2CategorySignature,
)

LEVEL1_DECISION_ALIASES = {
    "OUT_OF_SCOPE": "REJECT",
}


@dataclass(frozen=True, slots=True)
class CategoryCatalogPayload:
    prompt_text: str
    allowed_categories: tuple[str, ...]
    forward_value: str | tuple[str, ...] | dict[str, str]


def _read_attr(value: object, field_name: str) -> object:
    if hasattr(value, field_name):
        return getattr(value, field_name)
    raise ValueError(
        f"DSPy intake predictor output is missing required field `{field_name}`."
    )


def _normalize_required_string(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"DSPy intake field `{field_name}` must be a non-empty string, got {value!r}."
        )
    return value.strip()


def _normalize_optional_string(value: object, *, field_name: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(
            f"DSPy intake field `{field_name}` must be a string when provided, got {value!r}."
        )
    return value.strip()


def _normalize_category_hint(
    value: object,
    *,
    field_name: str,
    allowed_categories: tuple[str, ...],
) -> str:
    hint = _normalize_optional_string(value, field_name=field_name)
    if hint and hint not in allowed_categories:
        raise ValueError(
            f"DSPy intake field `{field_name}` must be empty or one of "
            f"{allowed_categories}, got {hint!r}."
        )
    return hint


def _coerce_image(image: dspy.Image | str | Path) -> dspy.Image:
    if isinstance(image, dspy.Image):
        return image
    if isinstance(image, Path):
        if not image.is_file():
            raise ValueError(
                f"DSPy intake image path `{image}` does not exist or is not a file."
            )
        return dspy.Image(str(image))
    if isinstance(image, str):
        if image.startswith(("http://", "https://", "data:", "gs://")):
            return dspy.Image(image)
        image_path = Path(image)
        if not image_path.is_file():
            raise ValueError(
                f"DSPy intake image path `{image_path}` does not exist or is not a file."
            )
        return dspy.Image(str(image_path))
    raise ValueError(
        f"DSPy intake image must be a dspy.Image or filesystem path, got {type(image).__name__}."
    )


def _parse_catalog_names_from_string(category_catalog: str) -> tuple[str, ...]:
    normalized_catalog = category_catalog.strip()
    if not normalized_catalog:
        return ()

    if "\n" in normalized_catalog or "\r" in normalized_catalog:
        raw_names = normalized_catalog.splitlines()
    elif "|" in normalized_catalog and ":" not in normalized_catalog:
        raw_names = normalized_catalog.split("|")
    else:
        raw_names = normalized_catalog.splitlines()

    names: list[str] = []
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
    return tuple(names)


def _validate_allowed_categories(allowed_categories: tuple[str, ...]) -> tuple[str, ...]:
    if not allowed_categories:
        raise ValueError("DSPy intake category catalog must contain at least one category.")
    invalid_categories = [
        category for category in allowed_categories if category not in LEVEL2_ALLOWED_CATEGORIES
    ]
    if invalid_categories:
        raise ValueError(
            "DSPy intake category catalog contains unsupported categories "
            f"{invalid_categories!r}; allowed categories are {LEVEL2_ALLOWED_CATEGORIES}."
        )
    return allowed_categories


def _format_category_catalog(
    category_catalog: str | Iterable[str] | Mapping[str, str],
) -> CategoryCatalogPayload:
    if isinstance(category_catalog, str):
        normalized_catalog = category_catalog.strip()
        allowed_categories = _parse_catalog_names_from_string(normalized_catalog)
        forward_value: str | tuple[str, ...] | dict[str, str] = normalized_catalog
    elif isinstance(category_catalog, Mapping):
        normalized_mapping = {
            str(name).strip(): str(guidance)
            for name, guidance in sorted(category_catalog.items())
            if str(name).strip()
        }
        normalized_catalog = "\n".join(
            f"{name}: {guidance}"
            for name, guidance in normalized_mapping.items()
        )
        allowed_categories = tuple(normalized_mapping)
        forward_value = normalized_mapping
    else:
        normalized_items = [str(item).strip() for item in category_catalog]
        normalized_catalog = "\n".join(item for item in normalized_items if item)
        allowed_categories = tuple(item for item in normalized_items if item)
        forward_value = allowed_categories

    if not normalized_catalog:
        raise ValueError("DSPy intake category catalog must not be empty.")

    return CategoryCatalogPayload(
        prompt_text=normalized_catalog,
        allowed_categories=_validate_allowed_categories(allowed_categories),
        forward_value=forward_value,
    )


def _normalize_level1_prediction(
    raw_prediction: object,
    allowed_categories: tuple[str, ...],
) -> dspy.Prediction:
    decision = _normalize_required_string(
        _read_attr(raw_prediction, "decision"),
        field_name="decision",
    )
    decision = LEVEL1_DECISION_ALIASES.get(decision, decision)
    if decision not in LEVEL1_ALLOWED_DECISIONS:
        raise ValueError(
            "DSPy Level 1 decision must be one of "
            f"{LEVEL1_ALLOWED_DECISIONS}, got {decision!r}."
        )

    best_matching_category_hint = _normalize_category_hint(
        _read_attr(raw_prediction, "best_matching_category_hint"),
        field_name="best_matching_category_hint",
        allowed_categories=allowed_categories,
    )
    if decision == "REJECT" and best_matching_category_hint:
        raise ValueError(
            "DSPy Level 1 `best_matching_category_hint` must be empty when decision is `REJECT`."
        )

    return dspy.Prediction(
        decision=decision,
        best_matching_category_hint=best_matching_category_hint,
        rationale=_normalize_required_string(
            _read_attr(raw_prediction, "rationale"),
            field_name="rationale",
        ),
    )


def _normalize_level2_prediction(
    raw_prediction: object,
    allowed_categories: tuple[str, ...],
) -> dspy.Prediction:
    category_name = _normalize_required_string(
        _read_attr(raw_prediction, "category_name"),
        field_name="category_name",
    )
    if category_name not in allowed_categories:
        raise ValueError(
            "DSPy Level 2 category must be one of "
            f"{allowed_categories}, got {category_name!r}."
        )

    return dspy.Prediction(
        category_name=category_name,
        rationale=_normalize_required_string(
            _read_attr(raw_prediction, "rationale"),
            field_name="rationale",
        ),
    )


class Level1ScopeClassifier(dspy.Module):
    """DSPy module for intake scope filtering."""

    def __init__(self, predictor=None):
        super().__init__()
        self.predictor = predictor or dspy.Predict(Level1ScopeSignature)

    def forward(
        self,
        *,
        image: dspy.Image | str | Path,
        category_catalog: str | Iterable[str] | Mapping[str, str],
    ) -> dspy.Prediction:
        image_input = _coerce_image(image)
        category_catalog_payload = _format_category_catalog(category_catalog)
        raw_prediction = self.predictor(
            image=image_input,
            category_catalog=category_catalog_payload.prompt_text,
        )
        return _normalize_level1_prediction(
            raw_prediction,
            category_catalog_payload.allowed_categories,
        )


class Level2CategoryClassifier(dspy.Module):
    """DSPy module for category selection after an in-scope decision."""

    def __init__(self, predictor=None):
        super().__init__()
        self.predictor = predictor or dspy.Predict(Level2CategorySignature)

    def forward(
        self,
        *,
        image: dspy.Image | str | Path,
        category_catalog: str | Iterable[str] | Mapping[str, str],
        best_matching_category_hint: str = "",
    ) -> dspy.Prediction:
        image_input = _coerce_image(image)
        category_catalog_payload = _format_category_catalog(category_catalog)
        hint_input = _normalize_category_hint(
            best_matching_category_hint,
            field_name="best_matching_category_hint",
            allowed_categories=category_catalog_payload.allowed_categories,
        )
        raw_prediction = self.predictor(
            image=image_input,
            category_catalog=category_catalog_payload.prompt_text,
            best_matching_category_hint=hint_input,
        )
        return _normalize_level2_prediction(
            raw_prediction,
            category_catalog_payload.allowed_categories,
        )


class TwoStageIntakeClassifier(dspy.Module):
    """Two-stage intake classifier with explicit contract validation between stages."""

    def __init__(self, level1_module=None, level2_module=None):
        super().__init__()
        self.level1_module = level1_module or Level1ScopeClassifier()
        self.level2_module = level2_module or Level2CategoryClassifier()

    def forward(
        self,
        *,
        image: dspy.Image | str | Path,
        category_catalog: str | Iterable[str] | Mapping[str, str],
    ) -> dspy.Prediction:
        image_input = _coerce_image(image)
        category_catalog_payload = _format_category_catalog(category_catalog)

        level1_prediction = _normalize_level1_prediction(
            self.level1_module(
                image=image_input,
                category_catalog=category_catalog_payload.forward_value,
            ),
            category_catalog_payload.allowed_categories,
        )
        if level1_prediction.decision == "REJECT":
            return dspy.Prediction(
                final_decision="REJECTED",
                category_name=None,
                rationale=level1_prediction.rationale,
            )

        level2_prediction = _normalize_level2_prediction(
            self.level2_module(
                image=image_input,
                category_catalog=category_catalog_payload.forward_value,
                best_matching_category_hint=level1_prediction.best_matching_category_hint,
            ),
            category_catalog_payload.allowed_categories,
        )
        return dspy.Prediction(
            final_decision="ACCEPTED_CATEGORY_MATCH",
            category_name=level2_prediction.category_name,
            rationale=level2_prediction.rationale,
        )

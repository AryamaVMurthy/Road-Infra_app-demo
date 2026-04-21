"""DSPy intake package exports with lazy runtime-safe imports."""

from __future__ import annotations

from .constants import (
    LEVEL1_NEGATIVE_LABEL,
    LEVEL1_POSITIVE_LABEL,
    LEVEL2_ALLOWED_LABELS,
)

__all__ = [
    "LEVEL1_NEGATIVE_LABEL",
    "LEVEL1_POSITIVE_LABEL",
    "LEVEL2_ALLOWED_LABELS",
    "export_dspy_datasets",
]


def export_dspy_datasets(*args, **kwargs):
    from .export_datasets import export_dspy_datasets as _impl

    return _impl(*args, **kwargs)

"""DSPy signatures for two-stage intake classification."""

from __future__ import annotations

import dspy

from tools.dspy_intake.constants import LEVEL2_ALLOWED_LABELS


LEVEL1_ALLOWED_DECISIONS = ("IN_SCOPE", "REJECT")
LEVEL2_ALLOWED_CATEGORIES = tuple(LEVEL2_ALLOWED_LABELS)


class Level1ScopeSignature(dspy.Signature):
    """Decide whether an intake image is in scope for the known issue catalog."""

    image: dspy.Image = dspy.InputField(desc="Citizen intake image to review.")
    category_catalog: str = dspy.InputField(
        desc=(
            "Canonical category catalog with category names and guidance for valid "
            "road-infrastructure issues."
        )
    )
    decision: str = dspy.OutputField(desc="One of IN_SCOPE or REJECT.")
    best_matching_category_hint: str = dspy.OutputField(
        desc=(
            "Optional best matching category hint when the image appears in scope. "
            "Return an empty string when no hint is appropriate."
        )
    )
    rationale: str = dspy.OutputField(
        desc="Brief explanation tied to category fit or out-of-scope status."
    )


class Level2CategorySignature(dspy.Signature):
    """Choose the backend category for an in-scope intake image."""

    image: dspy.Image = dspy.InputField(desc="Citizen intake image already judged in scope.")
    category_catalog: str = dspy.InputField(
        desc=(
            "Canonical category catalog with category names and guidance for valid "
            "road-infrastructure issues."
        )
    )
    best_matching_category_hint: str = dspy.InputField(
        desc="Optional Level 1 hint for the strongest candidate category."
    )
    category_name: str = dspy.OutputField(
        desc=f"One of {', '.join(LEVEL2_ALLOWED_CATEGORIES)}."
    )
    rationale: str = dspy.OutputField(
        desc="Brief explanation for the chosen backend category."
    )

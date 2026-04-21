from pathlib import Path
import sys
import warnings

import dspy
from PIL import Image
import pytest


sys.path.append(str(Path(__file__).resolve().parents[2]))


def _load_programs_module():
    import importlib.util

    spec = importlib.util.find_spec("tools.dspy_intake.programs")
    assert spec is not None, "Expected tools.dspy_intake.programs to exist for the DSPy intake slice."
    return __import__("tools.dspy_intake.programs", fromlist=["placeholder"])


def _write_test_image(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), color=(220, 40, 40)).save(path, format="JPEG")
    return path


class StubModule:
    def __init__(self, prediction):
        self.prediction = prediction
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return self.prediction


@pytest.mark.parametrize(
    ("decision", "hint"),
    [
        ("IN_SCOPE", "pothole"),
        ("REJECT", ""),
    ],
)
def test_level1_program_parses_only_expected_decisions(tmp_path: Path, decision: str, hint: str):
    programs = _load_programs_module()
    image_path = _write_test_image(tmp_path / "sample.jpg")
    seen = {}

    def stub_predictor(*, image, category_catalog):
        seen["image"] = image
        seen["category_catalog"] = category_catalog
        return dspy.Prediction(
            decision=decision,
            best_matching_category_hint=hint,
            rationale=f"stub rationale for {decision}",
        )

    program = programs.Level1ScopeClassifier(predictor=stub_predictor)
    result = program(
        image=image_path,
        category_catalog=["pothole", "damaged_road", "damaged_road_sign", "garbage_litter"],
    )

    assert isinstance(seen["image"], dspy.Image)
    assert "pothole" in seen["category_catalog"]
    assert result.decision == decision
    assert result.best_matching_category_hint == hint
    assert result.rationale == f"stub rationale for {decision}"


def test_level1_program_coerces_path_without_deprecation_warning(tmp_path: Path):
    programs = _load_programs_module()
    image_path = _write_test_image(tmp_path / "sample.jpg")
    program = programs.Level1ScopeClassifier(
        predictor=lambda **kwargs: dspy.Prediction(
            decision="IN_SCOPE",
            best_matching_category_hint="pothole",
            rationale="Valid in-scope image.",
        )
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = program(
            image=image_path,
            category_catalog=["pothole", "damaged_road", "damaged_road_sign", "garbage_litter"],
        )

    assert result.decision == "IN_SCOPE"
    assert not [warning for warning in caught if issubclass(warning.category, DeprecationWarning)]


def test_level1_program_accepts_gs_image_urls_without_treating_them_as_local_paths():
    programs = _load_programs_module()
    seen = {}

    def stub_predictor(*, image, category_catalog):
        seen["image"] = image
        seen["category_catalog"] = category_catalog
        return dspy.Prediction(
            decision="IN_SCOPE",
            best_matching_category_hint="pothole",
            rationale="Valid in-scope image.",
        )

    program = programs.Level1ScopeClassifier(predictor=stub_predictor)
    result = program(
        image="gs://bucket/object.jpg",
        category_catalog=["pothole", "damaged_road", "damaged_road_sign", "garbage_litter"],
    )

    assert result.decision == "IN_SCOPE"
    assert isinstance(seen["image"], dspy.Image)
    assert seen["image"].url == "gs://bucket/object.jpg"


def test_level1_program_fails_fast_when_image_path_is_missing(tmp_path: Path):
    programs = _load_programs_module()
    missing_path = tmp_path / "missing.jpg"
    program = programs.Level1ScopeClassifier(
        predictor=lambda **kwargs: dspy.Prediction(
            decision="IN_SCOPE",
            best_matching_category_hint="pothole",
            rationale="Should never run.",
        )
    )

    with pytest.raises(ValueError, match="does not exist"):
        program(
            image=missing_path,
            category_catalog=["pothole", "damaged_road", "damaged_road_sign", "garbage_litter"],
        )


def test_level1_program_rejects_non_empty_hint_for_reject_decision(tmp_path: Path):
    programs = _load_programs_module()
    image_path = _write_test_image(tmp_path / "sample.jpg")
    program = programs.Level1ScopeClassifier(
        predictor=lambda **kwargs: dspy.Prediction(
            decision="REJECT",
            best_matching_category_hint="pothole",
            rationale="Out-of-scope content.",
        )
    )

    with pytest.raises(ValueError, match="best_matching_category_hint.*REJECT"):
        program(
            image=image_path,
            category_catalog=["pothole", "damaged_road", "damaged_road_sign", "garbage_litter"],
        )


def test_level1_program_normalizes_out_of_scope_alias_to_reject(tmp_path: Path):
    programs = _load_programs_module()
    image_path = _write_test_image(tmp_path / "sample.jpg")
    program = programs.Level1ScopeClassifier(
        predictor=lambda **kwargs: dspy.Prediction(
            decision="OUT_OF_SCOPE",
            best_matching_category_hint="",
            rationale="The image does not match any allowed category.",
        )
    )

    result = program(
        image=image_path,
        category_catalog=["pothole", "damaged_road", "damaged_road_sign", "garbage_litter"],
    )

    assert result.decision == "REJECT"
    assert result.best_matching_category_hint == ""


def test_level1_program_rejects_unsupported_non_empty_hint(tmp_path: Path):
    programs = _load_programs_module()
    image_path = _write_test_image(tmp_path / "sample.jpg")
    program = programs.Level1ScopeClassifier(
        predictor=lambda **kwargs: dspy.Prediction(
            decision="IN_SCOPE",
            best_matching_category_hint="sinkhole",
            rationale="In-scope road defect.",
        )
    )

    with pytest.raises(ValueError, match="best_matching_category_hint"):
        program(
            image=image_path,
            category_catalog=["pothole", "damaged_road", "damaged_road_sign", "garbage_litter"],
        )


def test_level1_program_rejects_hint_outside_caller_supplied_category_subset(tmp_path: Path):
    programs = _load_programs_module()
    image_path = _write_test_image(tmp_path / "sample.jpg")
    program = programs.Level1ScopeClassifier(
        predictor=lambda **kwargs: dspy.Prediction(
            decision="IN_SCOPE",
            best_matching_category_hint="garbage_litter",
            rationale="In-scope road defect.",
        )
    )

    with pytest.raises(ValueError, match="best_matching_category_hint"):
        program(
            image=image_path,
            category_catalog=["pothole"],
        )


@pytest.mark.parametrize("invalid_hint", [[], {}, 3])
def test_level1_program_rejects_invalid_hint_types_with_explicit_value_error(
    tmp_path: Path,
    invalid_hint,
):
    programs = _load_programs_module()
    image_path = _write_test_image(tmp_path / "sample.jpg")
    program = programs.Level1ScopeClassifier(
        predictor=lambda **kwargs: dspy.Prediction(
            decision="IN_SCOPE",
            best_matching_category_hint=invalid_hint,
            rationale="In-scope road defect.",
        )
    )

    with pytest.raises(ValueError, match="best_matching_category_hint"):
        program(
            image=image_path,
            category_catalog=["pothole", "damaged_road", "damaged_road_sign", "garbage_litter"],
        )


def test_level2_program_only_accepts_allowed_category_names(tmp_path: Path):
    programs = _load_programs_module()
    assert hasattr(
        programs,
        "Level2CategoryClassifier",
    ), "Expected Level2CategoryClassifier to exist for the DSPy Level 2 slice."

    image_path = _write_test_image(tmp_path / "sample.jpg")
    valid_program = programs.Level2CategoryClassifier(
        predictor=lambda **kwargs: dspy.Prediction(
            category_name="garbage_litter",
            rationale="Visible roadside garbage.",
        )
    )

    valid_result = valid_program(
        image=image_path,
        category_catalog=["pothole", "damaged_road", "damaged_road_sign", "garbage_litter"],
        best_matching_category_hint="garbage_litter",
    )

    assert valid_result.category_name == "garbage_litter"

    invalid_program = programs.Level2CategoryClassifier(
        predictor=lambda **kwargs: dspy.Prediction(
            category_name="sinkhole",
            rationale="Unsupported label.",
        )
    )

    with pytest.raises(ValueError, match="Level 2 category"):
        invalid_program(
            image=image_path,
            category_catalog=["pothole", "damaged_road", "damaged_road_sign", "garbage_litter"],
            best_matching_category_hint="pothole",
        )


def test_level2_program_rejects_unsupported_non_empty_hint_from_direct_callers(tmp_path: Path):
    programs = _load_programs_module()
    image_path = _write_test_image(tmp_path / "sample.jpg")
    program = programs.Level2CategoryClassifier(
        predictor=lambda **kwargs: dspy.Prediction(
            category_name="pothole",
            rationale="Visible pothole damage.",
        )
    )

    with pytest.raises(ValueError, match="best_matching_category_hint"):
        program(
            image=image_path,
            category_catalog=["pothole", "damaged_road", "damaged_road_sign", "garbage_litter"],
            best_matching_category_hint="sinkhole",
        )


def test_level2_program_rejects_category_outside_caller_supplied_category_subset(tmp_path: Path):
    programs = _load_programs_module()
    image_path = _write_test_image(tmp_path / "sample.jpg")
    program = programs.Level2CategoryClassifier(
        predictor=lambda **kwargs: dspy.Prediction(
            category_name="garbage_litter",
            rationale="Visible roadside garbage.",
        )
    )

    with pytest.raises(ValueError, match="Level 2 category"):
        program(
            image=image_path,
            category_catalog=["pothole"],
            best_matching_category_hint="pothole",
        )


def test_two_stage_program_returns_rejected_without_running_level2(tmp_path: Path):
    programs = _load_programs_module()
    assert hasattr(
        programs,
        "TwoStageIntakeClassifier",
    ), "Expected TwoStageIntakeClassifier to exist for the DSPy two-stage slice."

    image_path = _write_test_image(tmp_path / "sample.jpg")
    level1 = StubModule(
        dspy.Prediction(
            decision="REJECT",
            best_matching_category_hint="",
            rationale="Out-of-scope content.",
        )
    )
    level2 = StubModule(
        dspy.Prediction(
            category_name="pothole",
            rationale="Should never be used.",
        )
    )

    program = programs.TwoStageIntakeClassifier(level1_module=level1, level2_module=level2)
    result = program(
        image=image_path,
        category_catalog=["pothole", "damaged_road", "damaged_road_sign", "garbage_litter"],
    )

    assert result.final_decision == "REJECTED"
    assert result.category_name is None
    assert result.rationale == "Out-of-scope content."
    assert level2.calls == []


def test_two_stage_program_returns_accepted_category_match_when_level1_is_in_scope(
    tmp_path: Path,
):
    programs = _load_programs_module()
    image_path = _write_test_image(tmp_path / "sample.jpg")
    level1 = StubModule(
        dspy.Prediction(
            decision="IN_SCOPE",
            best_matching_category_hint="pothole",
            rationale="Road damage is in scope.",
        )
    )
    level2 = StubModule(
        dspy.Prediction(
            category_name="pothole",
            rationale="The image most closely matches pothole damage.",
        )
    )

    program = programs.TwoStageIntakeClassifier(level1_module=level1, level2_module=level2)
    result = program(
        image=image_path,
        category_catalog=["pothole", "damaged_road", "damaged_road_sign", "garbage_litter"],
    )

    assert result.final_decision == "ACCEPTED_CATEGORY_MATCH"
    assert result.category_name == "pothole"
    assert result.rationale == "The image most closely matches pothole damage."
    assert level2.calls[0]["best_matching_category_hint"] == "pothole"


def test_two_stage_program_preserves_mapping_catalogs_with_multiline_guidance(
    tmp_path: Path,
):
    programs = _load_programs_module()
    image_path = _write_test_image(tmp_path / "sample.jpg")
    level1 = StubModule(
        dspy.Prediction(
            decision="IN_SCOPE",
            best_matching_category_hint="pothole",
            rationale="Road damage is in scope.",
        )
    )
    level2 = StubModule(
        dspy.Prediction(
            category_name="pothole",
            rationale="The image most closely matches pothole damage.",
        )
    )
    category_catalog = {
        "pothole": "Broken or missing surface.\nVisible hole in the carriageway.",
        "damaged_road": "Road cracks or surface breakup.",
    }

    program = programs.TwoStageIntakeClassifier(level1_module=level1, level2_module=level2)
    result = program(
        image=image_path,
        category_catalog=category_catalog,
    )

    assert result.final_decision == "ACCEPTED_CATEGORY_MATCH"
    assert result.category_name == "pothole"
    assert level1.calls[0]["category_catalog"] == category_catalog
    assert level2.calls[0]["category_catalog"] == category_catalog


def test_level1_program_accepts_multiline_string_catalog_guidance(tmp_path: Path):
    programs = _load_programs_module()
    image_path = _write_test_image(tmp_path / "sample.jpg")
    program = programs.Level1ScopeClassifier(
        predictor=lambda **kwargs: dspy.Prediction(
            decision="IN_SCOPE",
            best_matching_category_hint="pothole",
            rationale="Road damage is in scope.",
        )
    )
    category_catalog = (
        "pothole: Broken or missing surface.\n"
        "Visible hole in the carriageway.\n"
        "damaged_road: Road cracks or surface breakup."
    )

    result = program(
        image=image_path,
        category_catalog=category_catalog,
    )

    assert result.decision == "IN_SCOPE"
    assert result.best_matching_category_hint == "pothole"


def test_level1_program_accepts_multiline_guidance_with_pipe_characters(tmp_path: Path):
    programs = _load_programs_module()
    image_path = _write_test_image(tmp_path / "sample.jpg")
    program = programs.Level1ScopeClassifier(
        predictor=lambda **kwargs: dspy.Prediction(
            decision="IN_SCOPE",
            best_matching_category_hint="pothole",
            rationale="Road damage is in scope.",
        )
    )
    category_catalog = (
        "pothole: Broken | missing surface.\n"
        "damaged_road: Road cracks or surface breakup."
    )

    result = program(
        image=image_path,
        category_catalog=category_catalog,
    )

    assert result.decision == "IN_SCOPE"
    assert result.best_matching_category_hint == "pothole"


def test_two_stage_program_supports_one_shot_iterable_catalogs(tmp_path: Path):
    programs = _load_programs_module()
    image_path = _write_test_image(tmp_path / "sample.jpg")
    level1 = StubModule(
        dspy.Prediction(
            decision="IN_SCOPE",
            best_matching_category_hint="pothole",
            rationale="Road damage is in scope.",
        )
    )
    level2 = StubModule(
        dspy.Prediction(
            category_name="pothole",
            rationale="The image most closely matches pothole damage.",
        )
    )

    program = programs.TwoStageIntakeClassifier(level1_module=level1, level2_module=level2)
    result = program(
        image=image_path,
        category_catalog=(label for label in ("pothole", "damaged_road")),
    )

    assert result.final_decision == "ACCEPTED_CATEGORY_MATCH"
    assert level1.calls[0]["category_catalog"] == ("pothole", "damaged_road")
    assert level2.calls[0]["category_catalog"] == ("pothole", "damaged_road")


def test_two_stage_program_fails_fast_on_invalid_level1_decision(tmp_path: Path):
    programs = _load_programs_module()
    image_path = _write_test_image(tmp_path / "sample.jpg")

    program = programs.TwoStageIntakeClassifier(
        level1_module=StubModule(
            dspy.Prediction(
                decision="UNSURE",
                best_matching_category_hint="",
                rationale="Not a valid contract value.",
            )
        ),
        level2_module=StubModule(
            dspy.Prediction(
                category_name="pothole",
                rationale="Should not run.",
            )
        ),
    )

    with pytest.raises(ValueError, match="Level 1 decision"):
        program(
            image=image_path,
            category_catalog=["pothole", "damaged_road", "damaged_road_sign", "garbage_litter"],
        )


def test_two_stage_program_fails_fast_on_invalid_level2_category(tmp_path: Path):
    programs = _load_programs_module()
    image_path = _write_test_image(tmp_path / "sample.jpg")

    program = programs.TwoStageIntakeClassifier(
        level1_module=StubModule(
            dspy.Prediction(
                decision="IN_SCOPE",
                best_matching_category_hint="damaged_road",
                rationale="This is a valid in-scope image.",
            )
        ),
        level2_module=StubModule(
            dspy.Prediction(
                category_name="sinkhole",
                rationale="Not a supported backend category.",
            )
        ),
    )

    with pytest.raises(ValueError, match="Level 2 category"):
        program(
            image=image_path,
            category_catalog=["pothole", "damaged_road", "damaged_road_sign", "garbage_litter"],
        )

import csv
import json
from pathlib import Path
import sys

import dspy
from PIL import Image
import pytest


sys.path.append(str(Path(__file__).resolve().parents[2]))


def _load_evaluation_module():
    import importlib.util

    spec = importlib.util.find_spec("tools.dspy_intake.evaluate_two_stage")
    assert spec is not None, "Expected tools.dspy_intake.evaluate_two_stage to exist for the evaluation slice."
    return __import__("tools.dspy_intake.evaluate_two_stage", fromlist=["placeholder"])


def _write_image(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (16, 16), color=color).save(path, format="JPEG")


def _write_test_export(path: Path, dataset_root: Path) -> None:
    rows = [
        {
            "label": "in_scope_category_image",
            "relative_image_path": "images/test/pothole/pothole_1.jpg",
            "sample_id": "pothole_1",
            "split": "test",
            "subgroup": "accepted/pothole",
        },
        {
            "label": "in_scope_category_image",
            "relative_image_path": "images/test/damaged_road/damaged_road_1.jpg",
            "sample_id": "damaged_road_1",
            "split": "test",
            "subgroup": "accepted/damaged_road",
        },
        {
            "label": "spoof_or_out_of_scope",
            "relative_image_path": "images/test/rejected_real_irrelevant/real_1.jpg",
            "sample_id": "real_1",
            "split": "test",
            "subgroup": "rejected_real_irrelevant",
        },
        {
            "label": "spoof_or_out_of_scope",
            "relative_image_path": "images/test/rejected_synthetic_spoof/spoof_1.jpg",
            "sample_id": "spoof_1",
            "split": "test",
            "subgroup": "rejected_synthetic_spoof",
        },
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for index, row in enumerate(rows, start=1):
            _write_image(
                dataset_root / str(row["relative_image_path"]),
                color=(index * 30, 80, 140),
            )
            handle.write(json.dumps(row) + "\n")


class StubLevel1Program:
    def __init__(self):
        self.calls = []

    def __call__(self, *, image, category_catalog):
        image_name = Path(image).name
        self.calls.append(image_name)
        if image_name.startswith("pothole"):
            return dspy.Prediction(
                decision="IN_SCOPE",
                best_matching_category_hint="pothole",
                rationale="In-scope pothole.",
            )
        if image_name.startswith("damaged_road"):
            return dspy.Prediction(
                decision="IN_SCOPE",
                best_matching_category_hint="damaged_road",
                rationale="In-scope road damage.",
            )
        return dspy.Prediction(
            decision="REJECT",
            best_matching_category_hint="",
            rationale="Out of scope.",
        )


class StubLevel2Program:
    def __init__(self, expected_hint: str | None = None, category_name: str = "garbage_litter", rationale: str = "Incorrect collapse into garbage."):
        self.expected_hint = expected_hint
        self.category_name = category_name
        self.rationale = rationale

    def __call__(self, *, image, category_catalog, best_matching_category_hint=""):
        if self.expected_hint is not None:
            assert best_matching_category_hint == self.expected_hint
        image_name = Path(image).name
        if image_name.startswith("pothole"):
            return dspy.Prediction(
                category_name="pothole",
                rationale="Correct pothole category.",
            )
        return dspy.Prediction(
            category_name=self.category_name,
            rationale=self.rationale,
        )


class UngatedLevel1Program:
    def __call__(self, *, image, category_catalog):
        image_name = Path(image).name
        if image_name.startswith("pothole"):
            return dspy.Prediction(
                decision="IN_SCOPE",
                best_matching_category_hint="pothole",
                rationale="In-scope pothole.",
            )
        return dspy.Prediction(
            decision="REJECT",
            best_matching_category_hint="",
            rationale="Incorrect reject for accepted sample.",
        )


class UngatedLevel2Program:
    def __call__(self, *, image, category_catalog, best_matching_category_hint=""):
        image_name = Path(image).name
        if image_name.startswith("pothole"):
            label = "pothole"
        elif image_name.startswith("damaged_road"):
            label = "damaged_road"
        else:
            label = "garbage_litter"
        return dspy.Prediction(
            category_name=label,
            rationale="Ungated level2 prediction.",
        )


def test_evaluator_writes_summary_subgroup_metrics_and_confusion_matrix(tmp_path: Path):
    evaluation = _load_evaluation_module()
    dataset_root = tmp_path / "dataset"
    export_path = tmp_path / "exports" / "level1_test.jsonl"
    _write_test_export(export_path, dataset_root)
    output_root = tmp_path / "reports"

    result = evaluation.evaluate_two_stage(
        dataset_root=dataset_root,
        level1_export_path=export_path,
        output_root=output_root,
        level1_program=StubLevel1Program(),
        level2_program=StubLevel2Program(),
    )

    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert summary["counts"]["total_examples"] == 4
    assert "accepted/pothole" in summary["level1_subgroup_metrics"]
    assert "rejected_real_irrelevant" in summary["level1_subgroup_metrics"]
    assert "pothole" in summary["level2_category_metrics"]
    assert "damaged_road" in summary["level2_category_metrics"]
    assert summary["end_to_end"]["accuracy"] == 0.75

    confusion_rows = list(csv.DictReader(result.confusion_matrix_path.open("r", encoding="utf-8")))
    assert confusion_rows
    assert {row["expected_label"] for row in confusion_rows} >= {
        "REJECT",
        "pothole",
        "damaged_road",
    }

    predictions = [
        json.loads(line)
        for line in result.predictions_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(predictions) == 4
    assert {prediction["predicted_label"] for prediction in predictions} >= {
        "REJECT",
        "pothole",
        "garbage_litter",
    }


def test_evaluator_rejects_non_test_exports_for_held_out_reports(tmp_path: Path):
    evaluation = _load_evaluation_module()
    dataset_root = tmp_path / "dataset"
    export_path = tmp_path / "exports" / "level1_train.jsonl"
    _write_test_export(export_path, dataset_root)
    rows = [json.loads(line) for line in export_path.read_text(encoding="utf-8").splitlines()]
    for row in rows:
        row["split"] = "train"
    export_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="expected split `test`"):
        evaluation.evaluate_two_stage(
            dataset_root=dataset_root,
            level1_export_path=export_path,
            output_root=tmp_path / "reports",
            level1_program=StubLevel1Program(),
            level2_program=StubLevel2Program(),
        )


def test_evaluator_reports_ungated_level2_metrics_separately_from_end_to_end(tmp_path: Path):
    evaluation = _load_evaluation_module()
    dataset_root = tmp_path / "dataset"
    export_path = tmp_path / "exports" / "level1_test.jsonl"
    _write_test_export(export_path, dataset_root)

    result = evaluation.evaluate_two_stage(
        dataset_root=dataset_root,
        level1_export_path=export_path,
        output_root=tmp_path / "reports",
        level1_program=UngatedLevel1Program(),
        level2_program=UngatedLevel2Program(),
    )

    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert summary["end_to_end"]["accuracy"] == 0.75
    assert summary["level2_category_metrics"]["pothole"]["accuracy"] == 1.0
    assert summary["level2_category_metrics"]["damaged_road"]["accuracy"] == 1.0


def test_evaluator_can_disable_level1_hint_for_level2_calls(tmp_path: Path):
    evaluation = _load_evaluation_module()
    dataset_root = tmp_path / "dataset"
    export_path = tmp_path / "exports" / "level1_test.jsonl"
    _write_test_export(export_path, dataset_root)

    result = evaluation.evaluate_two_stage(
        dataset_root=dataset_root,
        level1_export_path=export_path,
        output_root=tmp_path / "reports",
        level1_program=StubLevel1Program(),
        level2_program=StubLevel2Program(expected_hint=""),
        level2_hint_mode="off",
    )

    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert summary["counts"]["total_examples"] == 4


def test_variant_comparison_reports_both_systems_and_selects_the_better_one(tmp_path: Path):
    evaluation = _load_evaluation_module()
    dataset_root = tmp_path / "dataset"
    export_path = tmp_path / "exports" / "level1_test.jsonl"
    _write_test_export(export_path, dataset_root)

    comparison = evaluation.evaluate_two_stage_variants(
        dataset_root=dataset_root,
        level1_export_path=export_path,
        output_root=tmp_path / "reports",
        variants={
            "gepa": {
                "level1_program": StubLevel1Program(),
                "level2_program": StubLevel2Program(),
            },
            "mipro": {
                "level1_program": UngatedLevel1Program(),
                "level2_program": UngatedLevel2Program(),
            },
        },
    )

    summary = json.loads(comparison.comparison_summary_path.read_text(encoding="utf-8"))
    assert set(summary["variants"]) == {"gepa", "mipro"}
    assert summary["selected_variant"] == "mipro"

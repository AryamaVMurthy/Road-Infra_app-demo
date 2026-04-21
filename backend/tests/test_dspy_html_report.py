import json
from pathlib import Path
import sys

from PIL import Image


sys.path.append(str(Path(__file__).resolve().parents[2]))


def _load_report_module():
    import importlib.util

    spec = importlib.util.find_spec("tools.dspy_intake.render_html_report")
    assert spec is not None, "Expected tools.dspy_intake.render_html_report to exist for the HTML report slice."
    return __import__("tools.dspy_intake.render_html_report", fromlist=["placeholder"])


def _write_image(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (24, 24), color=color).save(path, format="JPEG")


def test_html_report_renders_metrics_and_image_cards(tmp_path: Path):
    report = _load_report_module()
    dataset_root = tmp_path / "dataset"
    evaluation_root = tmp_path / "evaluation"
    image_paths = {
        "sample_good": dataset_root / "images/test/pothole/sample_good.jpg",
        "sample_false_reject": dataset_root / "images/test/damaged_road/sample_false_reject.jpg",
        "sample_spoof": dataset_root / "images/test/rejected_synthetic_spoof/sample_spoof.jpg",
    }
    _write_image(image_paths["sample_good"], color=(220, 40, 40))
    _write_image(image_paths["sample_false_reject"], color=(40, 220, 40))
    _write_image(image_paths["sample_spoof"], color=(40, 40, 220))

    summary_path = evaluation_root / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(
            {
                "variant_name": "gepa",
                "counts": {"total_examples": 3, "correct_predictions": 2},
                "end_to_end": {"accuracy": 2 / 3},
                "level1_subgroup_metrics": {
                    "accepted/pothole": {"total": 1, "correct_scope": 1, "accuracy": 1.0},
                    "accepted/damaged_road": {"total": 1, "correct_scope": 0, "accuracy": 0.0},
                    "rejected_synthetic_spoof": {"total": 1, "correct_scope": 1, "accuracy": 1.0},
                },
                "level2_category_metrics": {
                    "pothole": {"total": 1, "correct": 1, "accuracy": 1.0},
                    "damaged_road": {"total": 1, "correct": 0, "accuracy": 0.0},
                },
            }
        ),
        encoding="utf-8",
    )
    predictions_path = evaluation_root / "predictions.jsonl"
    predictions_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "sample_id": "sample_good",
                        "subgroup": "accepted/pothole",
                        "expected_label": "pothole",
                        "predicted_label": "pothole",
                        "level1_decision": "IN_SCOPE",
                        "level1_best_matching_category_hint": "pothole",
                        "ungated_level2_predicted_label": "pothole",
                    }
                ),
                json.dumps(
                    {
                        "sample_id": "sample_false_reject",
                        "subgroup": "accepted/damaged_road",
                        "expected_label": "damaged_road",
                        "predicted_label": "REJECT",
                        "level1_decision": "REJECT",
                        "level1_best_matching_category_hint": "",
                        "ungated_level2_predicted_label": "damaged_road",
                    }
                ),
                json.dumps(
                    {
                        "sample_id": "sample_spoof",
                        "subgroup": "rejected_synthetic_spoof",
                        "expected_label": "REJECT",
                        "predicted_label": "REJECT",
                        "level1_decision": "REJECT",
                        "level1_best_matching_category_hint": "",
                        "ungated_level2_predicted_label": None,
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    manifest_path = dataset_root / "manifests" / "test.jsonl"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "sample_id": "sample_good",
                        "relative_image_path": "images/test/pothole/sample_good.jpg",
                        "canonical_label": "pothole",
                        "intake_outcome": "accepted",
                        "is_spoof": False,
                        "negative_source_type": None,
                        "source_dataset": "roads",
                        "source_label": "Pothole Issues",
                    }
                ),
                json.dumps(
                    {
                        "sample_id": "sample_false_reject",
                        "relative_image_path": "images/test/damaged_road/sample_false_reject.jpg",
                        "canonical_label": "damaged_road",
                        "intake_outcome": "accepted",
                        "is_spoof": False,
                        "negative_source_type": None,
                        "source_dataset": "roads",
                        "source_label": "Damaged Road issues",
                    }
                ),
                json.dumps(
                    {
                        "sample_id": "sample_spoof",
                        "relative_image_path": "images/test/rejected_synthetic_spoof/sample_spoof.jpg",
                        "canonical_label": None,
                        "intake_outcome": "rejected",
                        "is_spoof": True,
                        "negative_source_type": "synthetic_spoof",
                        "source_dataset": "spoof",
                        "source_label": None,
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    output_path = evaluation_root / "report.html"
    rendered_output = report.render_html_report(
        dataset_root=dataset_root,
        summary_path=summary_path,
        predictions_path=predictions_path,
        manifest_path=manifest_path,
        output_path=output_path,
        report_title="DSPy Intake Benchmark Report",
    )

    html = rendered_output.read_text(encoding="utf-8")
    assert "DSPy Intake Benchmark Report" in html
    assert "Spoof / Not-Spoof Gate" in html
    assert "Correct Accepts" in html
    assert "False Rejects" in html
    assert "Correct Rejects" in html
    assert "sample_good" in html
    assert "sample_false_reject" in html
    assert "sample_spoof" in html
    assert "images/test/pothole/sample_good.jpg" in html
    assert "2 / 3" in html
    assert "synthetic_spoof" in html


def test_html_report_flags_summary_metric_mismatches(tmp_path: Path):
    report = _load_report_module()
    dataset_root = tmp_path / "dataset"
    evaluation_root = tmp_path / "evaluation"
    _write_image(dataset_root / "images/test/pothole/sample_ok.jpg", color=(120, 80, 40))

    summary_path = evaluation_root / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(
            {
                "variant_name": "gepa",
                "counts": {"total_examples": 1, "correct_predictions": 1},
                "end_to_end": {"accuracy": 1.0},
                "level1_subgroup_metrics": {
                    "accepted/pothole": {"total": 1, "correct_scope": 0, "accuracy": 0.0}
                },
                "level2_category_metrics": {
                    "pothole": {"total": 1, "correct": 0, "accuracy": 0.0}
                },
            }
        ),
        encoding="utf-8",
    )

    predictions_path = evaluation_root / "predictions.jsonl"
    predictions_path.write_text(
        json.dumps(
            {
                "sample_id": "sample_ok",
                "subgroup": "accepted/pothole",
                "expected_label": "pothole",
                "predicted_label": "pothole",
                "level1_decision": "IN_SCOPE",
                "level1_best_matching_category_hint": "pothole",
                "ungated_level2_predicted_label": "pothole",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    manifest_path = dataset_root / "manifests" / "test.jsonl"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "sample_id": "sample_ok",
                "relative_image_path": "images/test/pothole/sample_ok.jpg",
                "canonical_label": "pothole",
                "intake_outcome": "accepted",
                "is_spoof": False,
                "negative_source_type": None,
                "source_dataset": "roads",
                "source_label": "Pothole Issues",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    output_path = evaluation_root / "report.html"
    rendered_output = report.render_html_report(
        dataset_root=dataset_root,
        summary_path=summary_path,
        predictions_path=predictions_path,
        manifest_path=manifest_path,
        output_path=output_path,
        report_title="Mismatch Report",
    )

    html = rendered_output.read_text(encoding="utf-8")
    assert "Metrics Consistency Warning" in html
    assert "accepted/pothole" in html
    assert "summary.json says 0 / 1" in html
    assert "computed from predictions.jsonl as 1 / 1" in html

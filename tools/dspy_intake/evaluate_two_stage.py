"""Held-out evaluation for two-stage DSPy intake programs."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import csv
import json
from pathlib import Path
import sys
from typing import Literal

import dspy

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from tools.dspy_intake.programs import (
    _normalize_level1_prediction,
    _normalize_level2_prediction,
)
from tools.dspy_intake.training import DEFAULT_CATEGORY_CATALOG, load_stage_examples


LEVEL2_HINT_MODE = Literal["use_level1", "off"]


@dataclass(frozen=True, slots=True)
class EvaluationArtifacts:
    variant_name: str
    summary_path: Path
    confusion_matrix_path: Path
    predictions_path: Path
    level1_metrics_path: Path
    level2_metrics_path: Path


@dataclass(frozen=True, slots=True)
class VariantComparisonArtifacts:
    comparison_summary_path: Path
    variant_artifacts: dict[str, EvaluationArtifacts]


def evaluate_two_stage(
    *,
    dataset_root: Path,
    level1_export_path: Path,
    output_root: Path,
    level1_program,
    level2_program,
    variant_name: str = "selected",
    level2_hint_mode: LEVEL2_HINT_MODE = "use_level1",
) -> EvaluationArtifacts:
    if level2_hint_mode not in {"use_level1", "off"}:
        raise ValueError(
            f"Unsupported level2_hint_mode `{level2_hint_mode}`. Expected `use_level1` or `off`."
        )
    examples = load_stage_examples(
        stage="level1",
        export_path=level1_export_path,
        dataset_root=dataset_root,
        category_catalog=DEFAULT_CATEGORY_CATALOG,
        expected_split="test",
    )

    predictions: list[dict[str, object]] = []
    level1_group_totals: Counter[str] = Counter()
    level1_group_correct: Counter[str] = Counter()
    level2_category_totals: Counter[str] = Counter()
    level2_category_correct: Counter[str] = Counter()
    confusion: Counter[tuple[str, str]] = Counter()

    for example in examples:
        expected_scope = example.decision == "IN_SCOPE"
        expected_label = example.category_name if expected_scope else "REJECT"
        level1_prediction = _normalize_level1_prediction(
            level1_program(
                image=example.image,
                category_catalog=example.category_catalog,
            ),
            tuple(DEFAULT_CATEGORY_CATALOG),
        )
        predicted_scope = level1_prediction.decision == "IN_SCOPE"
        subgroup = str(example.subgroup)
        level1_group_totals[subgroup] += 1
        if predicted_scope == expected_scope:
            level1_group_correct[subgroup] += 1

        level2_predicted_label: str | None = None
        if expected_scope:
            best_matching_category_hint = (
                level1_prediction.best_matching_category_hint
                if predicted_scope and level2_hint_mode == "use_level1"
                else ""
            )
            ungated_level2_prediction = _normalize_level2_prediction(
                level2_program(
                    image=example.image,
                    category_catalog=example.category_catalog,
                    best_matching_category_hint=best_matching_category_hint,
                ),
                tuple(DEFAULT_CATEGORY_CATALOG),
            )
            level2_predicted_label = ungated_level2_prediction.category_name
            level2_category_totals[str(example.category_name)] += 1
            if level2_predicted_label == example.category_name:
                level2_category_correct[str(example.category_name)] += 1

        if predicted_scope:
            predicted_label = level2_predicted_label
        else:
            predicted_label = "REJECT"

        confusion[(str(expected_label), str(predicted_label))] += 1
        predictions.append(
            {
                "sample_id": example.sample_id,
                "subgroup": subgroup,
                "expected_label": expected_label,
                "predicted_label": predicted_label,
                "level1_decision": level1_prediction.decision,
                "level1_best_matching_category_hint": level1_prediction.best_matching_category_hint,
                "ungated_level2_predicted_label": level2_predicted_label,
            }
        )

    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    predictions_path = output_root / "predictions.jsonl"
    with predictions_path.open("w", encoding="utf-8") as handle:
        for prediction in predictions:
            handle.write(json.dumps(prediction) + "\n")

    confusion_matrix_path = output_root / "confusion_matrix.csv"
    _write_confusion_matrix(confusion_matrix_path, confusion)

    level1_metrics_path = output_root / "level1_subgroup_metrics.csv"
    level1_subgroup_metrics = _write_level1_metrics(
        level1_metrics_path,
        level1_group_totals,
        level1_group_correct,
    )

    level2_metrics_path = output_root / "level2_category_metrics.csv"
    level2_category_metrics = _write_level2_metrics(
        level2_metrics_path,
        level2_category_totals,
        level2_category_correct,
    )

    correct_predictions = sum(
        1 for row in predictions if row["expected_label"] == row["predicted_label"]
    )
    summary = {
        "variant_name": variant_name,
        "counts": {
            "total_examples": len(predictions),
            "correct_predictions": correct_predictions,
        },
        "level1_subgroup_metrics": level1_subgroup_metrics,
        "level2_category_metrics": level2_category_metrics,
        "end_to_end": {
            "accuracy": correct_predictions / len(predictions) if predictions else 0.0,
        },
        "level2_hint_mode": level2_hint_mode,
    }
    summary_path = output_root / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return EvaluationArtifacts(
        variant_name=variant_name,
        summary_path=summary_path,
        confusion_matrix_path=confusion_matrix_path,
        predictions_path=predictions_path,
        level1_metrics_path=level1_metrics_path,
        level2_metrics_path=level2_metrics_path,
    )


def evaluate_two_stage_variants(
    *,
    dataset_root: Path,
    level1_export_path: Path,
    output_root: Path,
    variants: dict[str, dict[str, object]],
) -> VariantComparisonArtifacts:
    if not variants:
        raise ValueError("At least one evaluation variant must be provided.")

    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    artifacts_by_variant: dict[str, EvaluationArtifacts] = {}
    summary_by_variant: dict[str, dict[str, object]] = {}

    for variant_name, programs in sorted(variants.items()):
        level1_program = programs.get("level1_program")
        level2_program = programs.get("level2_program")
        if level1_program is None or level2_program is None:
            raise ValueError(
                f"Variant `{variant_name}` must include both `level1_program` and `level2_program`."
            )
        variant_output_root = output_root / variant_name
        artifacts = evaluate_two_stage(
            dataset_root=dataset_root,
            level1_export_path=level1_export_path,
            output_root=variant_output_root,
            level1_program=level1_program,
            level2_program=level2_program,
            variant_name=variant_name,
            level2_hint_mode=programs.get("level2_hint_mode", "use_level1"),
        )
        artifacts_by_variant[variant_name] = artifacts
        summary_by_variant[variant_name] = json.loads(
            artifacts.summary_path.read_text(encoding="utf-8")
        )

    selected_variant = max(
        summary_by_variant,
        key=lambda name: (
            float(summary_by_variant[name]["end_to_end"]["accuracy"]),
            float(
                sum(
                    metric["accuracy"]
                    for metric in summary_by_variant[name]["level2_category_metrics"].values()
                )
            ),
        ),
    )

    comparison_summary = {
        "variants": summary_by_variant,
        "selected_variant": selected_variant,
    }
    comparison_summary_path = output_root / "comparison_summary.json"
    comparison_summary_path.write_text(
        json.dumps(comparison_summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return VariantComparisonArtifacts(
        comparison_summary_path=comparison_summary_path,
        variant_artifacts=artifacts_by_variant,
    )


def _write_confusion_matrix(
    path: Path,
    confusion: Counter[tuple[str, str]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["expected_label", "predicted_label", "count"],
        )
        writer.writeheader()
        for (expected_label, predicted_label), count in sorted(confusion.items()):
            writer.writerow(
                {
                    "expected_label": expected_label,
                    "predicted_label": predicted_label,
                    "count": count,
                }
            )


def _write_level1_metrics(
    path: Path,
    totals: Counter[str],
    correct: Counter[str],
) -> dict[str, dict[str, float | int]]:
    metrics: dict[str, dict[str, float | int]] = {}
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["subgroup", "total", "correct_scope", "accuracy"],
        )
        writer.writeheader()
        for subgroup in sorted(totals):
            total = totals[subgroup]
            correct_scope = correct[subgroup]
            accuracy = correct_scope / total if total else 0.0
            writer.writerow(
                {
                    "subgroup": subgroup,
                    "total": total,
                    "correct_scope": correct_scope,
                    "accuracy": accuracy,
                }
            )
            metrics[subgroup] = {
                "total": total,
                "correct_scope": correct_scope,
                "accuracy": accuracy,
            }
    return metrics


def _write_level2_metrics(
    path: Path,
    totals: Counter[str],
    correct: Counter[str],
) -> dict[str, dict[str, float | int]]:
    metrics: dict[str, dict[str, float | int]] = {}
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["category_name", "total", "correct", "accuracy"],
        )
        writer.writeheader()
        for category_name in sorted(totals):
            total = totals[category_name]
            correct_predictions = correct[category_name]
            accuracy = correct_predictions / total if total else 0.0
            writer.writerow(
                {
                    "category_name": category_name,
                    "total": total,
                    "correct": correct_predictions,
                    "accuracy": accuracy,
                }
            )
            metrics[category_name] = {
                "total": total,
                "correct": correct_predictions,
                "accuracy": accuracy,
            }
    return metrics


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate two-stage DSPy intake programs.")
    parser.add_argument("--dataset-root", type=Path, default=Path("artifacts/datasets/vlm_intake_v2"))
    parser.add_argument("--level1-export-path", type=Path, required=True)
    parser.add_argument("--level1-program-path", type=Path)
    parser.add_argument("--level2-program-path", type=Path)
    parser.add_argument("--gepa-level1-program-path", type=Path)
    parser.add_argument("--gepa-level2-program-path", type=Path)
    parser.add_argument("--mipro-level1-program-path", type=Path)
    parser.add_argument("--mipro-level2-program-path", type=Path)
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/models/intake_dspy/reports"))
    parser.add_argument("--level2-hint-mode", choices=("use_level1", "off"), default="use_level1")
    return parser.parse_args()


def main() -> int:
    from tools.dspy_intake.training import load_compiled_program

    args = _parse_args()
    variants: dict[str, dict[str, object]] = {}
    if args.gepa_level1_program_path or args.gepa_level2_program_path:
        if not args.gepa_level1_program_path or not args.gepa_level2_program_path:
            raise ValueError("Both GEPA program paths must be provided together.")
        variants["gepa"] = {
            "level1_program": load_compiled_program(args.gepa_level1_program_path),
            "level2_program": load_compiled_program(args.gepa_level2_program_path),
            "level2_hint_mode": args.level2_hint_mode,
        }
    if args.mipro_level1_program_path or args.mipro_level2_program_path:
        if not args.mipro_level1_program_path or not args.mipro_level2_program_path:
            raise ValueError("Both MIPRO program paths must be provided together.")
        variants["mipro"] = {
            "level1_program": load_compiled_program(args.mipro_level1_program_path),
            "level2_program": load_compiled_program(args.mipro_level2_program_path),
            "level2_hint_mode": args.level2_hint_mode,
        }
    if not variants and args.level1_program_path and args.level2_program_path:
        variants["selected"] = {
            "level1_program": load_compiled_program(args.level1_program_path),
            "level2_program": load_compiled_program(args.level2_program_path),
            "level2_hint_mode": args.level2_hint_mode,
        }
    if not variants:
        raise ValueError("Provide either a single pair of program paths or GEPA/MIPRO pairs.")

    comparison = evaluate_two_stage_variants(
        dataset_root=args.dataset_root,
        level1_export_path=args.level1_export_path,
        output_root=args.output_root,
        variants=variants,
    )
    print(
        json.dumps(
            {
                "comparison_summary_path": str(comparison.comparison_summary_path),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

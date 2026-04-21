"""Validate dataset manifests and optionally evaluate the live VLM gateway."""

from __future__ import annotations

import argparse
import base64
import csv
import json
import time
from collections import Counter, defaultdict
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

import httpx

from tools.dataset_prep.common import (
    DatasetBuildError,
    REAL_NEGATIVE_KEY,
    SPOOF_NEGATIVE_KEY,
    SampleManifestRecord,
    load_manifest_records,
    validate_manifest_records,
)


def call_gateway_for_manifest(
    records: list[SampleManifestRecord],
    dataset_root: Path,
    gateway_url: str,
    timeout_seconds: int,
    predictions_cache_path: Path | None = None,
    sleep_seconds: float = 0.0,
) -> dict[str, dict[str, Any]]:
    active_categories = {
        record.canonical_label: ""
        for record in records
        if record.canonical_label is not None
    }
    predictions = (
        load_predictions_cache(predictions_cache_path)
        if predictions_cache_path is not None
        else {}
    )
    with httpx.Client(base_url=gateway_url, timeout=timeout_seconds) as client:
        for record in records:
            if record.sample_id in predictions:
                continue
            image_path = dataset_root / record.relative_image_path
            image_base64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
            try:
                response = client.post(
                    "/internal/v1/intake/classify",
                    json={
                        "submission_id": record.sample_id,
                        "image_base64": image_base64,
                        "mime_type": "image/jpeg",
                        "reporter_notes": None,
                        "active_categories": active_categories,
                        "prompt_version": "dataset_eval_v1",
                    },
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = exc.response.text.strip()
                raise DatasetBuildError(
                    f"Gateway request failed for sample `{record.sample_id}` "
                    f"with status {exc.response.status_code}: {detail}"
                ) from exc
            except httpx.HTTPError as exc:
                raise DatasetBuildError(
                    f"Gateway request failed for sample `{record.sample_id}`: {exc}"
                ) from exc

            predictions[record.sample_id] = response.json()
            if predictions_cache_path is not None:
                save_predictions_cache(predictions_cache_path, predictions)
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
    return predictions


def load_predictions_cache(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise DatasetBuildError(f"Predictions cache `{path}` did not load as a JSON object")
    return {str(key): dict(value) for key, value in payload.items()}


def save_predictions_cache(
    path: Path,
    predictions: dict[str, dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(predictions, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def summarize_predictions(
    records: list[SampleManifestRecord],
    predictions: dict[str, dict[str, str | None]],
) -> dict[str, object]:
    total = len(records)
    if total == 0:
        return {
            "overall_accuracy": 0.0,
            "accept_reject_accuracy": 0.0,
            "real_negative_reject_rate": 0.0,
            "spoof_reject_rate": 0.0,
            "per_class": {},
            "confusion_rows": [],
            "misclassified_rows": [],
        }

    overall_correct = 0
    decision_correct = 0
    per_class = defaultdict(lambda: {"total": 0, "correct": 0})
    confusion = Counter()
    misclassified_rows: list[dict[str, str]] = []
    real_negative_total = 0
    real_negative_rejected = 0
    spoof_total = 0
    spoof_rejected = 0

    for record in records:
        prediction = predictions[record.sample_id]
        predicted_decision = (
            "accepted"
            if prediction["decision"] == "ACCEPTED_CATEGORY_MATCH"
            else "rejected"
        )
        predicted_label = (
            str(prediction["category_name"]).lower()
            if predicted_decision == "accepted" and prediction["category_name"] is not None
            else "rejected"
        )
        if record.intake_outcome == "accepted":
            expected_label = record.canonical_label
        elif record.is_spoof:
            expected_label = SPOOF_NEGATIVE_KEY
        else:
            expected_label = REAL_NEGATIVE_KEY

        confusion[
            (
                record.intake_outcome,
                expected_label,
                predicted_decision,
                predicted_label,
            )
        ] += 1
        if predicted_decision == record.intake_outcome:
            decision_correct += 1
        if record.intake_outcome == "rejected":
            if record.is_spoof:
                spoof_total += 1
                if predicted_decision == "rejected":
                    spoof_rejected += 1
            else:
                real_negative_total += 1
                if predicted_decision == "rejected":
                    real_negative_rejected += 1
        is_correct = False
        if record.intake_outcome == "accepted":
            is_correct = (
                predicted_decision == "accepted"
                and predicted_label == expected_label
            )
        else:
            is_correct = predicted_decision == "rejected"

        if is_correct:
            overall_correct += 1
            if record.canonical_label is not None:
                per_class[record.canonical_label]["correct"] += 1
        else:
            misclassified_rows.append(
                {
                    "sample_id": record.sample_id,
                    "expected_decision": record.intake_outcome,
                    "expected_label": expected_label,
                    "predicted_decision": predicted_decision,
                    "predicted_label": predicted_label,
                    "relative_image_path": record.relative_image_path,
                }
            )
        if record.canonical_label is not None:
            per_class[record.canonical_label]["total"] += 1

    confusion_rows = [
        {
            "expected_decision": expected_decision,
            "expected_label": expected_label,
            "predicted_decision": predicted_decision,
            "predicted_label": predicted_label,
            "count": count,
        }
        for (
            expected_decision,
            expected_label,
            predicted_decision,
            predicted_label,
        ), count in sorted(confusion.items())
    ]

    return {
        "overall_accuracy": overall_correct / total,
        "accept_reject_accuracy": decision_correct / total,
        "real_negative_reject_rate": (
            real_negative_rejected / real_negative_total if real_negative_total else 0.0
        ),
        "spoof_reject_rate": (
            spoof_rejected / spoof_total if spoof_total else 0.0
        ),
        "per_class": dict(per_class),
        "confusion_rows": confusion_rows,
        "misclassified_rows": misclassified_rows,
    }


def write_validation_outputs(
    output_dir: Path,
    summary: dict[str, object],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "validation_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_csv(
        output_dir / "confusion_matrix.csv",
        rows=list(summary["confusion_rows"]),
        fieldnames=[
            "expected_decision",
            "expected_label",
            "predicted_decision",
            "predicted_label",
            "count",
        ],
    )
    _write_csv(
        output_dir / "misclassified_samples.csv",
        rows=list(summary["misclassified_rows"]),
        fieldnames=[
            "sample_id",
            "expected_decision",
            "expected_label",
            "predicted_decision",
            "predicted_label",
            "relative_image_path",
        ],
    )


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--gateway-url", type=str, default=None)
    parser.add_argument("--timeout-seconds", type=int, default=240)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--predictions-cache", type=Path, default=None)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    args = parser.parse_args()

    records = load_manifest_records(args.manifest)
    dataset_root = args.manifest.parent.parent
    validate_manifest_records(dataset_root, records)

    if args.gateway_url is None:
        raise DatasetBuildError(
            "Static manifest validation passed. Provide --gateway-url to run live VLM evaluation."
        )

    output_dir = args.output_dir or dataset_root / "reports" / "validation"
    predictions_cache = args.predictions_cache or (output_dir / "predictions_cache.json")

    predictions = call_gateway_for_manifest(
        records,
        dataset_root=dataset_root,
        gateway_url=args.gateway_url,
        timeout_seconds=args.timeout_seconds,
        predictions_cache_path=predictions_cache,
        sleep_seconds=args.sleep_seconds,
    )
    summary = summarize_predictions(records, predictions)
    write_validation_outputs(output_dir, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

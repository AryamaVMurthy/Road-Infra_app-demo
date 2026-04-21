"""Build the canonical train/test VLM intake v2 benchmark corpus."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from tools.dataset_prep.common import (
    DatasetBuildError,
    NegativeImageSourceRecord,
    REAL_NEGATIVE_KEY,
    SPOOF_NEGATIVE_KEY,
    SampleManifestRecord,
    audit_source_labels,
    compute_average_hash,
    compute_sha256,
    dedupe_by_content,
    inventory_selection_key,
    load_dataset_config,
    normalize_image,
    resolve_output_root,
    validate_manifest_records,
    write_jsonl_records,
)

SPLITS = ("train", "test")


def build_dataset(config_path: Path) -> Path:
    config = load_dataset_config(config_path)
    output_root = resolve_output_root(config_path, config)
    output_root.mkdir(parents=True, exist_ok=True)

    seed = int(config.get("seed", 42))
    jpeg_quality = int(config.get("jpeg_quality", 92))
    min_short_edge = int(config.get("min_short_edge", 256))
    target_counts = dict(config["target_counts"])
    split_targets = dict(config["split_targets"])

    for directory in (output_root / "images", output_root / "manifests", output_root / "reports"):
        if directory.is_dir():
            shutil.rmtree(directory)

    inventory = _build_inventory(config, output_root)
    deduped_inventory, dedup_report = dedupe_by_content(
        [{"source_id": item["source_id"], "path": Path(str(item["path"])), **item} for item in inventory]
    )
    filtered_inventory = _filter_by_size(deduped_inventory, min_short_edge=min_short_edge)
    assignments = _select_and_assign(
        inventory=filtered_inventory,
        target_counts=target_counts,
        split_targets=split_targets,
        seed=seed,
    )

    manifests = _materialize(
        assignments=assignments,
        output_root=output_root,
        jpeg_quality=jpeg_quality,
        min_short_edge=min_short_edge,
    )
    validate_manifest_records(output_root, manifests)
    _write_manifests(output_root, manifests)

    selected = [record for split_records in assignments.values() for record in split_records]
    _write_reports(
        output_root=output_root,
        inventory=filtered_inventory,
        selected=selected,
        dedup_report=dedup_report,
        manifests=manifests,
    )
    return output_root


def _build_inventory(config: dict[str, Any], output_root: Path) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []

    for source in config["positive_sources"]:
        source_root = output_root / str(source["output_dir"])
        label_mapping = dict(source["label_mapping"])
        dataset_slug = str(source.get("dataset_slug", source_root.name))

        if source.get("mirror_label_field") == "none":
            canonical = list(label_mapping.values())[0]
            image_paths = sorted(
                path for path in source_root.rglob("*")
                if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png"}
            )
            if not image_paths:
                raise DatasetBuildError(f"No supplement images were discovered under {source_root}")
            for index, image_path in enumerate(image_paths, start=1):
                inventory.append(
                    {
                        "source_id": f"{dataset_slug}-{canonical}-{index:04d}",
                        "path": image_path,
                        "canonical_label": canonical,
                        "intake_outcome": "accepted",
                        "source_dataset": str(source["dataset_id"]),
                        "source_label": canonical,
                        "source_path": str(image_path.relative_to(output_root)),
                        "source_url": str(source["source_url"]),
                        "license_name": str(source["license_name"]),
                        "license_url": str(source["license_url"]),
                        "author_or_uploader": str(source["author_or_uploader"]),
                        "negative_source_type": None,
                        "is_spoof": False,
                        "notes": None,
                    }
                )
            continue

        audited = audit_source_labels(source_root, label_mapping)
        for index, record in enumerate(audited, start=1):
            path = Path(str(record["path"]))
            inventory.append(
                {
                    "source_id": f"{dataset_slug}-{record['canonical_label']}-{index:04d}",
                    "path": path,
                    "canonical_label": record["canonical_label"],
                    "intake_outcome": "accepted",
                    "source_dataset": str(source["dataset_id"]),
                    "source_label": record["source_label"],
                    "source_path": str(path.relative_to(output_root)),
                    "source_url": str(source["source_url"]),
                    "license_name": str(source["license_name"]),
                    "license_url": str(source["license_url"]),
                    "author_or_uploader": str(source["author_or_uploader"]),
                    "negative_source_type": None,
                    "is_spoof": False,
                    "notes": None,
                }
            )

    rejected_sources = list(config.get("rejected_dataset_sources", []))
    if not rejected_sources:
        raise DatasetBuildError("Dataset config must declare `rejected_dataset_sources`")

    rejected_index = 1
    for source in rejected_sources:
        source_root = output_root / str(source["output_dir"])
        source_rows = _load_rejected_sidecars(
            source_root=source_root,
            output_root=output_root,
            start_index=rejected_index,
        )
        inventory.extend(source_rows)
        rejected_index += len(source_rows)

    return inventory


def _load_rejected_sidecars(
    *,
    source_root: Path,
    output_root: Path,
    start_index: int,
) -> list[dict[str, Any]]:
    if not source_root.is_dir():
        raise DatasetBuildError(f"Rejected source directory missing: {source_root}")

    sidecar_paths = sorted(source_root.glob("*.json"))
    if not sidecar_paths:
        raise DatasetBuildError(f"No rejected source sidecars were found under {source_root}")

    rows: list[dict[str, Any]] = []
    for offset, sidecar_path in enumerate(sidecar_paths):
        image_path = sidecar_path.with_suffix("")
        if not image_path.is_file():
            raise DatasetBuildError(
                f"Rejected source sidecar `{sidecar_path}` is missing its paired image file"
            )
        source_row = NegativeImageSourceRecord.model_validate_json(sidecar_path.read_text(encoding="utf-8"))
        rows.append(
            {
                "source_id": f"rejected-{start_index + offset:04d}",
                "path": image_path,
                "canonical_label": None,
                "intake_outcome": "rejected",
                "source_dataset": source_row.source_dataset,
                "source_label": None,
                "source_path": str(image_path.relative_to(output_root)),
                "source_url": source_row.source_url,
                "license_name": source_row.license_name,
                "license_url": source_row.license_url,
                "author_or_uploader": source_row.author_or_uploader,
                "negative_source_type": source_row.negative_source_type,
                "is_spoof": source_row.is_spoof,
                "notes": source_row.notes,
            }
        )
    return rows


def _filter_by_size(inventory: list[dict[str, Any]], min_short_edge: int) -> list[dict[str, Any]]:
    from PIL import Image

    kept: list[dict[str, Any]] = []
    skipped: Counter[str] = Counter()
    for record in inventory:
        selection_key = inventory_selection_key(record)
        with Image.open(Path(str(record["path"]))) as image:
            width, height = image.size
        if min(width, height) < min_short_edge:
            skipped[selection_key] += 1
            continue
        kept.append(record)
    for label, count in sorted(skipped.items()):
        print(f"Skipped {count} samples below {min_short_edge}px for {label}")
    return kept


def _select_and_assign(
    *,
    inventory: list[dict[str, Any]],
    target_counts: dict[str, int],
    split_targets: dict[str, dict[str, int]],
    seed: int,
) -> dict[str, list[dict[str, Any]]]:
    import random

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in inventory:
        grouped[inventory_selection_key(record)].append(record)

    rng = random.Random(seed)
    selected: list[dict[str, Any]] = []
    for label_key, total_count in target_counts.items():
        available = list(grouped.get(label_key, []))
        if len(available) < total_count:
            raise DatasetBuildError(
                f"Not enough samples for `{label_key}`: need {total_count}, have {len(available)}"
            )
        available.sort(key=lambda row: str(row["source_id"]))
        rng.shuffle(available)
        selected.extend(available[:total_count])

    selected_grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in selected:
        selected_grouped[inventory_selection_key(record)].append(record)

    assignments: dict[str, list[dict[str, Any]]] = {split_name: [] for split_name in SPLITS}
    for label_key, split_counts in _transpose(split_targets).items():
        available = list(selected_grouped.get(label_key, []))
        if len(available) < sum(split_counts.values()):
            raise DatasetBuildError(
                f"Split targets for `{label_key}` exceed selected pool: "
                f"need {sum(split_counts.values())}, have {len(available)}"
            )
        rng.shuffle(available)
        cursor = 0
        for split_name, count in split_counts.items():
            assignments[split_name].extend(available[cursor:cursor + count])
            cursor += count
    return assignments


def _transpose(split_targets: dict[str, dict[str, int]]) -> dict[str, dict[str, int]]:
    per_label: dict[str, dict[str, int]] = {}
    for split_name, label_counts in split_targets.items():
        for label_key, count in label_counts.items():
            per_label.setdefault(label_key, {})[split_name] = count
    return per_label


def _materialize(
    *,
    assignments: dict[str, list[dict[str, Any]]],
    output_root: Path,
    jpeg_quality: int,
    min_short_edge: int,
) -> list[SampleManifestRecord]:
    manifests: list[SampleManifestRecord] = []
    counter = 1
    for split_name in SPLITS:
        split_records = sorted(assignments[split_name], key=lambda row: (inventory_selection_key(row), str(row["source_id"])))
        for record in split_records:
            label_dir = inventory_selection_key(record) if record["intake_outcome"] == "rejected" else str(record["canonical_label"])
            sample_id = f"vlm_v2_{counter:04d}"
            counter += 1
            relative_image_path = Path("images") / split_name / label_dir / f"{sample_id}.jpg"
            destination_path = output_root / relative_image_path
            width, height = normalize_image(
                Path(str(record["path"])),
                destination_path,
                jpeg_quality=jpeg_quality,
                min_short_edge=min_short_edge,
            )
            manifests.append(
                SampleManifestRecord(
                    sample_id=sample_id,
                    split=split_name,
                    intake_outcome=str(record["intake_outcome"]),
                    canonical_label=record["canonical_label"],
                    is_negative=record["intake_outcome"] == "rejected",
                    is_spoof=bool(record["is_spoof"]),
                    negative_source_type=record["negative_source_type"],
                    relative_image_path=str(relative_image_path),
                    source_dataset=str(record["source_dataset"]),
                    source_label=record["source_label"],
                    source_path=record["source_path"],
                    source_url=str(record["source_url"]),
                    license_name=str(record["license_name"]),
                    license_url=str(record["license_url"]),
                    author_or_uploader=str(record["author_or_uploader"]),
                    width=width,
                    height=height,
                    sha256=compute_sha256(destination_path),
                    phash=compute_average_hash(destination_path),
                    notes=record["notes"],
                )
            )
    return manifests


def _write_manifests(output_root: Path, manifests: list[SampleManifestRecord]) -> None:
    manifests_dir = output_root / "manifests"
    all_rows = [record.model_dump(mode="json") for record in manifests]
    write_jsonl_records(manifests_dir / "all_samples.jsonl", all_rows)
    for split_name in SPLITS:
        write_jsonl_records(
            manifests_dir / f"{split_name}.jsonl",
            [record.model_dump(mode="json") for record in manifests if record.split == split_name],
        )
    label_map = {
        "accepted_labels": sorted({record.canonical_label for record in manifests if record.canonical_label is not None}),
        "rejected_types": [REAL_NEGATIVE_KEY, SPOOF_NEGATIVE_KEY],
    }
    (manifests_dir / "label_map.json").write_text(
        json.dumps(label_map, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_reports(
    *,
    output_root: Path,
    inventory: list[dict[str, Any]],
    selected: list[dict[str, Any]],
    dedup_report: list[dict[str, str]],
    manifests: list[SampleManifestRecord],
) -> None:
    reports_dir = output_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    selected_source_ids = {str(record["source_id"]) for record in selected}
    excluded_rows = [
        record for record in inventory
        if str(record["source_id"]) not in selected_source_ids
    ]

    _write_csv(
        reports_dir / "source_inventory.csv",
        inventory,
        fieldnames=[
            "source_id",
            "source_dataset",
            "source_label",
            "canonical_label",
            "intake_outcome",
            "negative_source_type",
            "is_spoof",
            "source_path",
            "license_name",
        ],
    )
    _write_csv(
        reports_dir / "excluded_samples.csv",
        excluded_rows,
        fieldnames=[
            "source_id",
            "source_dataset",
            "source_label",
            "canonical_label",
            "intake_outcome",
            "negative_source_type",
            "source_path",
        ],
    )
    _write_csv(
        reports_dir / "dedup_report.csv",
        dedup_report,
        fieldnames=["removed_source_id", "kept_source_id", "reason"],
    )

    split_counts = Counter(record.split for record in manifests)
    accepted_counts = Counter(
        record.canonical_label for record in manifests if record.intake_outcome == "accepted"
    )
    rejected_counts = Counter(
        inventory_selection_key(
            {
                "intake_outcome": record.intake_outcome,
                "canonical_label": record.canonical_label,
                "negative_source_type": record.negative_source_type,
                "source_id": record.sample_id,
            }
        )
        for record in manifests
        if record.intake_outcome == "rejected"
    )
    source_counts = Counter(record.source_dataset for record in manifests)

    summary_lines = [
        "# VLM Intake v2 Dataset Summary",
        "",
        f"- Total samples: {len(manifests)}",
        f"- Accepted positives: {sum(accepted_counts.values())}",
        f"- Rejected negatives: {sum(rejected_counts.values())}",
        "",
        "## Split Counts",
    ]
    summary_lines.extend(f"- {split_name}: {split_counts[split_name]}" for split_name in SPLITS)
    summary_lines.extend(["", "## Accepted Class Counts"])
    summary_lines.extend(f"- {label}: {count}" for label, count in sorted(accepted_counts.items()))
    summary_lines.extend(["", "## Rejected Type Counts"])
    summary_lines.extend(f"- {label}: {count}" for label, count in sorted(rejected_counts.items()))
    summary_lines.extend(["", "## Source Dataset Counts"])
    summary_lines.extend(f"- {source_dataset}: {count}" for source_dataset, count in sorted(source_counts.items()))
    (reports_dir / "dataset_summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fieldnames})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    build_dataset(args.config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

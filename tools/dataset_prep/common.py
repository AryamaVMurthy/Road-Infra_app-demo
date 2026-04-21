"""Common helpers for preparing the VLM intake evaluation datasets."""

from __future__ import annotations

import hashlib
import json
import random
import shutil
from pathlib import Path
from typing import Any, Literal

import yaml

from pydantic import BaseModel, ConfigDict, Field, model_validator
from PIL import Image


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
NEGATIVE_LABEL_KEY = "rejected"
REAL_NEGATIVE_KEY = "rejected_real_irrelevant"
SPOOF_NEGATIVE_KEY = "rejected_synthetic_spoof"


class DatasetBuildError(RuntimeError):
    """Raised when the dataset prep pipeline cannot continue safely."""


class KaggleEnvironmentError(DatasetBuildError):
    """Raised when Kaggle acquisition prerequisites are missing."""


class SampleManifestRecord(BaseModel):
    """Normalized manifest row for a selected dataset sample."""

    model_config = ConfigDict(extra="forbid")

    sample_id: str
    split: Literal["train", "test"]
    intake_outcome: Literal["accepted", "rejected"]
    canonical_label: str | None
    is_negative: bool
    is_spoof: bool
    negative_source_type: Literal["real_irrelevant", "synthetic_spoof"] | None
    relative_image_path: str
    source_dataset: str
    source_label: str | None
    source_path: str | None
    source_url: str
    license_name: str
    license_url: str
    author_or_uploader: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    sha256: str = Field(min_length=64, max_length=64)
    phash: str = Field(min_length=16, max_length=16)
    notes: str | None = None

    @model_validator(mode="after")
    def validate_accept_reject_contract(self) -> "SampleManifestRecord":
        if self.intake_outcome == "accepted":
            if self.canonical_label is None:
                raise ValueError("Accepted manifest records must include a canonical label")
            if self.is_negative:
                raise ValueError("Accepted manifest records cannot be negative samples")
            if self.is_spoof:
                raise ValueError("Accepted manifest records cannot be marked as spoof")
            if self.negative_source_type is not None:
                raise ValueError(
                    "Accepted manifest records cannot include a negative source type"
                )
        else:
            if self.canonical_label is not None:
                raise ValueError("Rejected manifest records must not include a canonical label")
            if not self.is_negative:
                raise ValueError("Rejected manifest records must be marked as negative")
            if self.negative_source_type not in {"real_irrelevant", "synthetic_spoof"}:
                raise ValueError("Rejected manifest records must declare a supported negative_source_type")
            if self.negative_source_type == "real_irrelevant" and self.is_spoof:
                raise ValueError("Real irrelevant negatives cannot be marked as spoof")
            if self.negative_source_type == "synthetic_spoof" and not self.is_spoof:
                raise ValueError("Synthetic spoof negatives must be marked as spoof")
        return self


class NegativeImageSourceRecord(BaseModel):
    """Normalized source metadata for a stored negative image sample."""

    model_config = ConfigDict(extra="forbid")

    topic_bucket: str = Field(min_length=1)
    source_dataset: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    source_page_title: str = Field(min_length=1)
    license_name: str = Field(min_length=1)
    license_url: str = Field(min_length=1)
    author_or_uploader: str = Field(min_length=1)
    negative_source_type: Literal["real_irrelevant", "synthetic_spoof"]
    is_spoof: bool
    notes: str | None = None

    @model_validator(mode="after")
    def validate_spoof_contract(self) -> "NegativeImageSourceRecord":
        if self.negative_source_type == "real_irrelevant" and self.is_spoof:
            raise ValueError("real_irrelevant source records must set is_spoof=false")
        if self.negative_source_type == "synthetic_spoof" and not self.is_spoof:
            raise ValueError("synthetic_spoof source records must set is_spoof=true")
        return self


def load_dataset_config(config_path: Path) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, dict):
        raise DatasetBuildError(f"Config {config_path} did not load as a mapping")
    return loaded


def resolve_output_root(config_path: Path, config: dict[str, Any]) -> Path:
    configured = Path(str(config["output_root"]))
    if configured.is_absolute():
        return configured
    return (config_path.parent / configured).resolve()


def inventory_selection_key(record: dict[str, Any]) -> str:
    if record["intake_outcome"] == "accepted":
        return str(record["canonical_label"])
    negative_source_type = record.get("negative_source_type")
    if negative_source_type == "synthetic_spoof":
        return SPOOF_NEGATIVE_KEY
    if negative_source_type == "real_irrelevant":
        return REAL_NEGATIVE_KEY
    raise DatasetBuildError(
        f"Rejected inventory record `{record.get('source_id')}` is missing a supported negative_source_type"
    )


def ensure_kaggle_environment(
    kaggle_json_path: Path | None = None,
    kaggle_cli_path: str | None = None,
) -> Path:
    """Fail fast when Kaggle CLI or credentials are missing."""

    messages: list[str] = []
    if kaggle_cli_path is None:
        cli_path = shutil.which("kaggle")
    else:
        explicit_path = Path(kaggle_cli_path)
        cli_path = (
            kaggle_cli_path
            if explicit_path.exists()
            else shutil.which(kaggle_cli_path)
        )
    if cli_path is None:
        messages.append("Install the Kaggle CLI and ensure `kaggle` is on PATH.")

    resolved_kaggle_json_path = kaggle_json_path or (Path.home() / ".kaggle" / "kaggle.json")
    if not resolved_kaggle_json_path.is_file():
        messages.append(
            "Provide Kaggle credentials at `~/.kaggle/kaggle.json` before downloading sources."
        )

    if messages:
        raise KaggleEnvironmentError(" ".join(messages))

    return resolved_kaggle_json_path


def audit_source_labels(
    source_root: Path,
    label_mapping: dict[str, str],
) -> list[dict[str, str]]:
    """Inspect leaf image directories and fail on unknown source labels."""

    known_labels = set(label_mapping)
    inventory: list[dict[str, str]] = []
    unknown_labels: set[str] = set()

    for directory in sorted(path for path in source_root.rglob("*") if path.is_dir()):
        image_files = sorted(
            candidate
            for candidate in directory.iterdir()
            if candidate.is_file() and candidate.suffix.lower() in IMAGE_SUFFIXES
        )
        if not image_files:
            continue
        source_label = directory.name
        if source_label not in known_labels:
            unknown_labels.add(source_label)
            continue
        for image_path in image_files:
            inventory.append(
                {
                    "source_label": source_label,
                    "canonical_label": label_mapping[source_label],
                    "path": str(image_path),
                }
            )

    if unknown_labels:
        unknown_list = ", ".join(sorted(unknown_labels))
        raise DatasetBuildError(f"Unknown source labels discovered in raw data: {unknown_list}")

    if not inventory:
        raise DatasetBuildError(
            f"No usable images were discovered under {source_root} for the configured source labels"
        )

    return inventory


def assign_split_targets(
    inventory: list[dict[str, str | None]],
    split_targets: dict[str, dict[str, int]],
    seed: int,
) -> dict[str, list[dict[str, str | None]]]:
    """Assign deterministic split membership that exactly matches target counts."""

    grouped: dict[str, list[dict[str, str | None]]] = {}
    for record in inventory:
        label_key = inventory_selection_key(record)
        grouped.setdefault(str(label_key), []).append(record)

    assignments = {split_name: [] for split_name in split_targets}
    rng = random.Random(seed)
    seen_ids: set[str] = set()

    for label_key, required_counts in _transpose_split_targets(split_targets).items():
        available = list(grouped.get(label_key, []))
        if len(available) < sum(required_counts.values()):
            raise DatasetBuildError(
                f"Not enough usable samples for `{label_key}`: "
                f"need {sum(required_counts.values())}, found {len(available)}"
            )
        rng.shuffle(available)
        cursor = 0
        for split_name, count in required_counts.items():
            chosen = available[cursor : cursor + count]
            cursor += count
            assignments[split_name].extend(chosen)
            for item in chosen:
                source_id = str(item["source_id"])
                if source_id in seen_ids:
                    raise DatasetBuildError(
                        f"Duplicate source_id `{source_id}` encountered during split assignment"
                    )
                seen_ids.add(source_id)

    return assignments


def _transpose_split_targets(
    split_targets: dict[str, dict[str, int]]
) -> dict[str, dict[str, int]]:
    per_label: dict[str, dict[str, int]] = {}
    for split_name, label_counts in split_targets.items():
        for label_key, count in label_counts.items():
            per_label.setdefault(label_key, {})[split_name] = count
    return per_label


def compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compute_average_hash(path: Path) -> str:
    with Image.open(path) as image:
        grayscale = image.convert("L").resize((8, 8))
        pixels = [grayscale.getpixel((x, y)) for y in range(8) for x in range(8)]
    average = sum(pixels) / len(pixels)
    bits = "".join("1" if value >= average else "0" for value in pixels)
    return f"{int(bits, 2):016x}"


def normalize_image(
    source_path: Path,
    destination_path: Path,
    jpeg_quality: int,
    min_short_edge: int,
) -> tuple[int, int]:
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source_path) as image:
        normalized = image.convert("RGB")
        width, height = normalized.size
        if min(width, height) < min_short_edge:
            raise DatasetBuildError(
                f"Image `{source_path}` is below the minimum short edge of {min_short_edge}px"
            )
        normalized.save(destination_path, format="JPEG", quality=jpeg_quality)
        return normalized.size


def dedupe_by_content(
    records: list[dict[str, object]]
) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    """Drop exact-content duplicates deterministically."""

    seen_sha_to_source_id: dict[str, str] = {}
    kept: list[dict[str, object]] = []
    removed: list[dict[str, str]] = []

    for record in records:
        path = Path(str(record["path"]))
        sha256_value = compute_sha256(path)
        source_id = str(record["source_id"])
        if sha256_value in seen_sha_to_source_id:
            removed.append(
                {
                    "removed_source_id": source_id,
                    "kept_source_id": seen_sha_to_source_id[sha256_value],
                    "reason": "exact_sha256_duplicate",
                }
            )
            continue
        seen_sha_to_source_id[sha256_value] = source_id
        kept.append(record)

    return kept, removed


def validate_manifest_records(
    dataset_root: Path,
    records: list[SampleManifestRecord],
) -> None:
    """Ensure every manifest entry points to an existing normalized image."""

    seen_relative_paths: set[str] = set()
    for record in records:
        if record.relative_image_path in seen_relative_paths:
            raise DatasetBuildError(
                f"Manifest contains duplicate relative_image_path `{record.relative_image_path}`"
            )
        seen_relative_paths.add(record.relative_image_path)
        image_path = dataset_root / record.relative_image_path
        if not image_path.is_file():
            raise DatasetBuildError(f"Manifest image `{image_path}` does not exist on disk")


def load_manifest_records(manifest_path: Path) -> list[SampleManifestRecord]:
    records: list[SampleManifestRecord] = []
    with manifest_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            records.append(SampleManifestRecord.model_validate_json(line))
    return records


def write_jsonl_records(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

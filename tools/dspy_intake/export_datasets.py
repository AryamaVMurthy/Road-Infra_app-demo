"""Export VLM intake v2 manifests into two-stage DSPy JSONL datasets."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any

from pydantic import ValidationError

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from tools.dspy_intake.constants import (
    LEVEL1_NEGATIVE_LABEL,
    LEVEL1_POSITIVE_LABEL,
    LEVEL2_ALLOWED_LABELS,
)
from tools.dataset_prep.common import (
    DatasetBuildError,
    SampleManifestRecord,
    validate_manifest_records,
    write_jsonl_records,
)
SUPPORTED_SPLITS = ("train", "test")
SUPPORTED_NEGATIVE_SUBGROUPS = {
    "real_irrelevant": "rejected_real_irrelevant",
    "synthetic_spoof": "rejected_synthetic_spoof",
}


def export_dspy_datasets(
    dataset_root: Path,
    output_root: Path | None = None,
) -> dict[str, dict[str, Path]]:
    """Write two-stage DSPy JSONL exports for the configured dataset root."""

    resolved_dataset_root = Path(dataset_root)
    resolved_output_root = (
        resolved_dataset_root / "dspy_exports"
        if output_root is None
        else Path(output_root)
    )
    resolved_output_root.parent.mkdir(parents=True, exist_ok=True)
    if resolved_output_root.is_symlink():
        raise DatasetBuildError(
            f"DSPy export output_root `{resolved_output_root}` is a symbolic link, which is not supported. "
            "Replace it with a real directory path before rerunning the export."
        )
    if resolved_output_root.exists() and not resolved_output_root.is_dir():
        raise DatasetBuildError(
            f"DSPy export output_root `{resolved_output_root}` already exists and must be a directory. "
            "Remove or rename the file before rerunning the export."
        )

    hidden_output_root = _hide_existing_output_root(resolved_output_root)
    staging_root: Path | None = None

    try:
        export_rows = _build_export_rows(resolved_dataset_root)
        staging_root = Path(
            tempfile.mkdtemp(
                prefix=f".{resolved_output_root.name}.staging-",
                dir=resolved_output_root.parent,
            )
        )
        _write_export_rows(staging_root, export_rows)
        staging_root.rename(resolved_output_root)
        staging_root = None
        if hidden_output_root is not None:
            _remove_path(hidden_output_root)
        return _build_output_paths(resolved_output_root)
    except Exception:
        if staging_root is not None and staging_root.exists():
            _remove_path(staging_root)
        if hidden_output_root is not None and hidden_output_root.exists():
            _remove_path(hidden_output_root)
        raise


def _hide_existing_output_root(output_root: Path) -> Path | None:
    if not output_root.exists():
        return None
    hidden_output_root = Path(
        tempfile.mkdtemp(
            prefix=f".{output_root.name}.backup-",
            dir=output_root.parent,
        )
    )
    hidden_output_root.rmdir()
    output_root.rename(hidden_output_root)
    return hidden_output_root


def _remove_path(path: Path) -> None:
    if path.is_symlink():
        path.unlink()
        return
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
        return
    path.unlink()


def _build_export_rows(dataset_root: Path) -> dict[str, dict[str, list[dict[str, Any]]]]:
    export_rows: dict[str, dict[str, list[dict[str, Any]]]] = {
        "level1": {},
        "level2": {},
    }

    for split_name in SUPPORTED_SPLITS:
        records = _load_split_records(dataset_root, split_name)
        export_rows["level1"][split_name] = [
            _build_level1_row(record) for record in records
        ]
        export_rows["level2"][split_name] = [
            _build_level2_row(record)
            for record in records
            if record.intake_outcome == "accepted"
        ]

    return export_rows


def _write_export_rows(
    output_root: Path,
    export_rows: dict[str, dict[str, list[dict[str, Any]]]],
) -> None:
    for split_name in SUPPORTED_SPLITS:
        write_jsonl_records(
            output_root / f"level1_{split_name}.jsonl",
            export_rows["level1"][split_name],
        )
        write_jsonl_records(
            output_root / f"level2_{split_name}.jsonl",
            export_rows["level2"][split_name],
        )


def _build_output_paths(output_root: Path) -> dict[str, dict[str, Path]]:
    return {
        "level1": {
            split_name: output_root / f"level1_{split_name}.jsonl"
            for split_name in SUPPORTED_SPLITS
        },
        "level2": {
            split_name: output_root / f"level2_{split_name}.jsonl"
            for split_name in SUPPORTED_SPLITS
        },
    }


def _load_split_records(dataset_root: Path, split_name: str) -> list[SampleManifestRecord]:
    manifest_path = dataset_root / "manifests" / f"{split_name}.jsonl"
    if not manifest_path.is_file():
        raise DatasetBuildError(
            f"DSPy export manifest `{manifest_path}` does not exist. "
            "Build `vlm_intake_v2` manifests before exporting DSPy datasets."
        )

    records = _load_manifest_records_with_context(manifest_path)
    validate_manifest_records(dataset_root, records)

    for record in records:
        if record.split != split_name:
            raise DatasetBuildError(
                f"Manifest `{manifest_path}` contains sample `{record.sample_id}` "
                f"with split `{record.split}` instead of `{split_name}`."
            )

    return records


def _load_manifest_records_with_context(manifest_path: Path) -> list[SampleManifestRecord]:
    records: list[SampleManifestRecord] = []
    with manifest_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                records.append(SampleManifestRecord.model_validate_json(line))
            except (ValidationError, ValueError) as exc:
                raise DatasetBuildError(
                    f"DSPy export manifest `{manifest_path}` has a malformed row at line {line_number}. "
                    "Fix or regenerate the malformed manifest row and rerun the export.\n"
                    f"Root cause:\n{exc}"
                ) from exc
    return records


def _build_level1_row(record: SampleManifestRecord) -> dict[str, Any]:
    if record.intake_outcome == "accepted":
        canonical_label = record.canonical_label
        if canonical_label not in LEVEL2_ALLOWED_LABELS:
            raise DatasetBuildError(
                f"Accepted sample `{record.sample_id}` has unsupported "
                f"canonical_label `{canonical_label}` for DSPy Level 2 export."
            )
        subgroup = f"accepted/{canonical_label}"
        label = LEVEL1_POSITIVE_LABEL
    else:
        subgroup = SUPPORTED_NEGATIVE_SUBGROUPS.get(str(record.negative_source_type))
        if subgroup is None:
            raise DatasetBuildError(
                f"Rejected sample `{record.sample_id}` has unsupported "
                f"negative_source_type `{record.negative_source_type}`."
            )
        label = LEVEL1_NEGATIVE_LABEL

    return {
        "label": label,
        "relative_image_path": record.relative_image_path,
        "sample_id": record.sample_id,
        "split": record.split,
        "subgroup": subgroup,
    }


def _build_level2_row(record: SampleManifestRecord) -> dict[str, Any]:
    canonical_label = record.canonical_label
    if canonical_label not in LEVEL2_ALLOWED_LABELS:
        raise DatasetBuildError(
            f"Accepted sample `{record.sample_id}` has unsupported "
            f"canonical_label `{canonical_label}` for DSPy Level 2 export."
        )

    return {
        "label": canonical_label,
        "relative_image_path": record.relative_image_path,
        "sample_id": record.sample_id,
        "split": record.split,
        "subgroup": f"accepted/{canonical_label}",
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export VLM intake v2 manifests into two-stage DSPy JSONL datasets.",
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=Path("artifacts/datasets/vlm_intake_v2"),
        help="Dataset root containing `manifests/` and `images/`.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help=(
            "Output directory for exported JSONL files. Defaults to "
            "`<dataset-root>/dspy_exports`."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    export_dspy_datasets(
        dataset_root=args.dataset_root,
        output_root=args.output_root,
    )


if __name__ == "__main__":
    main()

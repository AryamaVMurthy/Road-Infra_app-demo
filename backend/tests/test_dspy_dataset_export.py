import json
from collections import Counter
from pathlib import Path
import sys

from PIL import Image
import pytest


sys.path.append(str(Path(__file__).resolve().parents[2]))

from tools.dataset_prep.common import DatasetBuildError, SampleManifestRecord


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _repeat_to_length(seed: str, length: int) -> str:
    return (seed * ((length // len(seed)) + 1))[:length]


def _write_image(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (16, 16), color=color).save(path, format="JPEG")


def _build_manifest_record(
    *,
    sample_id: str,
    split: str,
    relative_image_path: str,
    intake_outcome: str,
    canonical_label: str | None,
    negative_source_type: str | None = None,
) -> SampleManifestRecord:
    return SampleManifestRecord(
        sample_id=sample_id,
        split=split,
        intake_outcome=intake_outcome,
        canonical_label=canonical_label,
        is_negative=intake_outcome == "rejected",
        is_spoof=negative_source_type == "synthetic_spoof",
        negative_source_type=negative_source_type,
        relative_image_path=relative_image_path,
        source_dataset="test-dataset",
        source_label=canonical_label,
        source_path=f"raw/{sample_id}.jpg",
        source_url="https://example.com/dataset",
        license_name="CC0-1.0",
        license_url="https://creativecommons.org/publicdomain/zero/1.0/",
        author_or_uploader="dataset-author",
        width=16,
        height=16,
        sha256=_repeat_to_length(sample_id, 64),
        phash=_repeat_to_length(sample_id[::-1], 16),
        notes=None,
    )


def _write_manifest(path: Path, records: list[SampleManifestRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(record.model_dump_json() + "\n")


def _seed_dataset(
    dataset_root: Path,
    *,
    include_test_manifest: bool = True,
    missing_image_sample_id: str | None = None,
) -> dict[str, list[SampleManifestRecord]]:
    records_by_split = {
        "train": [
            _build_manifest_record(
                sample_id="train_pothole_1",
                split="train",
                relative_image_path="images/train/pothole/train_pothole_1.jpg",
                intake_outcome="accepted",
                canonical_label="pothole",
            ),
            _build_manifest_record(
                sample_id="train_damaged_road_1",
                split="train",
                relative_image_path="images/train/damaged_road/train_damaged_road_1.jpg",
                intake_outcome="accepted",
                canonical_label="damaged_road",
            ),
            _build_manifest_record(
                sample_id="train_real_reject_1",
                split="train",
                relative_image_path=(
                    "images/train/rejected_real_irrelevant/train_real_reject_1.jpg"
                ),
                intake_outcome="rejected",
                canonical_label=None,
                negative_source_type="real_irrelevant",
            ),
            _build_manifest_record(
                sample_id="train_spoof_reject_1",
                split="train",
                relative_image_path=(
                    "images/train/rejected_synthetic_spoof/train_spoof_reject_1.jpg"
                ),
                intake_outcome="rejected",
                canonical_label=None,
                negative_source_type="synthetic_spoof",
            ),
        ],
        "test": [
            _build_manifest_record(
                sample_id="test_sign_1",
                split="test",
                relative_image_path="images/test/damaged_road_sign/test_sign_1.jpg",
                intake_outcome="accepted",
                canonical_label="damaged_road_sign",
            ),
            _build_manifest_record(
                sample_id="test_litter_1",
                split="test",
                relative_image_path="images/test/garbage_litter/test_litter_1.jpg",
                intake_outcome="accepted",
                canonical_label="garbage_litter",
            ),
            _build_manifest_record(
                sample_id="test_real_reject_1",
                split="test",
                relative_image_path=(
                    "images/test/rejected_real_irrelevant/test_real_reject_1.jpg"
                ),
                intake_outcome="rejected",
                canonical_label=None,
                negative_source_type="real_irrelevant",
            ),
            _build_manifest_record(
                sample_id="test_spoof_reject_1",
                split="test",
                relative_image_path=(
                    "images/test/rejected_synthetic_spoof/test_spoof_reject_1.jpg"
                ),
                intake_outcome="rejected",
                canonical_label=None,
                negative_source_type="synthetic_spoof",
            ),
        ],
    }

    for split_name, records in records_by_split.items():
        if split_name == "test" and not include_test_manifest:
            continue
        _write_manifest(dataset_root / "manifests" / f"{split_name}.jsonl", records)

    for color_index, records in enumerate(records_by_split.values(), start=1):
        for record_index, record in enumerate(records, start=1):
            if record.sample_id == missing_image_sample_id:
                continue
            _write_image(
                dataset_root / record.relative_image_path,
                color=(color_index * 30, record_index * 30, 120),
            )

    return records_by_split


def _export_rows(
    dataset_root: Path,
    output_root: Path,
) -> dict[str, dict[str, list[dict[str, object]]]]:
    from tools.dspy_intake.export_datasets import export_dspy_datasets

    outputs = export_dspy_datasets(dataset_root=dataset_root, output_root=output_root)
    return {
        stage_name: {
            split_name: _read_jsonl(path)
            for split_name, path in split_outputs.items()
        }
        for stage_name, split_outputs in outputs.items()
    }


@pytest.fixture
def sample_dataset_root(tmp_path: Path) -> Path:
    dataset_root = tmp_path / "dataset"
    _seed_dataset(dataset_root)
    return dataset_root


def test_level1_export_uses_binary_label_vocabulary(
    sample_dataset_root: Path,
    tmp_path: Path,
):
    outputs = _export_rows(sample_dataset_root, tmp_path / "exports")
    labels = {
        str(row["label"])
        for split_name in ("train", "test")
        for row in outputs["level1"][split_name]
    }

    assert labels == {
        "in_scope_category_image",
        "spoof_or_out_of_scope",
    }


def test_level1_export_preserves_subgroups_and_image_paths(
    sample_dataset_root: Path,
    tmp_path: Path,
):
    outputs = _export_rows(sample_dataset_root, tmp_path / "exports")
    expected = {
        "train": {
            "labels": {
                "in_scope_category_image": 2,
                "spoof_or_out_of_scope": 2,
            },
            "subgroups": {
                "accepted/pothole": 1,
                "accepted/damaged_road": 1,
                "rejected_real_irrelevant": 1,
                "rejected_synthetic_spoof": 1,
            },
        },
        "test": {
            "labels": {
                "in_scope_category_image": 2,
                "spoof_or_out_of_scope": 2,
            },
            "subgroups": {
                "accepted/damaged_road_sign": 1,
                "accepted/garbage_litter": 1,
                "rejected_real_irrelevant": 1,
                "rejected_synthetic_spoof": 1,
            },
        },
    }

    for split_name, split_expected in expected.items():
        rows = outputs["level1"][split_name]
        assert Counter(str(row["label"]) for row in rows) == split_expected["labels"]
        assert Counter(str(row["subgroup"]) for row in rows) == split_expected["subgroups"]
        for row in rows:
            assert row["split"] == split_name
            assert str(row["relative_image_path"]).startswith(f"images/{split_name}/")
            assert (sample_dataset_root / str(row["relative_image_path"])).is_file()


def test_level2_export_contains_only_accepted_category_examples(
    sample_dataset_root: Path,
    tmp_path: Path,
):
    outputs = _export_rows(sample_dataset_root, tmp_path / "exports")
    expected = {
        "train": {"pothole": 1, "damaged_road": 1},
        "test": {"damaged_road_sign": 1, "garbage_litter": 1},
    }

    for split_name, split_expected in expected.items():
        rows = outputs["level2"][split_name]
        assert Counter(str(row["label"]) for row in rows) == split_expected
        assert Counter(str(row["subgroup"]) for row in rows) == {
            f"accepted/{label}": count
            for label, count in split_expected.items()
        }
        for row in rows:
            assert row["split"] == split_name
            assert str(row["subgroup"]).startswith("accepted/")
            assert row["label"] in {
                "pothole",
                "damaged_road",
                "damaged_road_sign",
                "garbage_litter",
            }
            assert str(row["relative_image_path"]).startswith(f"images/{split_name}/")
            assert (sample_dataset_root / str(row["relative_image_path"])).is_file()


def test_exporter_reports_manifest_path_line_and_remediation_for_malformed_row(
    tmp_path: Path,
):
    from tools.dspy_intake.export_datasets import export_dspy_datasets

    dataset_root = tmp_path / "dataset"
    manifest_path = dataset_root / "manifests" / "train.jsonl"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text('{"sample_id":"broken"}\n', encoding="utf-8")

    with pytest.raises(DatasetBuildError) as exc:
        export_dspy_datasets(dataset_root=dataset_root, output_root=tmp_path / "exports")

    message = str(exc.value)
    assert str(manifest_path) in message
    assert "line 1" in message
    assert "malformed row" in message
    assert "Fix or regenerate the malformed manifest row and rerun the export." in message


def test_exporter_fails_fast_when_split_manifest_is_missing(tmp_path: Path):
    from tools.dspy_intake.export_datasets import export_dspy_datasets

    dataset_root = tmp_path / "dataset"
    missing_manifest = dataset_root / "manifests" / "test.jsonl"
    _seed_dataset(dataset_root, include_test_manifest=False)

    with pytest.raises(DatasetBuildError) as exc:
        export_dspy_datasets(dataset_root=dataset_root, output_root=tmp_path / "exports")

    message = str(exc.value)
    assert str(missing_manifest) in message
    assert "does not exist" in message


def test_exporter_fails_fast_when_manifest_image_is_missing(tmp_path: Path):
    from tools.dspy_intake.export_datasets import export_dspy_datasets

    dataset_root = tmp_path / "dataset"
    missing_image = (
        dataset_root / "images" / "test" / "garbage_litter" / "test_litter_1.jpg"
    )
    _seed_dataset(dataset_root, missing_image_sample_id="test_litter_1")

    with pytest.raises(DatasetBuildError) as exc:
        export_dspy_datasets(dataset_root=dataset_root, output_root=tmp_path / "exports")

    message = str(exc.value)
    assert str(missing_image) in message
    assert "does not exist on disk" in message


def test_exporter_fails_fast_when_output_root_is_a_file(tmp_path: Path):
    from tools.dspy_intake.export_datasets import export_dspy_datasets

    dataset_root = tmp_path / "dataset"
    output_root = tmp_path / "exports"
    _seed_dataset(dataset_root)
    output_root.write_text("not a directory\n", encoding="utf-8")

    with pytest.raises(DatasetBuildError) as exc:
        export_dspy_datasets(dataset_root=dataset_root, output_root=output_root)

    message = str(exc.value)
    assert str(output_root) in message
    assert "must be a directory" in message
    assert output_root.read_text(encoding="utf-8") == "not a directory\n"
    assert list(tmp_path.glob(".exports.backup-*")) == []


def test_exporter_fails_fast_when_output_root_is_a_symlink(tmp_path: Path):
    from tools.dspy_intake.export_datasets import export_dspy_datasets

    dataset_root = tmp_path / "dataset"
    target_dir = tmp_path / "existing_exports"
    output_root = tmp_path / "exports"
    _seed_dataset(dataset_root)
    target_dir.mkdir()
    output_root.symlink_to(target_dir, target_is_directory=True)

    with pytest.raises(DatasetBuildError) as exc:
        export_dspy_datasets(dataset_root=dataset_root, output_root=output_root)

    message = str(exc.value)
    assert str(output_root) in message
    assert "symbolic link" in message
    assert output_root.is_symlink()
    assert output_root.resolve() == target_dir.resolve()
    assert list(tmp_path.glob(".exports.backup-*")) == []


def test_exporter_does_not_leave_partial_outputs_when_later_split_fails(tmp_path: Path):
    from tools.dspy_intake.export_datasets import export_dspy_datasets

    dataset_root = tmp_path / "dataset"
    output_root = tmp_path / "exports"
    _seed_dataset(dataset_root, include_test_manifest=False)

    with pytest.raises(DatasetBuildError):
        export_dspy_datasets(dataset_root=dataset_root, output_root=output_root)

    assert not output_root.exists()


def test_exporter_removes_stale_outputs_when_rerun_fails(tmp_path: Path):
    from tools.dspy_intake.export_datasets import export_dspy_datasets

    dataset_root = tmp_path / "dataset"
    output_root = tmp_path / "exports"
    _seed_dataset(dataset_root)

    export_dspy_datasets(dataset_root=dataset_root, output_root=output_root)
    assert output_root.is_dir()
    assert sorted(path.name for path in output_root.iterdir()) == [
        "level1_test.jsonl",
        "level1_train.jsonl",
        "level2_test.jsonl",
        "level2_train.jsonl",
    ]

    (dataset_root / "manifests" / "test.jsonl").unlink()

    with pytest.raises(DatasetBuildError):
        export_dspy_datasets(dataset_root=dataset_root, output_root=output_root)

    assert not output_root.exists()

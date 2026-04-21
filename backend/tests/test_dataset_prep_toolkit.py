from pathlib import Path
import sys

import pytest
from PIL import Image

sys.path.append(str(Path(__file__).resolve().parents[2]))

from tools.dataset_prep.common import (
    DatasetBuildError,
    KaggleEnvironmentError,
    NegativeImageSourceRecord,
    REAL_NEGATIVE_KEY,
    SampleManifestRecord,
    SPOOF_NEGATIVE_KEY,
    assign_split_targets,
    audit_source_labels,
    dedupe_by_content,
    ensure_kaggle_environment,
    inventory_selection_key,
    validate_manifest_records,
)


def _write_image(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (512, 384), color=color).save(path)


def test_ensure_kaggle_environment_requires_cli_and_credentials(tmp_path: Path):
    with pytest.raises(KaggleEnvironmentError) as exc:
        ensure_kaggle_environment(
            kaggle_json_path=tmp_path / "missing.json",
            kaggle_cli_path="missing-kaggle-cli",
        )

    assert "Install the Kaggle CLI" in str(exc.value)
    assert "kaggle.json" in str(exc.value)


def test_audit_source_labels_fails_on_unknown_leaf_directory(tmp_path: Path):
    raw_root = tmp_path / "raw" / "kaggle" / "road_issues_detection"
    _write_image(raw_root / "Pothole Issues" / "pothole_1.jpg", (255, 0, 0))
    _write_image(raw_root / "Alien Issue" / "bad_1.jpg", (0, 255, 0))

    with pytest.raises(DatasetBuildError) as exc:
        audit_source_labels(
            source_root=raw_root,
            label_mapping={"Pothole Issues": "pothole"},
        )

    assert "Unknown source labels" in str(exc.value)
    assert "Alien Issue" in str(exc.value)


def test_manifest_record_enforces_accept_reject_contract():
    accepted = SampleManifestRecord(
        sample_id="vlm_v2_0001",
        split="train",
        intake_outcome="accepted",
        canonical_label="pothole",
        is_negative=False,
        is_spoof=False,
        negative_source_type=None,
        relative_image_path="images/train/pothole/vlm_v2_0001.jpg",
        source_dataset="programmerrdai/road-issues-detection-dataset",
        source_label="Pothole Issues",
        source_path="raw/pothole_1.jpg",
        source_url="https://www.kaggle.com/datasets/programmerrdai/road-issues-detection-dataset",
        license_name="CC0-1.0",
        license_url="https://creativecommons.org/publicdomain/zero/1.0/",
        author_or_uploader="dataset-author",
        width=512,
        height=384,
        sha256="a" * 64,
        phash="f" * 16,
        notes=None,
    )
    assert accepted.canonical_label == "pothole"

    with pytest.raises(ValueError):
        SampleManifestRecord(
            sample_id="vlm_v2_0002",
            split="train",
            intake_outcome="rejected",
            canonical_label="pothole",
            is_negative=True,
            is_spoof=False,
            negative_source_type="real_irrelevant",
            relative_image_path="images/train/rejected_real_irrelevant/vlm_v2_0002.jpg",
            source_dataset="wikimedia_commons",
            source_label=None,
            source_path=None,
            source_url="https://commons.wikimedia.org/wiki/File:Cat.jpg",
            license_name="CC BY-SA 4.0",
            license_url="https://creativecommons.org/licenses/by-sa/4.0/",
            author_or_uploader="photographer",
            width=512,
            height=384,
            sha256="b" * 64,
            phash="0" * 16,
            notes="real negative image",
        )

    spoof = SampleManifestRecord(
        sample_id="vlm_v2_0003",
        split="test",
        intake_outcome="rejected",
        canonical_label=None,
        is_negative=True,
        is_spoof=True,
        negative_source_type="synthetic_spoof",
        relative_image_path="images/test/rejected_synthetic_spoof/vlm_v2_0003.jpg",
        source_dataset="Zitacron/real-vs-ai-corpus",
        source_label=None,
        source_path="raw/rejected_datasets/zitacron_spoof/001.jpg",
        source_url="https://huggingface.co/datasets/Zitacron/real-vs-ai-corpus",
        license_name="CC-BY-4.0",
        license_url="https://huggingface.co/datasets/Zitacron/real-vs-ai-corpus",
        author_or_uploader="Zitacron",
        width=512,
        height=384,
        sha256="c" * 64,
        phash="1" * 16,
        notes="upstream source=svjack/diffusiondb_random_10k",
    )
    assert spoof.is_spoof is True


def test_assign_split_targets_matches_exact_plan_counts():
    inventory = []
    counts = {
        "pothole": 24,
        "damaged_road": 12,
        "damaged_road_sign": 12,
        "garbage_litter": 10,
        REAL_NEGATIVE_KEY: 6,
        SPOOF_NEGATIVE_KEY: 8,
    }
    for label, count in counts.items():
        for index in range(count):
            is_rejected = label in {REAL_NEGATIVE_KEY, SPOOF_NEGATIVE_KEY}
            inventory.append(
                {
                    "source_id": f"{label}-{index}",
                    "canonical_label": None if is_rejected else label,
                    "intake_outcome": "rejected" if is_rejected else "accepted",
                    "negative_source_type": (
                        "synthetic_spoof"
                        if label == SPOOF_NEGATIVE_KEY
                        else "real_irrelevant" if label == REAL_NEGATIVE_KEY else None
                    ),
                }
            )

    split_targets = {
        "train": {
            "pothole": 18,
            "damaged_road": 9,
            "damaged_road_sign": 9,
            "garbage_litter": 8,
            REAL_NEGATIVE_KEY: 4,
            SPOOF_NEGATIVE_KEY: 6,
        },
        "test": {
            "pothole": 6,
            "damaged_road": 3,
            "damaged_road_sign": 3,
            "garbage_litter": 2,
            REAL_NEGATIVE_KEY: 2,
            SPOOF_NEGATIVE_KEY: 2,
        },
    }

    assignments = assign_split_targets(inventory, split_targets=split_targets, seed=7)

    assert sum(len(values) for values in assignments.values()) == 72
    assert len(assignments["train"]) == 54
    assert len(assignments["test"]) == 18
    assert sum(1 for item in assignments["test"] if item["canonical_label"] == "pothole") == 6
    assert sum(1 for item in assignments["train"] if item.get("negative_source_type") == "synthetic_spoof") == 6


def test_dedupe_by_content_drops_exact_duplicate(tmp_path: Path):
    first = tmp_path / "images" / "img_1.jpg"
    second = tmp_path / "images" / "img_2.jpg"
    _write_image(first, (10, 20, 30))
    second.write_bytes(first.read_bytes())

    kept, removed = dedupe_by_content(
        [
            {"source_id": "first", "path": first},
            {"source_id": "second", "path": second},
        ]
    )

    assert [item["source_id"] for item in kept] == ["first"]
    assert removed[0]["removed_source_id"] == "second"
    assert removed[0]["kept_source_id"] == "first"
    assert removed[0]["reason"] == "exact_sha256_duplicate"


def test_validate_manifest_records_fails_when_file_is_missing(tmp_path: Path):
    record = SampleManifestRecord(
        sample_id="vlm_v2_0001",
        split="train",
        intake_outcome="accepted",
        canonical_label="pothole",
        is_negative=False,
        is_spoof=False,
        negative_source_type=None,
        relative_image_path="images/train/pothole/vlm_v2_0001.jpg",
        source_dataset="programmerrdai/road-issues-detection-dataset",
        source_label="Pothole Issues",
        source_path="raw/pothole_1.jpg",
        source_url="https://www.kaggle.com/datasets/programmerrdai/road-issues-detection-dataset",
        license_name="CC0-1.0",
        license_url="https://creativecommons.org/publicdomain/zero/1.0/",
        author_or_uploader="dataset-author",
        width=512,
        height=384,
        sha256="a" * 64,
        phash="f" * 16,
        notes=None,
    )

    with pytest.raises(DatasetBuildError) as exc:
        validate_manifest_records(tmp_path, [record])

    assert "does not exist on disk" in str(exc.value)


def test_negative_image_source_requires_dataset_metadata():
    record = NegativeImageSourceRecord(
        topic_bucket="animals_or_pets",
        source_dataset="cvdl/oxford-pets",
        source_url="https://huggingface.co/datasets/cvdl/oxford-pets",
        source_page_title="Abyssinian sample 0001",
        license_name="MIT",
        license_url="https://huggingface.co/datasets/cvdl/oxford-pets",
        author_or_uploader="ZHAW CVDL",
        negative_source_type="real_irrelevant",
        is_spoof=False,
        notes="strict non-road pet image",
    )

    assert record.source_dataset == "cvdl/oxford-pets"

    with pytest.raises(ValueError):
        NegativeImageSourceRecord(
            topic_bucket="animals_or_pets",
            source_dataset="",
            source_url="https://huggingface.co/datasets/cvdl/oxford-pets",
            source_page_title="Abyssinian sample 0002",
            license_name="MIT",
            license_url="https://huggingface.co/datasets/cvdl/oxford-pets",
            author_or_uploader="ZHAW CVDL",
            negative_source_type="real_irrelevant",
            is_spoof=False,
            notes=None,
        )


def test_inventory_selection_key_separates_real_and_spoof_rejects():
    assert inventory_selection_key(
        {
            "source_id": "pos-1",
            "intake_outcome": "accepted",
            "canonical_label": "pothole",
        }
    ) == "pothole"
    assert inventory_selection_key(
        {
            "source_id": "neg-1",
            "intake_outcome": "rejected",
            "canonical_label": None,
            "negative_source_type": "real_irrelevant",
        }
    ) == REAL_NEGATIVE_KEY
    assert inventory_selection_key(
        {
            "source_id": "neg-2",
            "intake_outcome": "rejected",
            "canonical_label": None,
            "negative_source_type": "synthetic_spoof",
        }
    ) == SPOOF_NEGATIVE_KEY

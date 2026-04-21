import json
from pathlib import Path
import sys

import pytest
from PIL import Image

sys.path.append(str(Path(__file__).resolve().parents[2]))

from tools.dataset_prep.build_train_test import build_dataset, load_dataset_config
from tools.dataset_prep.common import (
    DatasetBuildError,
    NegativeImageSourceRecord,
    SampleManifestRecord,
)
from tools.dataset_prep.fetch_hf_rejected_sources import (
    build_rejected_dataset_filename,
    fetch_rejected_dataset_sources,
)
from tools.dataset_prep.fetch_positive_mirror import fetch_positive_mirror_sources
from tools.dataset_prep.fetch_pothole_supplement import fetch_supplement_sources
from tools.dataset_prep.validate_dataset import (
    call_gateway_for_manifest,
    load_predictions_cache,
    save_predictions_cache,
    summarize_predictions,
)


def _build_manifest_record(
    *,
    sample_id: str,
    relative_image_path: str,
    intake_outcome: str = "accepted",
    canonical_label: str | None = "pothole",
    negative_source_type: str | None = None,
    is_spoof: bool = False,
) -> SampleManifestRecord:
    return SampleManifestRecord(
        sample_id=sample_id,
        split="test",
        intake_outcome=intake_outcome,
        canonical_label=canonical_label,
        is_negative=intake_outcome == "rejected",
        is_spoof=is_spoof,
        negative_source_type=negative_source_type,
        relative_image_path=relative_image_path,
        source_dataset="dataset-source",
        source_label=None if intake_outcome == "rejected" else canonical_label,
        source_path=f"raw/{sample_id}.jpg",
        source_url="https://example.com/dataset",
        license_name="CC0-1.0",
        license_url="https://creativecommons.org/publicdomain/zero/1.0/",
        author_or_uploader="dataset-author",
        width=512,
        height=384,
        sha256="a" * 64,
        phash="f" * 16,
        notes=None,
    )


def test_load_dataset_config_reads_v2_fields(tmp_path: Path):
    config_path = tmp_path / "vlm_intake_v2.yaml"
    config_path.write_text(
        """
dataset_name: vlm_intake_v2
seed: 42
output_root: artifacts/datasets/vlm_intake_v2
rejected_dataset_sources:
  - dataset_id: cvdl/oxford-pets
    negative_source_type: real_irrelevant
    output_dir: raw/rejected_datasets/oxford_pets
split_targets:
  train:
    pothole: 96
""".strip()
    )

    config = load_dataset_config(config_path)

    assert config["dataset_name"] == "vlm_intake_v2"
    assert config["rejected_dataset_sources"][0]["negative_source_type"] == "real_irrelevant"
    assert config["split_targets"]["train"]["pothole"] == 96


def test_fetch_rejected_dataset_sources_writes_real_and_spoof_sidecars(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
dataset_name: vlm_intake_v2
seed: 42
output_root: dataset_out
min_short_edge: 256
rejected_dataset_sources:
  - dataset_id: cvdl/oxford-pets
    config_name: default
    split: train
    image_field: img
    label_field: category
    count: 1
    topic_bucket: animals_or_pets
    negative_source_type: real_irrelevant
    source_url: https://huggingface.co/datasets/cvdl/oxford-pets
    license_name: MIT
    license_url: https://huggingface.co/datasets/cvdl/oxford-pets
    author_or_uploader: ZHAW CVDL
    output_dir: raw/rejected_datasets/oxford_pets
    notes: strict non-road pet image
  - dataset_id: Zitacron/real-vs-ai-corpus
    config_name: default
    split: train
    image_field: image
    filter_field: label_text
    filter_values: [ai]
    source_dataset_field: source_dataset
    source_license_field: source_license
    diversity_field: source_dataset
    max_per_diversity_value: 1
    count: 1
    topic_bucket: spoof_mixed
    negative_source_type: synthetic_spoof
    source_url: https://huggingface.co/datasets/Zitacron/real-vs-ai-corpus
    license_name: mixed-permissive
    license_url: https://huggingface.co/datasets/Zitacron/real-vs-ai-corpus
    author_or_uploader: Zitacron
    output_dir: raw/rejected_datasets/zitacron_spoof
    notes: row-level provenance preserved
""".strip()
    )

    def fake_row_pages(**kwargs):
        dataset_id = kwargs["dataset_id"]
        if dataset_id == "cvdl/oxford-pets":
            return {
                "features": [
                    {"name": "category", "type": {"names": ["Abyssinian"]}},
                ],
                "rows": [
                    {
                        "row": {
                            "img": {
                                "src": "https://example.com/pet.jpg",
                                "width": 512,
                                "height": 512,
                            },
                            "category": 0,
                        }
                    }
                ],
            }
        return {
            "features": [
                {"name": "label_text", "type": {"dtype": "string", "_type": "Value"}},
                {"name": "source_dataset", "type": {"dtype": "string", "_type": "Value"}},
                {"name": "source_license", "type": {"dtype": "string", "_type": "Value"}},
            ],
            "rows": [
                {
                    "row": {
                        "image": {
                            "src": "https://example.com/spoof.jpg",
                            "width": 768,
                            "height": 768,
                        },
                        "label_text": "ai",
                        "source_dataset": "svjack/diffusiondb_random_10k",
                        "source_license": "cc-by-4.0",
                    }
                }
            ],
        }

    monkeypatch.setattr(
        "tools.dataset_prep.fetch_hf_rejected_sources._fetch_rows_page",
        fake_row_pages,
    )
    monkeypatch.setattr(
        "tools.dataset_prep.fetch_hf_rejected_sources._fetch_split_row_count",
        lambda **kwargs: 50,
    )
    monkeypatch.setattr(
        "tools.dataset_prep.fetch_hf_rejected_sources._download_image",
        lambda **kwargs: Image.new("RGB", (512, 512), color=(10, 20, 30)).save(
            kwargs["destination"], format="JPEG"
        ),
    )

    output_root = fetch_rejected_dataset_sources(config_path)
    real_dir = output_root / "raw" / "rejected_datasets" / "oxford_pets"
    spoof_dir = output_root / "raw" / "rejected_datasets" / "zitacron_spoof"

    real_sidecar = real_dir / (build_rejected_dataset_filename(1, "Abyssinian sample 0001") + ".json")
    spoof_sidecar = spoof_dir / (build_rejected_dataset_filename(1, "svjack diffusiondb random 10k sample 0001") + ".json")
    assert real_sidecar.is_file()
    assert spoof_sidecar.is_file()

    real_record = NegativeImageSourceRecord.model_validate_json(real_sidecar.read_text("utf-8"))
    spoof_record = NegativeImageSourceRecord.model_validate_json(spoof_sidecar.read_text("utf-8"))
    assert real_record.is_spoof is False
    assert real_record.negative_source_type == "real_irrelevant"
    assert spoof_record.is_spoof is True
    assert spoof_record.negative_source_type == "synthetic_spoof"
    assert spoof_record.source_dataset == "svjack/diffusiondb_random_10k"
    assert spoof_record.license_name == "cc-by-4.0"


def test_fetch_positive_mirror_sources_and_supplements_write_images(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
dataset_name: vlm_intake_v2
seed: 42
output_root: dataset_out
min_short_edge: 256
positive_sources:
  - dataset_id: programmerrdai/road-issues-detection-dataset
    dataset_slug: road_issues_detection
    output_dir: raw/kaggle/road_issues_detection
    source_url: https://huggingface.co/datasets/Programmer-RD-AI/road-issues-detection-dataset
    license_name: CC0-1.0
    license_url: https://huggingface.co/datasets/Programmer-RD-AI/road-issues-detection-dataset
    author_or_uploader: Programmer-RD-AI
    mirror_dataset_id: Programmer-RD-AI/road-issues-detection-dataset
    mirror_split: train
    mirror_config_name: default
    mirror_image_field: image
    mirror_label_field: label
    mirror_fetch_margin: 1
    mirror_sampling_strategy: rows_api
    mirror_offset_hints:
      Pothole Issues: 0
    label_mapping:
      Pothole Issues: pothole
  - dataset_id: manot/pothole-segmentation
    dataset_slug: pothole_seg_manot
    output_dir: raw/hf_supplements/pothole_manot
    source_url: https://huggingface.co/datasets/manot/pothole-segmentation
    license_name: CC
    license_url: https://huggingface.co/datasets/manot/pothole-segmentation
    author_or_uploader: manot
    mirror_dataset_id: manot/pothole-segmentation
    mirror_split: train
    mirror_config_name: full
    mirror_image_field: image
    mirror_label_field: none
    mirror_fetch_margin: 1
    mirror_sampling_strategy: rows_api
    label_mapping:
      pothole: pothole
target_counts:
  pothole: 2
  rejected_real_irrelevant: 0
  rejected_synthetic_spoof: 0
split_targets:
  train:
    pothole: 2
    rejected_real_irrelevant: 0
    rejected_synthetic_spoof: 0
  test:
    pothole: 0
    rejected_real_irrelevant: 0
    rejected_synthetic_spoof: 0
""".strip()
    )

    def fake_positive_rows(**kwargs):
        if kwargs["dataset_id"] == "Programmer-RD-AI/road-issues-detection-dataset":
            return {
                "features": [
                    {"name": "image", "type": {"_type": "Image"}},
                    {"name": "label", "type": {"names": ["Pothole Issues"], "_type": "ClassLabel"}},
                ],
                "rows": [
                    {"row": {"image": {"src": "https://example.com/p1.jpg", "width": 512, "height": 512}, "label": 0}},
                    {"row": {"image": {"src": "https://example.com/p2.jpg", "width": 512, "height": 512}, "label": 0}},
                ],
            }
        return {
            "features": [
                {"name": "image", "type": {"_type": "Image"}},
            ],
            "rows": [
                {"row": {"image": {"src": "https://example.com/s1.jpg", "width": 512, "height": 512}}},
                {"row": {"image": {"src": "https://example.com/s2.jpg", "width": 512, "height": 512}}},
            ],
        }

    monkeypatch.setattr(
        "tools.dataset_prep.fetch_positive_mirror._request_rows_page",
        fake_positive_rows,
    )
    monkeypatch.setattr(
        "tools.dataset_prep.fetch_positive_mirror._download_binary",
        lambda **kwargs: Image.new("RGB", (512, 512), color=(1, 2, 3)).save(
            kwargs["destination"], format="JPEG"
        ),
    )
    monkeypatch.setattr(
        "tools.dataset_prep.fetch_pothole_supplement._fetch_rows_page",
        fake_positive_rows,
    )
    monkeypatch.setattr(
        "tools.dataset_prep.fetch_pothole_supplement._fetch_split_row_count",
        lambda **kwargs: 20,
    )
    monkeypatch.setattr(
        "tools.dataset_prep.fetch_pothole_supplement._download_binary",
        lambda **kwargs: Image.new("RGB", (512, 512), color=(4, 5, 6)).save(
            kwargs["destination"], format="JPEG"
        ),
    )

    output_root = fetch_positive_mirror_sources(
        config_path=config_path,
        required_counts={"pothole": 1},
    )
    fetch_supplement_sources(config_path=config_path, required_counts={"pothole": 3})

    assert len(list((output_root / "raw" / "kaggle" / "road_issues_detection" / "Pothole Issues").glob("*.jpg"))) == 2
    assert len(list((output_root / "raw" / "hf_supplements" / "pothole_manot").glob("*.jpg"))) == 2


def test_build_dataset_materializes_spoof_and_real_reject_dirs(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
dataset_name: vlm_intake_v2
seed: 3
output_root: dataset_out
min_short_edge: 64
jpeg_quality: 90
positive_sources:
  - dataset_id: programmerrdai/road-issues-detection-dataset
    dataset_slug: road_issues_detection
    source_url: https://huggingface.co/datasets/Programmer-RD-AI/road-issues-detection-dataset
    license_name: CC0-1.0
    license_url: https://huggingface.co/datasets/Programmer-RD-AI/road-issues-detection-dataset
    author_or_uploader: Programmer-RD-AI
    output_dir: raw/kaggle/road_issues_detection
    label_mapping:
      Pothole Issues: pothole
rejected_dataset_sources:
  - dataset_id: cvdl/oxford-pets
    output_dir: raw/rejected_datasets/oxford_pets
  - dataset_id: Zitacron/real-vs-ai-corpus
    output_dir: raw/rejected_datasets/zitacron_spoof
target_counts:
  pothole: 2
  rejected_real_irrelevant: 1
  rejected_synthetic_spoof: 1
split_targets:
  train:
    pothole: 1
    rejected_real_irrelevant: 1
    rejected_synthetic_spoof: 0
  test:
    pothole: 1
    rejected_real_irrelevant: 0
    rejected_synthetic_spoof: 1
""".strip()
    )

    raw_pothole_dir = tmp_path / "dataset_out" / "raw" / "kaggle" / "road_issues_detection" / "Pothole Issues"
    real_dir = tmp_path / "dataset_out" / "raw" / "rejected_datasets" / "oxford_pets"
    spoof_dir = tmp_path / "dataset_out" / "raw" / "rejected_datasets" / "zitacron_spoof"
    raw_pothole_dir.mkdir(parents=True, exist_ok=True)
    real_dir.mkdir(parents=True, exist_ok=True)
    spoof_dir.mkdir(parents=True, exist_ok=True)

    for index, color in enumerate([(255, 0, 0), (0, 0, 255)], start=1):
        Image.new("RGB", (160, 120), color=color).save(raw_pothole_dir / f"pothole_{index}.jpg")

    real_image = real_dir / "001_pet.jpg"
    Image.new("RGB", (160, 120), color=(20, 30, 40)).save(real_image)
    real_image.with_suffix(".jpg.json").write_text(
        NegativeImageSourceRecord(
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
        ).model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    spoof_image = spoof_dir / "001_spoof.jpg"
    Image.new("RGB", (160, 120), color=(50, 60, 70)).save(spoof_image)
    spoof_image.with_suffix(".jpg.json").write_text(
        NegativeImageSourceRecord(
            topic_bucket="spoof_mixed",
            source_dataset="svjack/diffusiondb_random_10k",
            source_url="https://huggingface.co/datasets/svjack/diffusiondb_random_10k",
            source_page_title="diffusiondb sample 0001",
            license_name="CC-BY-4.0",
            license_url="https://huggingface.co/datasets/svjack/diffusiondb_random_10k",
            author_or_uploader="svjack",
            negative_source_type="synthetic_spoof",
            is_spoof=True,
            notes="via Zitacron/real-vs-ai-corpus",
        ).model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )

    output_root = build_dataset(config_path)

    assert (output_root / "manifests" / "all_samples.jsonl").is_file()
    assert len(list((output_root / "images" / "train" / "rejected_real_irrelevant").glob("*.jpg"))) == 1
    assert len(list((output_root / "images" / "test" / "rejected_synthetic_spoof").glob("*.jpg"))) == 1


def test_summarize_predictions_reports_spoof_specific_metrics():
    records = [
        SampleManifestRecord(
            sample_id="vlm_v2_0001",
            split="test",
            intake_outcome="accepted",
            canonical_label="pothole",
            is_negative=False,
            is_spoof=False,
            negative_source_type=None,
            relative_image_path="images/test/pothole/vlm_v2_0001.jpg",
            source_dataset="programmerrdai/road-issues-detection-dataset",
            source_label="Pothole Issues",
            source_path="raw/pothole_1.jpg",
            source_url="https://huggingface.co/datasets/Programmer-RD-AI/road-issues-detection-dataset",
            license_name="CC0-1.0",
            license_url="https://huggingface.co/datasets/Programmer-RD-AI/road-issues-detection-dataset",
            author_or_uploader="Programmer-RD-AI",
            width=512,
            height=384,
            sha256="a" * 64,
            phash="f" * 16,
            notes=None,
        ),
        SampleManifestRecord(
            sample_id="vlm_v2_0002",
            split="test",
            intake_outcome="rejected",
            canonical_label=None,
            is_negative=True,
            is_spoof=False,
            negative_source_type="real_irrelevant",
            relative_image_path="images/test/rejected_real_irrelevant/vlm_v2_0002.jpg",
            source_dataset="cvdl/oxford-pets",
            source_label=None,
            source_path="raw/rejected_datasets/oxford_pets/001_pet.jpg",
            source_url="https://huggingface.co/datasets/cvdl/oxford-pets",
            license_name="MIT",
            license_url="https://huggingface.co/datasets/cvdl/oxford-pets",
            author_or_uploader="ZHAW CVDL",
            width=512,
            height=384,
            sha256="b" * 64,
            phash="0" * 16,
            notes=None,
        ),
        SampleManifestRecord(
            sample_id="vlm_v2_0003",
            split="test",
            intake_outcome="rejected",
            canonical_label=None,
            is_negative=True,
            is_spoof=True,
            negative_source_type="synthetic_spoof",
            relative_image_path="images/test/rejected_synthetic_spoof/vlm_v2_0003.jpg",
            source_dataset="svjack/diffusiondb_random_10k",
            source_label=None,
            source_path="raw/rejected_datasets/zitacron_spoof/001_spoof.jpg",
            source_url="https://huggingface.co/datasets/Zitacron/real-vs-ai-corpus",
            license_name="CC-BY-4.0",
            license_url="https://huggingface.co/datasets/Zitacron/real-vs-ai-corpus",
            author_or_uploader="Zitacron",
            width=512,
            height=384,
            sha256="c" * 64,
            phash="1" * 16,
            notes=None,
        ),
    ]

    summary = summarize_predictions(
        records,
        predictions={
            "vlm_v2_0001": {
                "decision": "ACCEPTED_CATEGORY_MATCH",
                "category_name": "pothole",
            },
            "vlm_v2_0002": {
                "decision": "REJECTED",
                "category_name": None,
            },
            "vlm_v2_0003": {
                "decision": "ACCEPTED_CATEGORY_MATCH",
                "category_name": "pothole",
            },
        },
    )

    assert summary["overall_accuracy"] == pytest.approx(2 / 3)
    assert summary["real_negative_reject_rate"] == 1.0
    assert summary["spoof_reject_rate"] == 0.0


def test_load_predictions_cache_rejects_non_object_payload(tmp_path: Path):
    cache_path = tmp_path / "predictions_cache.json"
    cache_path.write_text('["bad"]\n', encoding="utf-8")

    with pytest.raises(DatasetBuildError, match="did not load as a JSON object"):
        load_predictions_cache(cache_path)


def test_call_gateway_for_manifest_skips_cached_predictions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    dataset_root = tmp_path / "dataset"
    image_dir = dataset_root / "images" / "test" / "pothole"
    image_dir.mkdir(parents=True)
    first_image = image_dir / "vlm_v2_0001.jpg"
    second_image = image_dir / "vlm_v2_0002.jpg"
    Image.new("RGB", (512, 384), color=(1, 2, 3)).save(first_image, format="JPEG")
    Image.new("RGB", (512, 384), color=(4, 5, 6)).save(second_image, format="JPEG")

    records = [
        _build_manifest_record(
            sample_id="vlm_v2_0001",
            relative_image_path="images/test/pothole/vlm_v2_0001.jpg",
        ),
        _build_manifest_record(
            sample_id="vlm_v2_0002",
            relative_image_path="images/test/pothole/vlm_v2_0002.jpg",
        ),
    ]

    cache_path = tmp_path / "cache" / "predictions_cache.json"
    save_predictions_cache(
        cache_path,
        {
            "vlm_v2_0001": {
                "decision": "ACCEPTED_CATEGORY_MATCH",
                "category_name": "pothole",
            }
        },
    )

    calls: list[str] = []

    class FakeResponse:
        def __init__(self, sample_id: str):
            self.sample_id = sample_id

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "decision": "ACCEPTED_CATEGORY_MATCH",
                "category_name": "pothole",
                "confidence": 0.95,
                "model_id": "fake-model",
                "model_quantization": "Q8_0",
                "prompt_version": "dataset_eval_v1",
                "raw_primary_result": {},
                "raw_evaluator_result": {},
                "latency_ms": 12,
                "submission_id": self.sample_id,
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url: str, json: dict[str, object]):
            calls.append(str(json["submission_id"]))
            return FakeResponse(str(json["submission_id"]))

    monkeypatch.setattr("tools.dataset_prep.validate_dataset.httpx.Client", FakeClient)

    predictions = call_gateway_for_manifest(
        records,
        dataset_root=dataset_root,
        gateway_url="http://gateway.example.test",
        timeout_seconds=30,
        predictions_cache_path=cache_path,
    )

    assert calls == ["vlm_v2_0002"]
    assert set(predictions) == {"vlm_v2_0001", "vlm_v2_0002"}
    saved = json.loads(cache_path.read_text(encoding="utf-8"))
    assert set(saved) == {"vlm_v2_0001", "vlm_v2_0002"}

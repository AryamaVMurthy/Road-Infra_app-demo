import json
from collections import Counter
from pathlib import Path
import sys

import dspy
from PIL import Image
import pytest


sys.path.append(str(Path(__file__).resolve().parents[2]))


def _load_training_module():
    import importlib.util

    spec = importlib.util.find_spec("tools.dspy_intake.training")
    assert spec is not None, "Expected tools.dspy_intake.training to exist for the optimizer slice."
    return __import__("tools.dspy_intake.training", fromlist=["placeholder"])


def _write_image(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (16, 16), color=color).save(path, format="JPEG")


def _write_stage_export(
    path: Path,
    *,
    stage: str,
    rows: list[dict[str, object]],
    dataset_root: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            relative_image_path = str(row["relative_image_path"])
            _write_image(
                dataset_root / relative_image_path,
                color=(20 * (len(relative_image_path) % 10), 80, 160),
            )
            handle.write(json.dumps(row) + "\n")


def _level1_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index in range(4):
        rows.append(
            {
                "label": "in_scope_category_image",
                "relative_image_path": f"images/train/pothole/pothole_{index}.jpg",
                "sample_id": f"pothole_{index}",
                "split": "train",
                "subgroup": "accepted/pothole",
            }
        )
        rows.append(
            {
                "label": "in_scope_category_image",
                "relative_image_path": f"images/train/damaged_road_sign/sign_{index}.jpg",
                "sample_id": f"sign_{index}",
                "split": "train",
                "subgroup": "accepted/damaged_road_sign",
            }
        )
        rows.append(
            {
                "label": "spoof_or_out_of_scope",
                "relative_image_path": (
                    f"images/train/rejected_real_irrelevant/real_{index}.jpg"
                ),
                "sample_id": f"real_{index}",
                "split": "train",
                "subgroup": "rejected_real_irrelevant",
            }
        )
        rows.append(
            {
                "label": "spoof_or_out_of_scope",
                "relative_image_path": (
                    f"images/train/rejected_synthetic_spoof/spoof_{index}.jpg"
                ),
                "sample_id": f"spoof_{index}",
                "split": "train",
                "subgroup": "rejected_synthetic_spoof",
            }
        )
    return rows


def _level2_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for label in ("pothole", "damaged_road", "damaged_road_sign", "garbage_litter"):
        for index in range(4):
            rows.append(
                {
                    "label": label,
                    "relative_image_path": f"images/train/{label}/{label}_{index}.jpg",
                    "sample_id": f"{label}_{index}",
                    "split": "train",
                    "subgroup": f"accepted/{label}",
                }
            )
    return rows


def _build_stage_exports(tmp_path: Path) -> tuple[Path, Path]:
    dataset_root = tmp_path / "dataset"
    export_root = tmp_path / "exports"
    _write_stage_export(
        export_root / "level1_train.jsonl",
        stage="level1",
        rows=_level1_rows(),
        dataset_root=dataset_root,
    )
    _write_stage_export(
        export_root / "level2_train.jsonl",
        stage="level2",
        rows=_level2_rows(),
        dataset_root=dataset_root,
    )
    return dataset_root, export_root


def test_load_stage_examples_converts_rows_into_dspy_examples(tmp_path: Path):
    training = _load_training_module()
    dataset_root, export_root = _build_stage_exports(tmp_path)

    examples = training.load_stage_examples(
        stage="level1",
        export_path=export_root / "level1_train.jsonl",
        dataset_root=dataset_root,
    )

    assert len(examples) == 16
    first_example = examples[0]
    assert isinstance(first_example, dspy.Example)
    assert str(first_example.image).endswith(".jpg")
    assert set(first_example.inputs().keys()) == {"image", "category_catalog"}
    assert set(first_example.labels().keys()) >= {"decision", "category_name", "sample_id", "subgroup"}


def test_load_stage_examples_rejects_rows_from_the_wrong_split(tmp_path: Path):
    training = _load_training_module()
    dataset_root, export_root = _build_stage_exports(tmp_path)
    train_path = export_root / "level1_train.jsonl"
    rows = [json.loads(line) for line in train_path.read_text(encoding="utf-8").splitlines()]
    rows[0]["split"] = "test"
    train_path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="expected split `train`"):
        training.load_stage_examples(
            stage="level1",
            export_path=train_path,
            dataset_root=dataset_root,
            expected_split="train",
        )


def test_stratified_split_keeps_every_subgroup_in_train_and_val(tmp_path: Path):
    training = _load_training_module()
    dataset_root, export_root = _build_stage_exports(tmp_path)
    examples = training.load_stage_examples(
        stage="level1",
        export_path=export_root / "level1_train.jsonl",
        dataset_root=dataset_root,
        expected_split="train",
    )

    train_examples, val_examples = training.stratified_split_examples(
        examples,
        val_fraction=0.25,
        seed=17,
    )

    train_counts = Counter(example.subgroup for example in train_examples)
    val_counts = Counter(example.subgroup for example in val_examples)
    assert set(train_counts) == {
        "accepted/pothole",
        "accepted/damaged_road_sign",
        "rejected_real_irrelevant",
        "rejected_synthetic_spoof",
    }
    assert set(val_counts) == set(train_counts)
    assert all(count == 3 for count in train_counts.values())
    assert all(count == 1 for count in val_counts.values())


def test_rebalance_examples_downsamples_to_the_smallest_subgroup_count():
    training = _load_training_module()
    examples = []
    subgroup_sizes = {
        "accepted/pothole": 6,
        "accepted/damaged_road": 3,
        "accepted/damaged_road_sign": 4,
        "accepted/garbage_litter": 5,
    }
    for subgroup, size in subgroup_sizes.items():
        label = subgroup.split("/", 1)[1]
        for index in range(size):
            examples.append(
                dspy.Example(
                    image=f"{subgroup}_{index}.jpg",
                    category_catalog=dict(training.DEFAULT_CATEGORY_CATALOG),
                    category_name=label,
                    sample_id=f"{subgroup}_{index}",
                    subgroup=subgroup,
                ).with_inputs("image", "category_catalog")
            )

    rebalanced = training.rebalance_examples(examples, seed=17)
    counts = Counter(example.subgroup for example in rebalanced)

    assert counts == {
        "accepted/pothole": 3,
        "accepted/damaged_road": 3,
        "accepted/damaged_road_sign": 3,
        "accepted/garbage_litter": 3,
    }


def test_augment_level2_examples_with_hints_emits_empty_correct_and_adversarial_variants():
    training = _load_training_module()
    example = dspy.Example(
        image="pothole_0.jpg",
        category_catalog=dict(training.DEFAULT_CATEGORY_CATALOG),
        category_name="pothole",
        sample_id="pothole_0",
        subgroup="accepted/pothole",
    ).with_inputs("image", "category_catalog")

    augmented = training.augment_level2_examples_with_hints([example])

    assert len(augmented) == 3
    observed_hints = sorted(
        getattr(augmented_example, "best_matching_category_hint")
        for augmented_example in augmented
    )
    assert observed_hints == ["", "damaged_road", "pothole"]
    assert all(
        set(augmented_example.inputs().keys())
        == {"image", "category_catalog", "best_matching_category_hint"}
        for augmented_example in augmented
    )


def test_gepa_harness_wires_reflection_lm_and_multimodal_instruction_proposer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    training = _load_training_module()
    dataset_root, export_root = _build_stage_exports(tmp_path)
    output_root = tmp_path / "artifacts"
    calls: dict[str, object] = {}

    class FakeLM:
        def __init__(self, *, model_name: str):
            self.model_name = model_name

    class FakeCompiledProgram:
        def __init__(self):
            self.saved = []

        def save(self, path, save_program=False, modules_to_serialize=None):
            path = Path(path)
            path.mkdir(parents=True, exist_ok=True)
            (path / "program.txt").write_text("compiled", encoding="utf-8")
            self.saved.append(
                {
                    "path": path,
                    "save_program": save_program,
                    "modules_to_serialize": tuple(modules_to_serialize or ()),
                }
            )

    class FakeOptimizer:
        def __init__(self, **kwargs):
            calls["optimizer_kwargs"] = kwargs
            self.stats = {"best_score": 0.8}

        def compile(self, student, *, trainset, valset):
            calls["compile"] = {
                "student_type": type(student).__name__,
                "train_count": len(trainset),
                "val_count": len(valset),
            }
            return FakeCompiledProgram()

    def fake_lm_factory(*, model_name: str, api_key_env: str, api_base_env: str | None):
        calls.setdefault("lm_requests", []).append(
            {
                "model_name": model_name,
                "api_key_env": api_key_env,
                "api_base_env": api_base_env,
            }
        )
        return FakeLM(model_name=model_name)

    run = training.train_stage(
        stage="level1",
        optimizer_kind="gepa",
        dataset_root=dataset_root,
        export_path=export_root / "level1_train.jsonl",
        output_root=output_root,
        task_model_name="gpt-5.4-mini",
        reflection_model_name="gpt-5.4-mini",
        api_key_env="OPENAI_API_KEY",
        api_base_env="OPENAI_BASE_URL",
        val_fraction=0.25,
        seed=17,
        lm_factory=fake_lm_factory,
        optimizer_factory=FakeOptimizer,
    )

    summary = json.loads(run.summary_path.read_text(encoding="utf-8"))
    assert summary["stage"] == "level1"
    assert summary["optimizer_kind"] == "gepa"
    assert summary["dataset"]["train_count"] == 12
    assert summary["dataset"]["val_count"] == 4
    assert summary["compile_stats"] == {"best_score": 0.8}
    assert calls["compile"]["student_type"] == "Level1ScopeClassifier"
    assert len(calls["lm_requests"]) == 2
    assert calls["optimizer_kwargs"]["reflection_lm"].model_name == "openai/gpt-5.4-mini"
    assert calls["optimizer_kwargs"]["instruction_proposer"].__class__.__name__ == (
        "MultiModalInstructionProposer"
    )
    assert run.program_path.joinpath("program.txt").is_file()
    assert run.run_root == output_root / "level1" / "gepa"


def test_level2_harness_rebalances_trainset_and_records_balanced_counts(
    tmp_path: Path,
):
    training = _load_training_module()
    dataset_root = tmp_path / "dataset"
    export_root = tmp_path / "exports"
    output_root = tmp_path / "artifacts"
    rows = []
    for label, size in (
        ("pothole", 8),
        ("damaged_road", 4),
        ("damaged_road_sign", 4),
        ("garbage_litter", 4),
    ):
        for index in range(size):
            rows.append(
                {
                    "label": label,
                    "relative_image_path": f"images/train/{label}/{label}_{index}.jpg",
                    "sample_id": f"{label}_{index}",
                    "split": "train",
                    "subgroup": f"accepted/{label}",
                }
            )

    _write_stage_export(
        export_root / "level2_train.jsonl",
        stage="level2",
        rows=rows,
        dataset_root=dataset_root,
    )
    calls = {}

    class FakeLM:
        def __init__(self, *, model_name: str):
            self.model_name = model_name

    class FakeCompiledProgram:
        def save(self, path, save_program=False, modules_to_serialize=None):
            path = Path(path)
            path.mkdir(parents=True, exist_ok=True)
            (path / "program.txt").write_text("compiled", encoding="utf-8")

    class FakeOptimizer:
        def __init__(self, **kwargs):
            self.stats = {"best_score": 0.5}

        def compile(self, student, *, trainset, valset):
            calls["train_counts"] = Counter(example.subgroup for example in trainset)
            calls["train_hint_counts"] = Counter(
                getattr(example, "best_matching_category_hint") for example in trainset
            )
            calls["train_count"] = len(trainset)
            calls["val_count"] = len(valset)
            return FakeCompiledProgram()

    training.train_stage(
        stage="level2",
        optimizer_kind="mipro",
        dataset_root=dataset_root,
        export_path=export_root / "level2_train.jsonl",
        output_root=output_root,
        task_model_name="gpt-5.4-mini",
        reflection_model_name=None,
        api_key_env=None,
        api_base_env=None,
        val_fraction=0.25,
        seed=17,
        lm_factory=lambda **kwargs: FakeLM(model_name=kwargs["model_name"]),
        optimizer_factory=FakeOptimizer,
    )

    summary = json.loads(
        (output_root / "level2" / "mipro" / "summary.json").read_text(encoding="utf-8")
    )
    assert summary["dataset"]["raw_train_count"] == 15
    assert summary["dataset"]["balanced_train_count"] == 12
    assert summary["dataset"]["train_count"] == 36
    assert summary["dataset"]["val_count"] == 15
    assert summary["dataset"]["train_subgroup_counts"] == {
        "accepted/damaged_road": 3,
        "accepted/damaged_road_sign": 3,
        "accepted/garbage_litter": 3,
        "accepted/pothole": 3,
    }
    assert summary["dataset"]["train_hint_variant_counts"] == {
        "": 12,
        "damaged_road": 12,
        "damaged_road_sign": 3,
        "garbage_litter": 3,
        "pothole": 6,
    }
    assert calls["train_counts"] == Counter(
        {
            subgroup: count * 3
            for subgroup, count in summary["dataset"]["train_subgroup_counts"].items()
        }
    )
    assert calls["train_hint_counts"] == Counter(summary["dataset"]["train_hint_variant_counts"])
    assert calls["train_count"] == 36
    assert calls["val_count"] == 15


def test_mipro_harness_saves_compiled_artifacts_without_reflection_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    training = _load_training_module()
    dataset_root, export_root = _build_stage_exports(tmp_path)
    output_root = tmp_path / "artifacts"
    calls: dict[str, object] = {}

    class FakeLM:
        def __init__(self, *, model_name: str):
            self.model_name = model_name

    class FakeCompiledProgram:
        def save(self, path, save_program=False, modules_to_serialize=None):
            path = Path(path)
            path.mkdir(parents=True, exist_ok=True)
            (path / "program.txt").write_text("compiled", encoding="utf-8")

    class FakeOptimizer:
        def __init__(self, **kwargs):
            calls["optimizer_kwargs"] = kwargs
            self.stats = {"best_score": 0.7}

        def compile(self, student, *, trainset, valset):
            calls["compile"] = {
                "student_type": type(student).__name__,
                "train_count": len(trainset),
                "val_count": len(valset),
            }
            return FakeCompiledProgram()

    def fake_lm_factory(*, model_name: str, api_key_env: str, api_base_env: str | None):
        calls.setdefault("lm_requests", []).append(
            {
                "model_name": model_name,
                "api_key_env": api_key_env,
                "api_base_env": api_base_env,
            }
        )
        return FakeLM(model_name=model_name)

    run = training.train_stage(
        stage="level2",
        optimizer_kind="mipro",
        dataset_root=dataset_root,
        export_path=export_root / "level2_train.jsonl",
        output_root=output_root,
        task_model_name="gpt-5.4-mini",
        reflection_model_name=None,
        api_key_env="OPENAI_API_KEY",
        api_base_env="OPENAI_BASE_URL",
        val_fraction=0.25,
        seed=17,
        lm_factory=fake_lm_factory,
        optimizer_factory=FakeOptimizer,
    )

    summary = json.loads(run.summary_path.read_text(encoding="utf-8"))
    assert summary["stage"] == "level2"
    assert summary["optimizer_kind"] == "mipro"
    assert summary["dataset"]["balanced_train_count"] == 12
    assert summary["dataset"]["train_count"] == 36
    assert summary["dataset"]["val_count"] == 12
    assert summary["compile_stats"] == {"best_score": 0.7}
    assert calls["compile"]["student_type"] == "Level2CategoryClassifier"
    assert calls["compile"]["train_count"] == 36
    assert calls["compile"]["val_count"] == 12
    assert len(calls["lm_requests"]) == 1
    assert calls["optimizer_kwargs"]["prompt_model"].model_name == "openai/gpt-5.4-mini"
    assert calls["optimizer_kwargs"]["task_model"].model_name == "openai/gpt-5.4-mini"
    assert run.program_path.joinpath("program.txt").is_file()
    assert run.run_root == output_root / "level2" / "mipro"


def test_build_lm_requires_present_api_key_env(monkeypatch: pytest.MonkeyPatch):
    training = _load_training_module()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        training.build_lm(
            model_name="gpt-5.4-mini",
            api_key_env="OPENAI_API_KEY",
            api_base_env=None,
        )


def test_build_lm_requires_present_api_base_env_when_requested(monkeypatch: pytest.MonkeyPatch):
    training = _load_training_module()
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    with pytest.raises(ValueError, match="OPENAI_BASE_URL"):
        training.build_lm(
            model_name="gpt-5.4-mini",
            api_key_env="OPENAI_API_KEY",
            api_base_env="OPENAI_BASE_URL",
        )


def test_train_stage_rejects_non_gpt_5_4_mini_models(tmp_path: Path):
    training = _load_training_module()
    dataset_root, export_root = _build_stage_exports(tmp_path)

    with pytest.raises(ValueError, match="gpt-5.4-mini"):
        training.train_stage(
            stage="level1",
            optimizer_kind="gepa",
            dataset_root=dataset_root,
            export_path=export_root / "level1_train.jsonl",
            output_root=tmp_path / "artifacts",
            task_model_name="gpt-4.1-mini",
            reflection_model_name="gpt-5.4-mini",
            api_key_env=None,
            api_base_env=None,
            val_fraction=0.25,
            seed=17,
            lm_factory=lambda **kwargs: object(),
            optimizer_factory=lambda **kwargs: object(),
        )


def test_run_cli_allows_fixed_stage_entrypoints_without_stage_flags(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    training = _load_training_module()
    dataset_root, export_root = _build_stage_exports(tmp_path)
    output_root = tmp_path / "artifacts"
    seen = {}

    def fake_train_stage(**kwargs):
        seen.update(kwargs)
        run_root = Path(kwargs["output_root"]) / "level1_gepa"
        program_path = run_root / "program"
        summary_path = run_root / "summary.json"
        program_path.mkdir(parents=True, exist_ok=True)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text("{}", encoding="utf-8")
        return training.TrainingRunArtifacts(
            run_root=run_root,
            program_path=program_path,
            summary_path=summary_path,
        )

    monkeypatch.setattr(training, "train_stage", fake_train_stage)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "train_level1_gepa.py",
            "--dataset-root",
            str(dataset_root),
            "--export-path",
            str(export_root / "level1_train.jsonl"),
            "--output-root",
            str(output_root),
            "--task-model-name",
            "gpt-5.4-mini",
            "--reflection-model-name",
            "gpt-5.4-mini",
        ],
    )

    result = training.run_cli(stage="level1", optimizer_kind="gepa")

    assert result == 0
    assert seen["stage"] == "level1"
    assert seen["optimizer_kind"] == "gepa"


def test_load_compiled_program_uses_dspy_load_for_saved_program_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    training = _load_training_module()
    run_root = tmp_path / "level1" / "gepa"
    program_dir = run_root / "program"
    program_dir.mkdir(parents=True)
    (run_root / "summary.json").write_text(
        json.dumps(
            {
                "task_model_name": "openai/gpt-5.4-mini",
                "api_key_env": "OPENAI_API_KEY",
                "api_base_env": None,
            }
        ),
        encoding="utf-8",
    )
    seen = {}

    def fake_dspy_load(path, allow_pickle=False):
        seen["path"] = path
        seen["allow_pickle"] = allow_pickle
        return object()

    def fake_build_lm(*, model_name, api_key_env, api_base_env, **kwargs):
        seen["lm"] = {
            "model_name": model_name,
            "api_key_env": api_key_env,
            "api_base_env": api_base_env,
            **kwargs,
        }
        return "configured-lm"

    def fake_configure(*, lm):
        seen["configured_lm"] = lm

    monkeypatch.setattr(training, "build_lm", fake_build_lm)
    monkeypatch.setattr(training.dspy, "configure", fake_configure)
    monkeypatch.setattr(training.dspy, "load", fake_dspy_load)

    loaded = training.load_compiled_program(program_dir)

    assert loaded is not None
    assert seen == {
        "lm": {
            "model_name": "openai/gpt-5.4-mini",
            "api_key_env": "OPENAI_API_KEY",
            "api_base_env": None,
            "temperature": 1.0,
        },
        "configured_lm": "configured-lm",
        "path": str(program_dir),
        "allow_pickle": True,
    }


def test_load_compiled_program_fails_fast_when_summary_metadata_is_missing(
    tmp_path: Path,
):
    training = _load_training_module()
    program_dir = tmp_path / "program"
    program_dir.mkdir()

    with pytest.raises(ValueError, match="summary.json"):
        training.load_compiled_program(program_dir)

"""Training helpers for two-stage DSPy intake optimization."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import json
import os
from pathlib import Path
import random
import sys
from typing import Callable, Literal

import dspy
from dspy.teleprompt.gepa.instruction_proposal import MultiModalInstructionProposer

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from tools.dataset_prep.common import DatasetBuildError
from tools.dspy_intake.constants import (
    LEVEL1_NEGATIVE_LABEL,
    LEVEL1_POSITIVE_LABEL,
    LEVEL2_ALLOWED_LABELS,
)
from tools.dspy_intake.metrics import level1_metric, level2_metric
from tools.dspy_intake.programs import Level1ScopeClassifier, Level2CategoryClassifier


DEFAULT_CATEGORY_CATALOG: dict[str, str] = {
    "pothole": "Broken or missing road surface forming a visible hole or cavity.",
    "damaged_road": "Cracked, eroded, or broken road surface without a discrete pothole cavity.",
    "damaged_road_sign": "Missing, broken, bent, or unreadable roadside sign infrastructure.",
    "garbage_litter": "Visible dumped waste or litter accumulation in public roadside space.",
}
LEVEL2_ADVERSARIAL_HINTS: dict[str, str] = {
    "pothole": "damaged_road",
    "damaged_road": "pothole",
    "damaged_road_sign": "damaged_road",
    "garbage_litter": "damaged_road",
}
OPENAI_MODEL_ID = "gpt-5.4-mini"
OPENAI_DSPY_MODEL_ID = f"openai/{OPENAI_MODEL_ID}"
DEFAULT_INFERENCE_TEMPERATURE = 1.0
STAGE_NAME = Literal["level1", "level2"]
OPTIMIZER_NAME = Literal["gepa", "mipro"]
DATASET_SPLIT = Literal["train", "test"]


@dataclass(frozen=True, slots=True)
class TrainingRunArtifacts:
    run_root: Path
    program_path: Path
    summary_path: Path


def build_lm(
    *,
    model_name: str,
    api_key_env: str | None,
    api_base_env: str | None,
    temperature: float = 1.0,
    max_tokens: int = 4000,
):
    _validate_model_name(model_name, field_name="model_name")
    kwargs: dict[str, object] = {
        "temperature": temperature,
        "max_tokens": max_tokens,
        "cache": False,
    }
    if api_key_env is not None:
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise ValueError(
                f"Required API key environment variable `{api_key_env}` is not set. "
                "Export it before running DSPy optimization."
            )
        kwargs["api_key"] = api_key
    if api_base_env is not None:
        api_base = os.environ.get(api_base_env)
        if not api_base:
            raise ValueError(
                f"Required API base environment variable `{api_base_env}` is not set. "
                "Export it before running DSPy optimization."
            )
        kwargs["api_base"] = api_base
    return dspy.LM(_canonicalize_model_name(model_name), **kwargs)


def load_stage_examples(
    *,
    stage: STAGE_NAME,
    export_path: Path,
    dataset_root: Path,
    category_catalog: dict[str, str] | None = None,
    expected_split: DATASET_SPLIT | None = None,
) -> list[dspy.Example]:
    resolved_export_path = Path(export_path)
    resolved_dataset_root = Path(dataset_root)
    if not resolved_export_path.is_file():
        raise DatasetBuildError(
            f"DSPy stage export `{resolved_export_path}` does not exist. "
            "Generate the DSPy exports before running optimization."
        )
    catalog = dict(category_catalog or DEFAULT_CATEGORY_CATALOG)
    if set(catalog) != set(LEVEL2_ALLOWED_LABELS):
        raise DatasetBuildError(
            "DSPy category catalog must exactly match the benchmark label vocabulary "
            f"{LEVEL2_ALLOWED_LABELS}, got {tuple(catalog)}."
        )
    catalog = {label: catalog[label] for label in LEVEL2_ALLOWED_LABELS}

    examples: list[dspy.Example] = []
    with resolved_export_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DatasetBuildError(
                    f"DSPy stage export `{resolved_export_path}` has malformed JSON at line "
                    f"{line_number}.\nRoot cause:\n{exc}"
                ) from exc
            examples.append(
                _build_example_from_row(
                    stage=stage,
                    row=row,
                    dataset_root=resolved_dataset_root,
                    category_catalog=catalog,
                    expected_split=expected_split,
                )
            )
    if not examples:
        raise DatasetBuildError(
            f"DSPy stage export `{resolved_export_path}` contains no examples."
        )
    return examples


def _build_example_from_row(
    *,
    stage: STAGE_NAME,
    row: dict[str, object],
    dataset_root: Path,
    category_catalog: dict[str, str],
    expected_split: DATASET_SPLIT | None,
) -> dspy.Example:
    sample_id = _require_row_string(row, "sample_id")
    subgroup = _require_row_string(row, "subgroup")
    split = _require_row_string(row, "split")
    if expected_split is not None and split != expected_split:
        raise ValueError(
            f"DSPy sample `{sample_id}` has split `{split}` but expected split "
            f"`{expected_split}`."
        )
    relative_image_path = _require_row_string(row, "relative_image_path")
    image_path = dataset_root / relative_image_path
    if not image_path.is_file():
        raise DatasetBuildError(
            f"DSPy example `{sample_id}` references missing image `{image_path}`."
        )

    if stage == "level1":
        label = _require_row_string(row, "label")
        if label == LEVEL1_POSITIVE_LABEL:
            if not subgroup.startswith("accepted/"):
                raise DatasetBuildError(
                    f"DSPy level1 sample `{sample_id}` has invalid accepted subgroup `{subgroup}`."
                )
            category_name = subgroup.split("/", 1)[1]
            decision = "IN_SCOPE"
        elif label == LEVEL1_NEGATIVE_LABEL:
            category_name = None
            decision = "REJECT"
        else:
            raise DatasetBuildError(
                f"DSPy level1 sample `{sample_id}` has unsupported label `{label}`."
            )
        return dspy.Example(
            image=str(image_path),
            category_catalog=dict(category_catalog),
            decision=decision,
            category_name=category_name,
            sample_id=sample_id,
            subgroup=subgroup,
        ).with_inputs("image", "category_catalog")

    label = _require_row_string(row, "label")
    if label not in LEVEL2_ALLOWED_LABELS:
        raise DatasetBuildError(
            f"DSPy level2 sample `{sample_id}` has unsupported label `{label}`."
        )
    return dspy.Example(
        image=str(image_path),
        category_catalog=dict(category_catalog),
        category_name=label,
        sample_id=sample_id,
        subgroup=subgroup,
    ).with_inputs("image", "category_catalog")


def _require_row_string(row: dict[str, object], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise DatasetBuildError(
            f"DSPy stage export row is missing required string field `{key}`: {row!r}"
        )
    return value.strip()


def stratified_split_examples(
    examples: list[dspy.Example],
    *,
    val_fraction: float,
    seed: int,
) -> tuple[list[dspy.Example], list[dspy.Example]]:
    if not 0.0 < val_fraction < 1.0:
        raise ValueError(
            f"`val_fraction` must be between 0 and 1, got {val_fraction!r}."
        )
    grouped_examples: dict[str, list[dspy.Example]] = defaultdict(list)
    for example in examples:
        subgroup = getattr(example, "subgroup", None)
        if not isinstance(subgroup, str) or not subgroup:
            raise ValueError(
                f"Every DSPy example must include a non-empty `subgroup`, got {subgroup!r}."
            )
        grouped_examples[subgroup].append(example)

    train_examples: list[dspy.Example] = []
    val_examples: list[dspy.Example] = []
    rng = random.Random(seed)

    for subgroup, subgroup_examples in sorted(grouped_examples.items()):
        if len(subgroup_examples) < 2:
            raise ValueError(
                f"Subgroup `{subgroup}` needs at least 2 examples for a train/val split, "
                f"got {len(subgroup_examples)}."
            )
        ordered = sorted(subgroup_examples, key=lambda example: str(example.sample_id))
        rng.shuffle(ordered)
        val_count = max(1, round(len(ordered) * val_fraction))
        if val_count >= len(ordered):
            val_count = len(ordered) - 1
        val_examples.extend(ordered[:val_count])
        train_examples.extend(ordered[val_count:])

    return train_examples, val_examples


def rebalance_examples(
    examples: list[dspy.Example],
    *,
    seed: int,
) -> list[dspy.Example]:
    grouped_examples: dict[str, list[dspy.Example]] = defaultdict(list)
    for example in examples:
        subgroup = getattr(example, "subgroup", None)
        if not isinstance(subgroup, str) or not subgroup:
            raise ValueError(
                f"Every DSPy example must include a non-empty `subgroup`, got {subgroup!r}."
            )
        grouped_examples[subgroup].append(example)

    if not grouped_examples:
        raise ValueError("Cannot rebalance an empty DSPy example set.")

    target_count = min(len(subgroup_examples) for subgroup_examples in grouped_examples.values())
    if target_count < 1:
        raise ValueError("DSPy subgroup rebalancing requires at least one example per subgroup.")

    rng = random.Random(seed)
    rebalanced_examples: list[dspy.Example] = []
    for subgroup, subgroup_examples in sorted(grouped_examples.items()):
        ordered = sorted(subgroup_examples, key=lambda example: str(example.sample_id))
        if len(ordered) > target_count:
            rng.shuffle(ordered)
            ordered = sorted(
                ordered[:target_count],
                key=lambda example: str(example.sample_id),
            )
        rebalanced_examples.extend(ordered)
    return rebalanced_examples


def augment_level2_examples_with_hints(
    examples: list[dspy.Example],
) -> list[dspy.Example]:
    if set(LEVEL2_ADVERSARIAL_HINTS) != set(LEVEL2_ALLOWED_LABELS):
        raise ValueError(
            "Level 2 adversarial hint map must exactly cover the allowed label vocabulary "
            f"{LEVEL2_ALLOWED_LABELS}, got {tuple(sorted(LEVEL2_ADVERSARIAL_HINTS))}."
        )

    augmented_examples: list[dspy.Example] = []
    for example in examples:
        category_name = getattr(example, "category_name", None)
        if not isinstance(category_name, str) or category_name not in LEVEL2_ALLOWED_LABELS:
            raise ValueError(
                "Level 2 hint augmentation requires examples with a valid `category_name`, "
                f"got {category_name!r}."
            )
        for hint_variant in (
            "",
            category_name,
            LEVEL2_ADVERSARIAL_HINTS[category_name],
        ):
            augmented_examples.append(
                dspy.Example(
                    image=example.image,
                    category_catalog=example.category_catalog,
                    best_matching_category_hint=hint_variant,
                    category_name=category_name,
                    sample_id=getattr(example, "sample_id", ""),
                    subgroup=getattr(example, "subgroup", ""),
                ).with_inputs("image", "category_catalog", "best_matching_category_hint")
            )
    return augmented_examples


def train_stage(
    *,
    stage: STAGE_NAME,
    optimizer_kind: OPTIMIZER_NAME,
    dataset_root: Path,
    export_path: Path,
    output_root: Path,
    task_model_name: str,
    reflection_model_name: str | None,
    api_key_env: str | None,
    api_base_env: str | None,
    val_fraction: float,
    seed: int,
    optimizer_auto: Literal["light", "medium", "heavy"] = "medium",
    lm_factory: Callable[..., object] = build_lm,
    optimizer_factory: Callable[..., object] | None = None,
) -> TrainingRunArtifacts:
    _validate_model_name(task_model_name, field_name="task_model_name")
    canonical_task_model_name = _canonicalize_model_name(task_model_name)
    if optimizer_kind == "gepa":
        if reflection_model_name is None:
            raise ValueError("GEPA requires a `reflection_model_name`.")
        _validate_model_name(
            reflection_model_name,
            field_name="reflection_model_name",
        )
        canonical_reflection_model_name = _canonicalize_model_name(reflection_model_name)
    else:
        canonical_reflection_model_name = None
    examples = load_stage_examples(
        stage=stage,
        export_path=export_path,
        dataset_root=dataset_root,
        expected_split="train",
    )
    trainset, valset = stratified_split_examples(examples, val_fraction=val_fraction, seed=seed)
    raw_train_count = len(trainset)
    raw_val_count = len(valset)
    if stage == "level2":
        trainset = rebalance_examples(trainset, seed=seed)
        balanced_train_count = len(trainset)
        train_subgroup_counts = {
            subgroup: len(subgroup_examples)
            for subgroup, subgroup_examples in sorted(
                _group_examples_by_subgroup(trainset).items()
            )
        }
        trainset = augment_level2_examples_with_hints(trainset)
        valset = augment_level2_examples_with_hints(valset)
        train_hint_variant_counts = dict(
            sorted(
                Counter(
                    str(example.best_matching_category_hint)
                    for example in trainset
                ).items()
            )
        )
    else:
        balanced_train_count = len(trainset)
        train_subgroup_counts = {
            subgroup: len(subgroup_examples)
            for subgroup, subgroup_examples in sorted(
                _group_examples_by_subgroup(trainset).items()
            )
        }
        train_hint_variant_counts = None

    task_lm = lm_factory(
        model_name=canonical_task_model_name,
        api_key_env=api_key_env,
        api_base_env=api_base_env,
    )
    dspy.configure(lm=task_lm)

    if stage == "level1":
        student = Level1ScopeClassifier()
        metric = level1_metric
    else:
        student = Level2CategoryClassifier()
        metric = level2_metric

    optimizer = _build_optimizer(
        optimizer_kind=optimizer_kind,
        metric=metric,
        task_lm=task_lm,
        reflection_model_name=canonical_reflection_model_name,
        api_key_env=api_key_env,
        api_base_env=api_base_env,
        auto=optimizer_auto,
        lm_factory=lm_factory,
        optimizer_factory=optimizer_factory,
    )

    compiled_program = optimizer.compile(student, trainset=trainset, valset=valset)

    run_root = Path(output_root) / stage / optimizer_kind
    program_path = run_root / "program"
    program_path.parent.mkdir(parents=True, exist_ok=True)
    compiled_program.save(
        program_path,
        save_program=True,
        modules_to_serialize=[sys.modules[student.__class__.__module__]],
    )

    summary = {
        "stage": stage,
        "optimizer_kind": optimizer_kind,
        "task_model_name": canonical_task_model_name,
        "reflection_model_name": canonical_reflection_model_name,
        "api_key_env": api_key_env,
        "api_base_env": api_base_env,
        "dataset": {
            "raw_train_count": raw_train_count,
            "raw_val_count": raw_val_count,
            "balanced_train_count": balanced_train_count,
            "train_count": len(trainset),
            "val_count": len(valset),
            "train_subgroup_counts": train_subgroup_counts,
            "train_hint_variant_counts": train_hint_variant_counts,
        },
        "compile_stats": getattr(optimizer, "stats", None),
    }
    summary_path = run_root / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return TrainingRunArtifacts(
        run_root=run_root,
        program_path=program_path,
        summary_path=summary_path,
    )


def _group_examples_by_subgroup(
    examples: list[dspy.Example],
) -> dict[str, list[dspy.Example]]:
    grouped_examples: dict[str, list[dspy.Example]] = defaultdict(list)
    for example in examples:
        subgroup = getattr(example, "subgroup", None)
        if not isinstance(subgroup, str) or not subgroup:
            raise ValueError(
                f"Every DSPy example must include a non-empty `subgroup`, got {subgroup!r}."
            )
        grouped_examples[subgroup].append(example)
    return dict(grouped_examples)


def _build_optimizer(
    *,
    optimizer_kind: OPTIMIZER_NAME,
    metric: Callable[..., object],
    task_lm: object,
    reflection_model_name: str | None,
    api_key_env: str | None,
    api_base_env: str | None,
    auto: Literal["light", "medium", "heavy"],
    lm_factory: Callable[..., object],
    optimizer_factory: Callable[..., object] | None,
):
    if optimizer_kind == "gepa":
        reflection_lm = lm_factory(
            model_name=reflection_model_name,
            api_key_env=api_key_env,
            api_base_env=api_base_env,
        )
        factory = optimizer_factory or dspy.GEPA
        return factory(
            metric=metric,
            auto=auto,
            reflection_lm=reflection_lm,
            instruction_proposer=MultiModalInstructionProposer(),
            track_stats=True,
        )

    factory = optimizer_factory or dspy.MIPROv2
    return factory(
        metric=metric,
        auto=auto,
        prompt_model=task_lm,
        task_model=task_lm,
        track_stats=True,
    )


def _validate_model_name(model_name: str, *, field_name: str) -> None:
    if model_name not in {OPENAI_MODEL_ID, OPENAI_DSPY_MODEL_ID}:
        raise ValueError(
            f"DSPy optimization is pinned to `{OPENAI_MODEL_ID}` only; "
            f"`{field_name}` received `{model_name}`."
        )


def _canonicalize_model_name(model_name: str) -> str:
    _validate_model_name(model_name, field_name="model_name")
    return OPENAI_DSPY_MODEL_ID


def load_compiled_program(
    path: Path,
    *,
    temperature: float = DEFAULT_INFERENCE_TEMPERATURE,
):
    resolved_path = Path(path)
    if not resolved_path.exists():
        raise ValueError(
            f"Compiled DSPy program path `{resolved_path}` does not exist."
        )
    summary_path = resolved_path.parent / "summary.json"
    if not summary_path.is_file():
        raise ValueError(
            f"Compiled DSPy program `{resolved_path}` is missing required run metadata "
            f"`{summary_path}`."
        )
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Compiled DSPy program summary `{summary_path}` contains malformed JSON."
        ) from exc

    task_model_name = summary.get("task_model_name")
    if not isinstance(task_model_name, str) or not task_model_name.strip():
        raise ValueError(
            f"Compiled DSPy program summary `{summary_path}` is missing a valid "
            "`task_model_name`."
        )
    api_key_env = summary.get("api_key_env")
    if api_key_env is not None and not isinstance(api_key_env, str):
        raise ValueError(
            f"Compiled DSPy program summary `{summary_path}` has invalid `api_key_env` "
            f"value {api_key_env!r}."
        )
    api_base_env = summary.get("api_base_env")
    if api_base_env is not None and not isinstance(api_base_env, str):
        raise ValueError(
            f"Compiled DSPy program summary `{summary_path}` has invalid `api_base_env` "
            f"value {api_base_env!r}."
        )

    dspy.configure(
        lm=build_lm(
            model_name=task_model_name,
            api_key_env=api_key_env,
            api_base_env=api_base_env,
            temperature=temperature,
        )
    )
    return dspy.load(str(resolved_path), allow_pickle=True)


def _parse_args(
    *,
    fixed_stage: STAGE_NAME | None = None,
    fixed_optimizer_kind: OPTIMIZER_NAME | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a DSPy intake stage optimizer harness.")
    parser.add_argument(
        "--stage",
        choices=("level1", "level2"),
        required=fixed_stage is None,
        default=fixed_stage,
    )
    parser.add_argument(
        "--optimizer-kind",
        choices=("gepa", "mipro"),
        required=fixed_optimizer_kind is None,
        default=fixed_optimizer_kind,
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=Path("artifacts/datasets/vlm_intake_v2"),
    )
    parser.add_argument("--export-path", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/models/intake_dspy"))
    parser.add_argument("--task-model-name", required=True)
    parser.add_argument("--reflection-model-name", default=None)
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--api-base-env", default=None)
    parser.add_argument("--val-fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--optimizer-auto", choices=("light", "medium", "heavy"), default="medium")
    return parser.parse_args()


def run_cli(
    *,
    stage: STAGE_NAME | None = None,
    optimizer_kind: OPTIMIZER_NAME | None = None,
) -> int:
    args = _parse_args(
        fixed_stage=stage,
        fixed_optimizer_kind=optimizer_kind,
    )
    chosen_stage = stage or args.stage
    chosen_optimizer = optimizer_kind or args.optimizer_kind
    if stage is not None and args.stage != stage:
        raise ValueError(
            f"This entrypoint is fixed to stage `{stage}` but received `--stage {args.stage}`."
        )
    if optimizer_kind is not None and args.optimizer_kind != optimizer_kind:
        raise ValueError(
            "This entrypoint is fixed to optimizer "
            f"`{optimizer_kind}` but received `--optimizer-kind {args.optimizer_kind}`."
        )
    artifacts = train_stage(
        stage=chosen_stage,
        optimizer_kind=chosen_optimizer,
        dataset_root=args.dataset_root,
        export_path=args.export_path,
        output_root=args.output_root,
        task_model_name=args.task_model_name,
        reflection_model_name=args.reflection_model_name,
        api_key_env=args.api_key_env,
        api_base_env=args.api_base_env,
        val_fraction=args.val_fraction,
        seed=args.seed,
        optimizer_auto=args.optimizer_auto,
    )
    print(json.dumps({"program_path": str(artifacts.program_path), "summary_path": str(artifacts.summary_path)}))
    return 0


def main() -> int:
    return run_cli()


if __name__ == "__main__":
    raise SystemExit(main())

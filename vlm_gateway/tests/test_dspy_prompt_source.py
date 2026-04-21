from pathlib import Path

import dspy
import pytest

from vlm_gateway.app import prompts


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROGRAM_PATH = (
    PROJECT_ROOT / "artifacts" / "models" / "intake_dspy" / "level1" / "gepa" / "program"
)


def test_load_dspy_level1_prompt_source_reads_exact_compiled_instructions():
    expected_program = dspy.load(str(DEFAULT_PROGRAM_PATH), allow_pickle=True)
    expected_instructions = expected_program.predictor.signature.instructions

    prompt_source = prompts.load_dspy_level1_prompt_source(DEFAULT_PROGRAM_PATH)

    assert prompt_source.instructions == expected_instructions
    assert prompt_source.output_field_names == (
        "decision",
        "best_matching_category_hint",
        "rationale",
    )


def test_load_dspy_level1_prompt_source_fails_fast_when_program_path_is_missing(tmp_path: Path):
    with pytest.raises(ValueError, match="does not exist"):
        prompts.load_dspy_level1_prompt_source(tmp_path / "missing-program")

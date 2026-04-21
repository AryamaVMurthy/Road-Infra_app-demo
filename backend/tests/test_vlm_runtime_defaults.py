import inspect
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.app.core.config import Settings
from vlm_gateway.app.llama_client import (
    DEFAULT_DSPY_LEVEL1_PROGRAM_PATH,
    create_llama_classifier,
)
from vlm_gateway.app.main import create_app


def test_backend_default_vlm_timeout_is_sized_for_dataset_benchmark_runs():
    assert Settings.model_fields["VLM_TIMEOUT_SECONDS"].default == 240


def test_gateway_default_result_timeout_is_sized_for_dataset_benchmark_runs():
    signature = inspect.signature(create_app)

    assert signature.parameters["result_timeout_seconds"].default == 240


def test_llama_classifier_default_timeout_is_sized_for_cpu_benchmark_runs():
    signature = inspect.signature(create_llama_classifier)

    assert signature.parameters["timeout_seconds"].default == 180


def test_default_dspy_level1_program_artifact_is_present_in_repo():
    assert DEFAULT_DSPY_LEVEL1_PROGRAM_PATH.exists()
    assert (DEFAULT_DSPY_LEVEL1_PROGRAM_PATH / "program.pkl").is_file()
    assert (DEFAULT_DSPY_LEVEL1_PROGRAM_PATH / "metadata.json").is_file()

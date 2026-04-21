from __future__ import annotations

import importlib
import sys


def _clear_modules() -> None:
    for module_name in [
        "tools.dspy_intake",
        "tools.dspy_intake.export_datasets",
        "tools.dspy_intake.signatures",
        "tools.dataset_prep.common",
    ]:
        sys.modules.pop(module_name, None)


def test_importing_tools_dspy_intake_does_not_import_dataset_export_stack():
    _clear_modules()

    importlib.import_module("tools.dspy_intake")

    assert "tools.dspy_intake.export_datasets" not in sys.modules
    assert "tools.dataset_prep.common" not in sys.modules


def test_importing_signatures_does_not_import_dataset_prep_modules():
    _clear_modules()

    importlib.import_module("tools.dspy_intake.signatures")

    assert "tools.dspy_intake.export_datasets" not in sys.modules
    assert "tools.dataset_prep.common" not in sys.modules

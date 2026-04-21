# DSPy Dataset Export Red-Run Equivalence Check

This note records an isolated equivalence check that I ran on `2026-04-20`
after `tools/dspy_intake/export_datasets.py` already existed in this worktree.
It is not a claim about earlier history. The purpose was to make the original
red-first failure signature auditable from the worktree by recreating the
pre-implementation condition in a temporary repo-shaped directory that contains
`tools/__init__.py` but does not contain `tools/dspy_intake/`.

## Exact Command Run

```bash
../../.venv/bin/python - <<'PY'
import os
import subprocess
import tempfile
import textwrap
from pathlib import Path

root = Path(tempfile.mkdtemp(prefix='dspy-red-equivalence-'))
(root / 'backend' / 'tests').mkdir(parents=True)
(root / 'tools').mkdir(parents=True)
(root / 'tools' / '__init__.py').write_text('', encoding='utf-8')
(root / 'backend' / 'tests' / 'test_dspy_dataset_export_red_equivalence.py').write_text(
    textwrap.dedent(
        '''
        from pathlib import Path
        import sys

        sys.path.append(str(Path(__file__).resolve().parents[2]))

        def test_missing_exporter_module():
            from tools.dspy_intake.export_datasets import export_dspy_datasets
        '''
    ).lstrip(),
    encoding='utf-8',
)

env = os.environ.copy()
env['PYTHONPATH'] = 'backend'
proc = subprocess.run(
    [
        str(Path('../../.venv/bin/pytest').resolve()),
        'backend/tests/test_dspy_dataset_export_red_equivalence.py',
        '-q',
    ],
    cwd=root,
    env=env,
    capture_output=True,
    text=True,
)
print(f'tmp_root={root}')
print(proc.stdout, end='')
print(proc.stderr, end='')
raise SystemExit(proc.returncode)
PY
```

## Observed Failure

```text
tmp_root=/tmp/dspy-red-equivalence-eaqwbea9
F                                                                        [100%]
=================================== FAILURES ===================================
_________________________ test_missing_exporter_module _________________________

    def test_missing_exporter_module():
>       from tools.dspy_intake.export_datasets import export_dspy_datasets
E       ModuleNotFoundError: No module named 'tools.dspy_intake'

backend/tests/test_dspy_dataset_export_red_equivalence.py:7: ModuleNotFoundError
=========================== short test summary info ============================
FAILED backend/tests/test_dspy_dataset_export_red_equivalence.py::test_missing_exporter_module
1 failed in 0.01s
```

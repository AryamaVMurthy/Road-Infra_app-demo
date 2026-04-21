from pathlib import Path
import sys


sys.path.append(str(Path(__file__).resolve().parents[2]))

from tools.dspy_intake.training import run_cli


if __name__ == "__main__":
    raise SystemExit(run_cli(stage="level1", optimizer_kind="mipro"))

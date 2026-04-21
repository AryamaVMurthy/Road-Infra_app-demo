from __future__ import annotations

import os
import subprocess
import sys


def build_bootstrap_commands() -> list[list[str]]:
    return [
        [sys.executable, "seed.py"],
        [sys.executable, "scripts/migrate_vlm_intake_schema.py"],
        [sys.executable, "seed.py"],
    ]


def build_server_command() -> list[str]:
    return [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8088",
        "--workers",
        "2",
        "--access-log",
    ]


def main() -> None:
    for command in build_bootstrap_commands():
        subprocess.run(command, check=True)
    os.execvp(build_server_command()[0], build_server_command())


if __name__ == "__main__":
    main()

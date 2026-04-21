from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_start_backend_module():
    root = Path(__file__).resolve().parents[1]
    script_path = root / "start_backend.py"
    spec = spec_from_file_location("start_backend", script_path)
    module = module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_backend_startup_runs_seed_then_migration_then_seed_before_uvicorn():
    module = _load_start_backend_module()

    bootstrap_commands = module.build_bootstrap_commands()
    server_command = module.build_server_command()

    assert bootstrap_commands == [
        [module.sys.executable, "seed.py"],
        [module.sys.executable, "scripts/migrate_vlm_intake_schema.py"],
        [module.sys.executable, "seed.py"],
    ]
    assert server_command[:3] == [module.sys.executable, "-m", "uvicorn"]
    assert server_command[3] == "app.main:app"
    assert "--port" in server_command

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_migration_module():
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "migrate_vlm_intake_schema.py"
    spec = spec_from_file_location("migrate_vlm_intake_schema", script_path)
    module = module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_migration_script_builds_required_postgres_statements():
    module = _load_migration_module()

    statements = module.build_postgres_statements()

    assert any(
        "create table if not exists reportintakesubmission" in statement.lower()
        for statement in statements
    )
    assert any(
        "alter table category add column if not exists classification_guidance"
        in statement.lower()
        for statement in statements
    )
    assert any(
        "alter table issue add column if not exists classification_model_quantization"
        in statement.lower()
        for statement in statements
    )

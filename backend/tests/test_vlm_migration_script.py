from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


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
    assert any(
        "alter table issue alter column category_id drop not null"
        in statement.lower()
        for statement in statements
    )


def test_migration_script_can_build_database_url_from_postgres_env(monkeypatch):
    module = _load_migration_module()

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_SERVER", "db")
    monkeypatch.setenv("POSTGRES_USER", "postgres")
    monkeypatch.setenv("POSTGRES_PASSWORD", "toto")
    monkeypatch.setenv("POSTGRES_DB", "app")

    assert (
        module.resolve_database_url()
        == "postgresql://postgres:toto@db/app"
    )


def test_migration_script_fails_fast_when_no_database_env_is_present(monkeypatch):
    module = _load_migration_module()

    for name in [
        "DATABASE_URL",
        "POSTGRES_SERVER",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
    ]:
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL or POSTGRES_\\*"):
        module.resolve_database_url()

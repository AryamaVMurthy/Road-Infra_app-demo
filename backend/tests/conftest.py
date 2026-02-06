import os
import pytest
from sqlmodel import SQLModel, create_engine, Session
from fastapi.testclient import TestClient
from sqlalchemy import text

db_host = os.getenv("POSTGRES_SERVER", os.getenv("POSTGRES_HOST", "localhost"))
db_name = os.getenv("POSTGRES_DB", "app_test")
db_user = os.getenv("POSTGRES_USER", "postgres")
db_password = os.getenv("POSTGRES_PASSWORD", "toto")

_admin_engine = create_engine(
    f"postgresql://{db_user}:{db_password}@{db_host}/postgres",
    isolation_level="AUTOCOMMIT",
)

with _admin_engine.connect() as conn:
    if not conn.execute(
        text(f"SELECT 1 FROM pg_database WHERE datname='{db_name}'")
    ).fetchone():
        conn.execute(text(f"CREATE DATABASE {db_name}"))

_test_db_url = f"postgresql://{db_user}:{db_password}@{db_host}/{db_name}"

# Test engine — this is the ONLY engine used during tests.
# The app's engine (app.db.session.engine) points at the production DB;
# we never import or use it.
test_engine = create_engine(_test_db_url, echo=True)

_truncate_engine = create_engine(
    _test_db_url,
    isolation_level="AUTOCOMMIT",
    pool_size=1,
    max_overflow=0,
)

from app.main import app as fastapi_app
from app.db.session import get_session
from app.services.minio_client import init_minio

# Ensure all domain models are imported so metadata.sorted_tables is populated
import app.models.domain  # noqa: F401


@pytest.fixture(name="session")
def session_fixture():
    init_minio()

    with test_engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        conn.commit()
    SQLModel.metadata.create_all(test_engine)

    with _truncate_engine.connect() as conn:
        existing = {
            row[0]
            for row in conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            ).fetchall()
        }
        tables = [
            t.name
            for t in reversed(SQLModel.metadata.sorted_tables)
            if t.name in existing
        ]
        if tables:
            names = ", ".join(f'"{t}"' for t in tables)
            conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE;"))

    with Session(test_engine) as session:
        yield session


@pytest.fixture(autouse=True)
def override_app_db_dependency():
    def get_session_override():
        with Session(test_engine) as session:
            yield session

    fastapi_app.dependency_overrides[get_session] = get_session_override
    yield
    fastapi_app.dependency_overrides.pop(get_session, None)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override_for_client():
        return session

    fastapi_app.dependency_overrides[get_session] = get_session_override_for_client
    client = TestClient(fastapi_app)
    yield client
    fastapi_app.dependency_overrides.pop(get_session, None)
    test_engine.dispose()

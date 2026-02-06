import os
import pytest
from sqlmodel import SQLModel, create_engine, Session
from fastapi.testclient import TestClient
from app.main import app as fastapi_app
from app.db.session import get_session
from sqlalchemy import text

# Use a separate test database
db_host = os.getenv("POSTGRES_SERVER", os.getenv("POSTGRES_HOST", "localhost"))
db_name = os.getenv("POSTGRES_DB", "app_test")
db_user = os.getenv("POSTGRES_USER", "postgres")
db_password = os.getenv("POSTGRES_PASSWORD", "toto")

default_url = f"postgresql://{db_user}:{db_password}@{db_host}/postgres"
default_engine = create_engine(default_url, isolation_level="AUTOCOMMIT")

with default_engine.connect() as conn:
    result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname='{db_name}'"))
    if not result.fetchone():
        conn.execute(text(f"CREATE DATABASE {db_name}"))

db_url = f"postgresql://{db_user}:{db_password}@{db_host}/{db_name}"
from app.core.config import settings

settings.DATABASE_URL = db_url

from app.db.session import engine


from app.services.minio_client import init_minio


@pytest.fixture(name="session")
def session_fixture():
    init_minio()

    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        conn.commit()

    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    fastapi_app.dependency_overrides[get_session] = get_session_override
    client = TestClient(fastapi_app)
    yield client
    fastapi_app.dependency_overrides.clear()

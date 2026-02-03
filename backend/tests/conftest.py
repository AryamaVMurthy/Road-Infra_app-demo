import pytest
from sqlmodel import SQLModel, create_engine, Session
from fastapi.testclient import TestClient
from app.main import app as fastapi_app
from app.db.session import get_session
from sqlalchemy import text

# Use a separate test database
sqlite_url = "postgresql://postgres:toto@localhost/app_test"
engine = create_engine(sqlite_url)


from app.services.minio_client import init_minio


@pytest.fixture(name="session")
def session_fixture():
    # Ensure minio bucket exists
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

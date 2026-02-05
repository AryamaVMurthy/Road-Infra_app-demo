from sqlmodel import create_engine, Session
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL or settings.assemble_db_connection(None, settings),
    echo=True,
)


def get_session():
    with Session(engine) as session:
        yield session

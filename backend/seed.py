from sqlmodel import Session, create_engine, SQLModel
from app.models.domain import Zone, Category, User
from app.core.config import settings
from uuid import uuid4
from sqlalchemy import text


def seed_data():
    engine = create_engine(settings.DATABASE_URL)

    # Create extension
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        conn.commit()

    # Create tables
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        # Check if already seeded
        if session.query(Category).first():
            print("Database already seeded.")
            return

        # Seed Categories
        categories = [
            Category(name="Pothole", default_priority="P2", expected_sla_days=3),
            Category(name="Drainage", default_priority="P1", expected_sla_days=2),
            Category(name="Street Light", default_priority="P3", expected_sla_days=5),
            Category(name="Garbage", default_priority="P3", expected_sla_days=1),
        ]
        for c in categories:
            session.add(c)

        # Seed GHMC Zones
        # Polygons for roughly Banjara Hills, Jubilee Hills, etc.
        zones = [
            Zone(
                name="Banjara Hills",
                boundary="SRID=4326;POLYGON((78.43 17.41, 78.45 17.41, 78.45 17.43, 78.43 17.43, 78.43 17.41))",
            ),
            Zone(
                name="Jubilee Hills",
                boundary="SRID=4326;POLYGON((78.39 17.41, 78.41 17.41, 78.41 17.43, 78.39 17.43, 78.39 17.41))",
            ),
            Zone(
                name="Gachibowli",
                boundary="SRID=4326;POLYGON((78.33 17.43, 78.35 17.43, 78.35 17.45, 78.33 17.45, 78.33 17.43))",
            ),
        ]
        for z in zones:
            session.add(z)

        # Seed test users
        users = [
            User(email="admin@ghmc.gov.in", role="ADMIN"),
            User(email="worker@ghmc.gov.in", role="WORKER"),
            User(email="resident@hyderabad.in", role="CITIZEN"),
        ]
        for u in users:
            session.add(u)

        session.commit()
        print("Database seeded successfully.")


if __name__ == "__main__":
    seed_data()

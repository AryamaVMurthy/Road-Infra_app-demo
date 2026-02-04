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

# Seed Jurisdictions
def seed_zones(session: Session):
    zones = [
        {"name": "Central Zone"},
        {"name": "North Zone"},
        {"name": "South Zone"},
        {"name": "East Zone"},
        {"name": "West Zone"},
    ]
        for z in zones:
            session.add(z)

        # Seed test users
        users = [
            User(
                email="sysadmin@marg.gov.in",
                role="SYSADMIN",
                full_name="System Administrator",
            ),
        User(email="admin@authority.gov.in", role="ADMIN", full_name="Authority Admin"),
        User(email="worker@authority.gov.in", role="WORKER", full_name="Field Worker"),
        User(email="worker2@authority.gov.in", role="WORKER", full_name="Field Worker 2"),
        User(email="worker3@authority.gov.in", role="WORKER", full_name="Field Worker 3"),
        User(
            email="citizen@example.com", role="CITIZEN", full_name="Citizen"
        ),
        ]
        for u in users:
            session.add(u)

        session.commit()
        print("Database seeded successfully.")


if __name__ == "__main__":
    seed_data()

import random
from sqlmodel import Session, create_engine, select, SQLModel
from app.models.domain import Category, User, Zone
from app.core.config import settings
import app.models.domain


def seed_data():
    engine = create_engine(
        settings.DATABASE_URL or settings.assemble_db_connection(None, settings)
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        # 1. Seed Categories
        categories = [
            Category(name="Pothole", default_priority="P2", expected_sla_days=3),
            Category(name="Drainage", default_priority="P1", expected_sla_days=2),
            Category(name="Street Light", default_priority="P3", expected_sla_days=5),
            Category(name="Garbage", default_priority="P4", expected_sla_days=1),
        ]
        for c in categories:
            # Check if exists
            existing = session.exec(
                select(Category).where(Category.name == c.name)
            ).first()
            if not existing:
                session.add(c)

        # 2. Seed Zones
        zones = [
            Zone(name="Central Zone", boundary="POLYGON((0 0,1 0,1 1,0 1,0 0))"),
            Zone(name="North Zone", boundary="POLYGON((1 0,2 0,2 1,1 1,1 0))"),
            Zone(name="South Zone", boundary="POLYGON((0 -1,1 -1,1 0,0 0,0 -1))"),
            Zone(name="East Zone", boundary="POLYGON((2 0,3 0,3 1,2 1,2 0))"),
            Zone(name="West Zone", boundary="POLYGON((-1 0,0 0,0 1,-1 1,-1 0))"),
        ]
        for z in zones:
            existing = session.exec(select(Zone).where(Zone.name == z.name)).first()
            if not existing:
                session.add(z)

        # 3. Seed Users
        users = [
            User(
                email="sysadmin@marg.gov.in",
                role="SYSADMIN",
                full_name="System Administrator",
            ),
            User(
                email="admin@authority.gov.in",
                role="ADMIN",
                full_name="Authority Admin",
            ),
            User(
                email="worker@authority.gov.in", role="WORKER", full_name="Field Worker"
            ),
            User(
                email="worker2@authority.gov.in",
                role="WORKER",
                full_name="Field Worker 2",
            ),
            User(
                email="worker3@authority.gov.in",
                role="WORKER",
                full_name="Field Worker 3",
            ),
            User(email="citizen@example.com", role="CITIZEN", full_name="Citizen"),
        ]
        for u in users:
            existing = session.exec(select(User).where(User.email == u.email)).first()
            if not existing:
                session.add(u)

        session.commit()
        print("Database seeded successfully.")


if __name__ == "__main__":
    seed_data()

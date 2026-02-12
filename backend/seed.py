import random
from sqlmodel import Session, create_engine, select, SQLModel
from app.models.domain import Category, User, Zone
from app.models.auth import RefreshToken
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
        # Hyderabad-area zone boundaries (covers mock data coordinates ~17.41-17.46°N, ~78.34-78.51°E)
        zones = [
            Zone(
                name="Central Zone",
                boundary="SRID=4326;POLYGON((78.33 17.40,78.52 17.40,78.52 17.47,78.33 17.47,78.33 17.40))",
            ),
            Zone(
                name="North Zone",
                boundary="SRID=4326;POLYGON((78.33 17.47,78.52 17.47,78.52 17.54,78.33 17.54,78.33 17.47))",
            ),
            Zone(
                name="South Zone",
                boundary="SRID=4326;POLYGON((78.33 17.33,78.52 17.33,78.52 17.40,78.33 17.40,78.33 17.33))",
            ),
            Zone(
                name="East Zone",
                boundary="SRID=4326;POLYGON((78.52 17.40,78.59 17.40,78.59 17.47,78.52 17.47,78.52 17.40))",
            ),
            Zone(
                name="West Zone",
                boundary="SRID=4326;POLYGON((78.26 17.40,78.33 17.40,78.33 17.47,78.26 17.47,78.26 17.40))",
            ),
        ]
        seeded_zones = []
        for z in zones:
            existing = session.exec(select(Zone).where(Zone.name == z.name)).first()
            if not existing:
                session.add(z)
                seeded_zones.append(z)
            else:
                seeded_zones.append(existing)

        # 3. Seed Organizations
        from app.models.domain import Organization

        orgs = [
            Organization(name="BBMP Central", zone_id=seeded_zones[0].id),
        ]
        seeded_orgs = []
        for o in orgs:
            existing = session.exec(
                select(Organization).where(Organization.name == o.name)
            ).first()
            if not existing:
                session.add(o)
                seeded_orgs.append(o)
            else:
                seeded_orgs.append(existing)

        session.commit()
        for o in seeded_orgs:
            session.refresh(o)

        # 4. Seed Users
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
                org_id=seeded_orgs[0].id,
            ),
            User(
                email="worker@authority.gov.in",
                role="WORKER",
                full_name="Field Worker",
                org_id=seeded_orgs[0].id,
            ),
            User(
                email="worker2@authority.gov.in",
                role="WORKER",
                full_name="Field Worker 2",
                org_id=seeded_orgs[0].id,
            ),
            User(
                email="worker3@authority.gov.in",
                role="WORKER",
                full_name="Field Worker 3",
                org_id=seeded_orgs[0].id,
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

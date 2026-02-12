#!/usr/bin/env python3
"""
Mock Data Loader for MARG (Monitoring Application for Road Governance)

Generates realistic test data:
- 8 workers across different zones
- 50+ issues across all categories and statuses
- Realistic city locations
- Proper issue lifecycle with timestamps

Usage:
    docker exec spec_requirements-backend-1 python load_mock_data.py
    # OR locally:
    python load_mock_data.py
"""

import random
from datetime import datetime, timedelta
from uuid import uuid4
from sqlmodel import Session, create_engine, select
from sqlalchemy import text
from app.models.domain import Zone, Category, User, Issue, Organization, Evidence
from app.models.auth import RefreshToken
from app.core.config import settings
from app.core.time import utc_now

# City locations with realistic coordinates
CITY_LOCATIONS = [
    # Area 1
    {"lat": 17.4156, "lng": 78.4347, "address": "Main Road, Sector 1"},
    {"lat": 17.4189, "lng": 78.4401, "address": "Park Avenue, Sector 2"},
    {"lat": 17.4203, "lng": 78.4289, "address": "Central Mall, Sector 3"},
    {"lat": 17.4267, "lng": 78.4355, "address": "City Circle"},
    # Area 2
    {"lat": 17.4325, "lng": 78.4073, "address": "High Street, Sector 4"},
    {"lat": 17.4356, "lng": 78.4156, "address": "Junction 5"},
    {"lat": 17.4289, "lng": 78.4012, "address": "Business District"},
    {"lat": 17.4412, "lng": 78.4098, "address": "Commercial Hub"},
    # Area 3
    {"lat": 17.4401, "lng": 78.3489, "address": "Tech Park, Sector 6"},
    {"lat": 17.4456, "lng": 78.3567, "address": "Corporate Park"},
    {"lat": 17.4378, "lng": 78.3623, "address": "Institutional Area"},
    {"lat": 17.4312, "lng": 78.3401, "address": "Ring Road"},
    # Area 4
    {"lat": 17.4489, "lng": 78.3867, "address": "Highway 1"},
    {"lat": 17.4534, "lng": 78.3912, "address": "City Towers"},
    {"lat": 17.4478, "lng": 78.3789, "address": "Outer Road"},
    {"lat": 17.4556, "lng": 78.3834, "address": "Suburban Area"},
    # Area 5
    {"lat": 17.4399, "lng": 78.4983, "address": "Railway Station Road"},
    {"lat": 17.4456, "lng": 78.5012, "address": "Station Circle"},
    {"lat": 17.4312, "lng": 78.5078, "address": "Green Belt"},
    {"lat": 17.4523, "lng": 78.4934, "address": "Lake Road"},
]

# Additional workers to create
ADDITIONAL_WORKERS = [
    {"email": "worker4@authority.gov.in", "name": "Field Worker 4", "zone": "Central"},
    {"email": "worker5@authority.gov.in", "name": "Field Worker 5", "zone": "North"},
    {"email": "worker6@authority.gov.in", "name": "Field Worker 6", "zone": "South"},
    {"email": "worker7@authority.gov.in", "name": "Field Worker 7", "zone": "East"},
    {"email": "worker8@authority.gov.in", "name": "Field Worker 8", "zone": "West"},
]

# Issue statuses and their distribution
STATUS_DISTRIBUTION = {
    "REPORTED": 12,
    "ASSIGNED": 8,
    "ACCEPTED": 6,
    "IN_PROGRESS": 10,
    "RESOLVED": 8,
    "CLOSED": 16,
}

# Priority distribution
PRIORITIES = ["P1", "P2", "P3"]
PRIORITY_WEIGHTS = [15, 35, 50]  # P1 is 15%, P2 is 35%, P3 is 50%


def create_point_wkt(lat: float, lng: float) -> str:
    """Create PostGIS point WKT string."""
    return f"SRID=4326;POINT({lng} {lat})"


def random_date(days_back: int = 60) -> datetime:
    """Generate random datetime within the last N days."""
    return utc_now() - timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )


def load_mock_data():
    """Load comprehensive mock data into the database."""
    engine = create_engine(settings.DATABASE_URL)

    with Session(engine) as session:
        # Get existing categories
        categories = session.exec(select(Category)).all()
        if not categories:
            print("❌ No categories found. Run seed.py first!")
            return

        category_map = {c.name: c for c in categories}
        print(f"✅ Found {len(categories)} categories: {list(category_map.keys())}")

        org = session.exec(
            select(Organization).where(Organization.name == "BBMP Central")
        ).first()
        if not org:
            print("❌ No organization found. Run seed.py first!")
            return
        print(f"✅ Found organization: {org.name} (id={org.id})")

        # Get existing users
        existing_workers = session.exec(select(User).where(User.role == "WORKER")).all()
        print(f"✅ Found {len(existing_workers)} existing workers")

        # Create additional workers
        for worker_data in ADDITIONAL_WORKERS:
            existing = session.exec(
                select(User).where(User.email == worker_data["email"])
            ).first()
            if not existing:
                new_worker = User(
                    email=worker_data["email"],
                    role="WORKER",
                    full_name=worker_data["name"],
                    status="ACTIVE",
                    org_id=org.id,
                )
                session.add(new_worker)
                print(
                    f"  + Created worker: {worker_data['name']} ({worker_data['email']})"
                )

        session.commit()

        # Refresh workers list
        all_workers = session.exec(select(User).where(User.role == "WORKER")).all()
        print(f"✅ Total workers: {len(all_workers)}")

        # Get or create a citizen for reporting
        citizen = session.exec(select(User).where(User.role == "CITIZEN")).first()
        if not citizen:
            citizen = User(
                email="citizen@example.com",
                role="CITIZEN",
                full_name="Citizen",
            )
            session.add(citizen)
            session.commit()
            session.refresh(citizen)

        # Check existing issues
        existing_issues = session.exec(select(Issue)).all()
        if len(existing_issues) > 20:
            print(
                f"⚠️  Already have {len(existing_issues)} issues. Skipping to avoid duplicates."
            )
            print(
                "   Run 'python reset_db.py && python seed.py && python load_mock_data.py' for fresh data."
            )
            return

        print("\n📝 Creating issues across all statuses and categories...")

        location_index = 0
        issue_count = 0

        for status, count in STATUS_DISTRIBUTION.items():
            for i in range(count):
                # Cycle through locations
                loc = CITY_LOCATIONS[location_index % len(CITY_LOCATIONS)]
                location_index += 1

                # Random category
                category = random.choice(categories)

                # Random priority (weighted)
                priority = random.choices(PRIORITIES, weights=PRIORITY_WEIGHTS)[0]

                # Base creation time
                created_at = random_date(60)
                updated_at = created_at

                # Assign worker for non-REPORTED statuses
                worker = None
                accepted_at = None
                resolved_at = None
                eta_date = None

                if status != "REPORTED":
                    worker = random.choice(all_workers)

                if status in ["ACCEPTED", "IN_PROGRESS", "RESOLVED", "CLOSED"]:
                    accepted_at = created_at + timedelta(hours=random.randint(1, 12))
                    eta_date = accepted_at + timedelta(days=random.randint(1, 7))
                    updated_at = accepted_at

                if status in ["RESOLVED", "CLOSED"]:
                    resolved_at = accepted_at + timedelta(hours=random.randint(2, 48))
                    updated_at = resolved_at

                if status == "CLOSED":
                    updated_at = resolved_at + timedelta(hours=random.randint(1, 24))

                issue = Issue(
                    category_id=category.id,
                    status=status,
                    location=create_point_wkt(loc["lat"], loc["lng"]),
                    address=loc["address"],
                    reporter_id=citizen.id,
                    worker_id=worker.id if worker else None,
                    priority=priority,
                    report_count=random.randint(1, 5),
                    eta_date=eta_date,
                    accepted_at=accepted_at,
                    resolved_at=resolved_at,
                    created_at=created_at,
                    updated_at=updated_at,
                    org_id=org.id,
                )
                session.add(issue)
                issue_count += 1

        session.commit()
        print(f"✅ Created {issue_count} issues")

        # Ensure EVERY worker has at least 3 completed issues in their history
        print("\n📜 Ensuring each worker has completed history...")
        history_count = 0
        for worker in all_workers:
            # Check how many completed issues this worker has
            completed = session.exec(
                select(Issue).where(
                    Issue.worker_id == worker.id,
                    Issue.status.in_(["RESOLVED", "CLOSED"]),
                )
            ).all()

            # If less than 3, create more CLOSED issues for this worker
            needed = 3 - len(completed)
            for _ in range(max(0, needed)):
                loc = random.choice(CITY_LOCATIONS)
                category = random.choice(categories)
                created_at = random_date(90)  # Older issues for history
                accepted_at = created_at + timedelta(hours=random.randint(1, 6))
                resolved_at = accepted_at + timedelta(hours=random.randint(2, 24))
                closed_at = resolved_at + timedelta(hours=random.randint(1, 12))
                eta_date = accepted_at + timedelta(days=random.randint(1, 5))

                history_issue = Issue(
                    category_id=category.id,
                    status="CLOSED",
                    location=create_point_wkt(loc["lat"], loc["lng"]),
                    address=loc["address"],
                    reporter_id=citizen.id,
                    worker_id=worker.id,
                    priority=random.choice(PRIORITIES),
                    report_count=random.randint(1, 3),
                    eta_date=eta_date,
                    accepted_at=accepted_at,
                    resolved_at=resolved_at,
                    created_at=created_at,
                    updated_at=closed_at,
                    org_id=org.id,
                )
                session.add(history_issue)
                history_count += 1

        session.commit()
        if history_count > 0:
            print(
                f"   + Added {history_count} completed issues to ensure worker history"
            )

        # Summary by status
        print("\n📊 Issue Distribution:")
        for status in STATUS_DISTRIBUTION.keys():
            count = session.exec(select(Issue).where(Issue.status == status)).all()
            print(f"   {status}: {len(count)}")

        # Summary by category
        print("\n📁 Issues by Category:")
        for cat_name, cat in category_map.items():
            count = session.exec(select(Issue).where(Issue.category_id == cat.id)).all()
            print(f"   {cat_name}: {len(count)}")

        # Worker workload
        print("\n👷 Worker Workload (active issues):")
        for worker in all_workers:
            active = session.exec(
                select(Issue).where(
                    Issue.worker_id == worker.id,
                    Issue.status.in_(["ASSIGNED", "ACCEPTED", "IN_PROGRESS"]),
                )
            ).all()
            resolved = session.exec(
                select(Issue).where(
                    Issue.worker_id == worker.id,
                    Issue.status.in_(["RESOLVED", "CLOSED"]),
                )
            ).all()
            print(
                f"   {worker.full_name}: {len(active)} active, {len(resolved)} completed"
            )

        print("\n✅ Mock data loaded successfully!")
        print("\n📌 Test Accounts:")
        print("   Admin:   admin@authority.gov.in")
        print(
            "   Workers: worker@authority.gov.in, worker2@authority.gov.in ... worker8@authority.gov.in"
        )
        print("   Citizen: citizen@example.com or any email")
        print("\n🔐 Get OTP: docker compose logs backend | grep OTP")


if __name__ == "__main__":
    load_mock_data()

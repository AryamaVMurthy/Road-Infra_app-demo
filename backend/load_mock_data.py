#!/usr/bin/env python3
"""
Mock Data Loader for Urban Infrastructure Reporting System

Generates realistic test data:
- 8 workers across different zones
- 50+ issues across all categories and statuses
- Realistic Hyderabad locations
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
from app.core.config import settings

# Hyderabad locations with realistic coordinates
HYDERABAD_LOCATIONS = [
    # Banjara Hills area
    {"lat": 17.4156, "lng": 78.4347, "address": "Road No. 12, Banjara Hills"},
    {"lat": 17.4189, "lng": 78.4401, "address": "Road No. 2, Banjara Hills"},
    {"lat": 17.4203, "lng": 78.4289, "address": "GVK One Mall, Banjara Hills"},
    {"lat": 17.4267, "lng": 78.4355, "address": "Panjagutta Circle"},
    # Jubilee Hills area
    {"lat": 17.4325, "lng": 78.4073, "address": "Road No. 36, Jubilee Hills"},
    {"lat": 17.4356, "lng": 78.4156, "address": "Jubilee Hills Check Post"},
    {"lat": 17.4289, "lng": 78.4012, "address": "Film Nagar, Jubilee Hills"},
    {"lat": 17.4412, "lng": 78.4098, "address": "Road No. 45, Jubilee Hills"},
    # Gachibowli area
    {"lat": 17.4401, "lng": 78.3489, "address": "DLF Cyber City, Gachibowli"},
    {"lat": 17.4456, "lng": 78.3567, "address": "Wipro Junction, Gachibowli"},
    {"lat": 17.4378, "lng": 78.3623, "address": "ISB Road, Gachibowli"},
    {"lat": 17.4312, "lng": 78.3401, "address": "Nanakramguda Main Road"},
    # Madhapur area
    {"lat": 17.4489, "lng": 78.3867, "address": "HITEC City Main Road"},
    {"lat": 17.4534, "lng": 78.3912, "address": "Cyber Towers, Madhapur"},
    {"lat": 17.4478, "lng": 78.3789, "address": "Durgam Cheruvu Road"},
    {"lat": 17.4556, "lng": 78.3834, "address": "Kondapur Junction"},
    # Secunderabad area
    {"lat": 17.4399, "lng": 78.4983, "address": "Secunderabad Railway Station"},
    {"lat": 17.4456, "lng": 78.5012, "address": "Paradise Circle"},
    {"lat": 17.4312, "lng": 78.5078, "address": "Trimulgherry"},
    {"lat": 17.4523, "lng": 78.4934, "address": "Tank Bund Road"},
    # Ameerpet area
    {"lat": 17.4378, "lng": 78.4478, "address": "Ameerpet Metro Station"},
    {"lat": 17.4423, "lng": 78.4512, "address": "SR Nagar Main Road"},
    {"lat": 17.4356, "lng": 78.4534, "address": "Yousufguda Check Post"},
    {"lat": 17.4401, "lng": 78.4423, "address": "Greenlands Road"},
    # Begumpet area
    {"lat": 17.4434, "lng": 78.4667, "address": "Begumpet Airport Road"},
    {"lat": 17.4478, "lng": 78.4712, "address": "Somajiguda Circle"},
    {"lat": 17.4389, "lng": 78.4623, "address": "Raj Bhavan Road"},
    {"lat": 17.4512, "lng": 78.4656, "address": "Khairatabad Junction"},
    # Kukatpally area
    {"lat": 17.4934, "lng": 78.3989, "address": "KPHB Colony Main Road"},
    {"lat": 17.4878, "lng": 78.4045, "address": "Kukatpally Y Junction"},
    {"lat": 17.4956, "lng": 78.3912, "address": "Allwyn Colony"},
    {"lat": 17.4823, "lng": 78.4078, "address": "Moosapet X Roads"},
    # Dilsukhnagar area
    {"lat": 17.3689, "lng": 78.5234, "address": "Dilsukhnagar Bus Stand"},
    {"lat": 17.3734, "lng": 78.5189, "address": "Chaitanyapuri"},
    {"lat": 17.3656, "lng": 78.5267, "address": "Kothapet Main Road"},
    {"lat": 17.3712, "lng": 78.5145, "address": "Malakpet"},
    # LB Nagar area
    {"lat": 17.3489, "lng": 78.5478, "address": "LB Nagar Circle"},
    {"lat": 17.3534, "lng": 78.5512, "address": "Sagar Ring Road Junction"},
    {"lat": 17.3456, "lng": 78.5423, "address": "Bairamalguda"},
    {"lat": 17.3578, "lng": 78.5389, "address": "Nagole Metro Station"},
]

# Additional workers to create
ADDITIONAL_WORKERS = [
    {"email": "worker4@ghmc.gov.in", "name": "Prasad Naidu", "zone": "Madhapur"},
    {"email": "worker5@ghmc.gov.in", "name": "Srinivas Goud", "zone": "Secunderabad"},
    {"email": "worker6@ghmc.gov.in", "name": "Mahesh Babu", "zone": "Kukatpally"},
    {"email": "worker7@ghmc.gov.in", "name": "Rajesh Khanna", "zone": "Dilsukhnagar"},
    {"email": "worker8@ghmc.gov.in", "name": "Anil Kumar", "zone": "Ameerpet"},
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
    return datetime.utcnow() - timedelta(
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
                email="citizen@hyderabad.in",
                role="CITIZEN",
                full_name="Hyderabad Citizen",
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
                loc = HYDERABAD_LOCATIONS[location_index % len(HYDERABAD_LOCATIONS)]
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
                loc = random.choice(HYDERABAD_LOCATIONS)
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
        print("   Admin:   admin@ghmc.gov.in")
        print(
            "   Workers: worker@ghmc.gov.in, worker2@ghmc.gov.in ... worker8@ghmc.gov.in"
        )
        print("   Citizen: citizen@hyderabad.in or any email")
        print("\n🔐 Get OTP: docker compose logs backend | grep OTP")


if __name__ == "__main__":
    load_mock_data()

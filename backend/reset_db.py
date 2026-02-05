from sqlmodel import SQLModel, create_engine
from app.core.config import settings
import app.models.domain
from sqlalchemy import text
import time
import fcntl


def reset_db():
    engine = create_engine(
        settings.DATABASE_URL or settings.assemble_db_connection(None, settings)
    )

    lock_file_path = "/tmp/marg-reset-db.lock"
    with open(lock_file_path, "w", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)

        # Retry logic for concurrent resets in tests
        for attempt in range(5):
            try:
                with engine.connect() as conn:
                    # Disable triggers to speed up and avoid lock issues
                    conn.execute(text("SET session_replication_role = 'replica';"))

                    conn.execute(text("DROP TABLE IF EXISTS auditlog CASCADE;"))
                    conn.execute(text("DROP TABLE IF EXISTS otp CASCADE;"))
                    conn.execute(text("DROP TABLE IF EXISTS feedback CASCADE;"))
                    conn.execute(text("DROP TABLE IF EXISTS evidence CASCADE;"))
                    conn.execute(text("DROP TABLE IF EXISTS issue CASCADE;"))
                    conn.execute(text("DROP TABLE IF EXISTS invite CASCADE;"))
                    conn.execute(text('DROP TABLE IF EXISTS "user" CASCADE;'))
                    conn.execute(text("DROP TABLE IF EXISTS organization CASCADE;"))
                    conn.execute(text("DROP TABLE IF EXISTS category CASCADE;"))
                    conn.execute(text("DROP TABLE IF EXISTS zone CASCADE;"))
                    conn.execute(text("DROP TYPE IF EXISTS zone CASCADE;"))

                    conn.execute(text("SET session_replication_role = 'origin';"))
                    conn.commit()
                break
            except Exception as e:
                print(f"Cleanup attempt {attempt} failed: {e}")
                time.sleep(1)

        # Re-seed
        from seed import seed_data

        seed_data()


if __name__ == "__main__":
    reset_db()

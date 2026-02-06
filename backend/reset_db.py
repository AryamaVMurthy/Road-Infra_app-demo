from sqlmodel import Session, create_engine, text, SQLModel
from app.core.config import settings
import time
import fcntl


def reset_db():
    engine = create_engine(
        settings.DATABASE_URL or settings.assemble_db_connection(None, settings)
    )

    lock_file_path = "/tmp/marg-reset-db.lock"
    with open(lock_file_path, "w", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)

        with engine.connect() as conn:
            tables = [
                '"user"',
                "refreshtoken",
                "otp",
                "issue",
                "category",
                "zone",
                "auditlog",
                "notification",
                "evidence",
                "feedback",
                "invite",
            ]
            conn.execute(
                text(f"TRUNCATE TABLE {', '.join(tables)} RESTART IDENTITY CASCADE;")
            )
            conn.commit()

        print("Database truncated successfully.")

        from seed import seed_data

        seed_data()


if __name__ == "__main__":
    reset_db()

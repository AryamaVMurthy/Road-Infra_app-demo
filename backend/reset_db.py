from sqlmodel import create_engine, text, SQLModel
from app.core.config import settings
import fcntl

# Ensure SQLModel metadata is populated when this script runs standalone.
from app.models import auth as _auth_models  # noqa: F401
from app.models import domain as _domain_models  # noqa: F401


def reset_db():
    engine = create_engine(
        settings.DATABASE_URL or settings.assemble_db_connection(None, settings)
    )
    SQLModel.metadata.create_all(engine)

    lock_file_path = "/tmp/marg-reset-db.lock"
    with open(lock_file_path, "w", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)

        with engine.connect() as conn:
            conn.execute(
                text(
                    "ALTER TABLE refreshtoken ADD COLUMN IF NOT EXISTS token_lookup VARCHAR"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_refreshtoken_token_lookup ON refreshtoken (token_lookup)"
                )
            )
            tables = [f'"{table.name}"' for table in SQLModel.metadata.sorted_tables]
            if tables:
                conn.execute(
                    text(
                        f"TRUNCATE TABLE {', '.join(tables)} RESTART IDENTITY CASCADE;"
                    )
                )
            conn.commit()

        print("Database truncated successfully.")

        from seed import seed_data

        seed_data()


if __name__ == "__main__":
    reset_db()

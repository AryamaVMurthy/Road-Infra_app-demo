from __future__ import annotations

import os
from typing import Iterable

from sqlalchemy import create_engine, text


def build_postgres_statements() -> list[str]:
    return [
        "ALTER TABLE category ADD COLUMN IF NOT EXISTS classification_guidance VARCHAR(500)",
        "ALTER TABLE issue ADD COLUMN IF NOT EXISTS intake_submission_id UUID",
        "ALTER TABLE issue ADD COLUMN IF NOT EXISTS classification_source VARCHAR(255)",
        "ALTER TABLE issue ADD COLUMN IF NOT EXISTS classification_confidence DOUBLE PRECISION",
        "ALTER TABLE issue ADD COLUMN IF NOT EXISTS classification_model_id VARCHAR(255)",
        "ALTER TABLE issue ADD COLUMN IF NOT EXISTS classification_model_quantization VARCHAR(255)",
        "ALTER TABLE issue ADD COLUMN IF NOT EXISTS classification_prompt_version VARCHAR(255)",
        "ALTER TABLE issue ADD COLUMN IF NOT EXISTS reporter_notes TEXT",
        """
        CREATE TABLE IF NOT EXISTS reportintakesubmission (
            id UUID PRIMARY KEY,
            reporter_id UUID NOT NULL REFERENCES "user"(id),
            org_id UUID NULL REFERENCES organization(id),
            issue_id UUID NULL REFERENCES issue(id),
            status VARCHAR(64) NOT NULL,
            reason_code VARCHAR(128),
            selected_category_id UUID NULL REFERENCES category(id),
            selected_category_name_snapshot VARCHAR(255),
            selected_category_confidence DOUBLE PRECISION,
            classification_source VARCHAR(255),
            model_id VARCHAR(255),
            model_quantization VARCHAR(255),
            prompt_version VARCHAR(255),
            reporter_notes TEXT,
            address TEXT,
            lat DOUBLE PRECISION NOT NULL,
            lng DOUBLE PRECISION NOT NULL,
            file_path TEXT NOT NULL,
            mime_type VARCHAR(255) NOT NULL,
            image_sha256 VARCHAR(255) NOT NULL,
            raw_primary_result JSONB,
            raw_evaluator_result JSONB,
            latency_ms INTEGER,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """.strip(),
    ]


def _iter_statements() -> Iterable[str]:
    for statement in build_postgres_statements():
        yield statement


def main() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set to run migrate_vlm_intake_schema.py")

    engine = create_engine(database_url)
    with engine.begin() as connection:
        for statement in _iter_statements():
            connection.execute(text(statement))


if __name__ == "__main__":
    main()

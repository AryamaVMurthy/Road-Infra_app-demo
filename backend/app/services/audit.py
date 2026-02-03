from sqlmodel import Session
from app.models.domain import AuditLog
from uuid import UUID
from typing import Optional


class AuditService:
    @staticmethod
    def log(
        session: Session,
        action: str,
        entity_type: str,
        entity_id: UUID,
        actor_id: UUID,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
    ):
        log_entry = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            old_value=old_value,
            new_value=new_value,
        )
        session.add(log_entry)
        # We don't commit here, usually part of a larger transaction

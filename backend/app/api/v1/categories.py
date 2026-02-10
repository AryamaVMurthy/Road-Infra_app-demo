"""Public issue category endpoints."""

from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.domain import Category

router = APIRouter()


@router.get("", response_model=List[Category])
def list_active_categories(session: Session = Depends(get_session)):
    """Return all active issue categories."""
    statement = select(Category).where(Category.is_active.is_(True))
    return session.exec(statement).all()

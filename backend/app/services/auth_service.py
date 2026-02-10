from __future__ import annotations

from datetime import timedelta
import hashlib
import secrets
from typing import Tuple
from uuid import UUID, uuid4

import bcrypt
from fastapi import HTTPException, status
from jose import jwt
from sqlmodel import Session, select

from app.core.config import settings
from app.core.time import utc_now
from app.models.auth import RefreshToken


class AuthService:
    @staticmethod
    def create_access_token(data: dict) -> str:
        to_encode = data.copy()
        expire = utc_now() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

    @staticmethod
    def _lookup_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _token_material(token: str) -> str:
        # Bcrypt has a 72-byte input limit. Hash first to preserve full entropy.
        return AuthService._lookup_hash(token)

    @staticmethod
    def _bcrypt_hash(token: str) -> str:
        return bcrypt.hashpw(
            AuthService._token_material(token).encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("utf-8")

    @staticmethod
    def _is_bcrypt_hash(value: str) -> bool:
        return value.startswith("$2")

    @staticmethod
    def _verify_token(raw_token: str, stored_hash: str) -> bool:
        if AuthService._is_bcrypt_hash(stored_hash):
            candidates = [raw_token, AuthService._token_material(raw_token)]
            for candidate in candidates:
                try:
                    if bcrypt.checkpw(
                        candidate.encode("utf-8"), stored_hash.encode("utf-8")
                    ):
                        return True
                except ValueError:
                    continue
            return False

        # Legacy plaintext fallback (one-time migration path).
        return secrets.compare_digest(stored_hash, raw_token)

    @staticmethod
    def _find_refresh_token(
        session: Session, raw_token: str, for_update: bool = False
    ) -> RefreshToken | None:
        lookup = AuthService._lookup_hash(raw_token)

        stmt = select(RefreshToken).where(RefreshToken.token_lookup == lookup)
        if for_update:
            stmt = stmt.with_for_update()
        token = session.exec(stmt).first()

        if token:
            if not AuthService._verify_token(raw_token, token.token_hash):
                return None
            return token

        # Transitional compatibility: scan legacy rows that predate token_lookup.
        legacy_stmt = select(RefreshToken).where(RefreshToken.token_lookup.is_(None))
        if for_update:
            legacy_stmt = legacy_stmt.with_for_update()
        legacy_tokens = session.exec(legacy_stmt).all()

        for legacy_token in legacy_tokens:
            if not AuthService._verify_token(raw_token, legacy_token.token_hash):
                continue

            # One-time migration for legacy rows.
            legacy_token.token_lookup = lookup
            if not AuthService._is_bcrypt_hash(legacy_token.token_hash):
                legacy_token.token_hash = AuthService._bcrypt_hash(raw_token)
            session.add(legacy_token)
            session.flush()
            return legacy_token

        return None

    @staticmethod
    def create_refresh_token(
        session: Session,
        user_id: UUID,
        family_id: UUID | None = None,
        commit: bool = True,
    ) -> Tuple[str, RefreshToken]:
        token_str = secrets.token_urlsafe(64)
        expires_at = utc_now() + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        if family_id is None:
            family_id = uuid4()

        db_token = RefreshToken(
            user_id=user_id,
            token_hash=AuthService._bcrypt_hash(token_str),
            token_lookup=AuthService._lookup_hash(token_str),
            expires_at=expires_at,
            family_id=family_id,
        )
        session.add(db_token)

        if commit:
            session.commit()
        else:
            session.flush()

        session.refresh(db_token)
        return token_str, db_token

    @staticmethod
    def _revoke_all_user_tokens(session: Session, user_id: UUID):
        now = utc_now()
        stmt = select(RefreshToken).where(RefreshToken.user_id == user_id)
        tokens = session.exec(stmt).all()
        for token in tokens:
            if token.revoked_at is None:
                token.revoked_at = now
                session.add(token)

    @staticmethod
    def rotate_refresh_token(session: Session, old_token_str: str) -> Tuple[str, str]:
        old_token = AuthService._find_refresh_token(
            session, old_token_str, for_update=True
        )

        if not old_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        if old_token.revoked_at is not None:
            AuthService._revoke_all_user_tokens(session, old_token.user_id)
            session.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Security breach detected. Please log in again.",
            )

        if old_token.expires_at < utc_now():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired",
            )

        old_token.revoked_at = utc_now()
        session.add(old_token)

        new_token_str, new_db_token = AuthService.create_refresh_token(
            session,
            user_id=old_token.user_id,
            family_id=old_token.family_id,
            commit=False,
        )

        # Store reference to DB id, never the raw token.
        old_token.replaced_by = str(new_db_token.id)
        session.add(old_token)
        session.commit()

        user = old_token.user
        access_token = AuthService.create_access_token(
            data={"sub": user.email, "role": user.role, "id": str(user.id)}
        )

        return access_token, new_token_str

    @staticmethod
    def revoke_refresh_token(session: Session, token_str: str) -> bool:
        token = AuthService._find_refresh_token(session, token_str, for_update=True)
        if not token:
            return False

        if token.revoked_at is None:
            token.revoked_at = utc_now()
            session.add(token)
            session.commit()

        return True

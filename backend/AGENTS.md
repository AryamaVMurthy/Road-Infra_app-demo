# BACKEND KNOWLEDGE BASE

## OVERVIEW
FastAPI + SQLModel service layer for auth, workflow, analytics, media, and role-gated operations.

## STRUCTURE
```text
backend/
├── app/        # Runtime API application code
├── tests/      # Integration + security + lifecycle invariants
├── requirements.txt
├── seed.py
└── reset_db.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| App bootstrapping | `app/main.py` | Middleware, startup, router mount |
| API composition | `app/api/v1/api.py` | Includes auth/issues/admin/worker/media/analytics |
| Domain logic | `app/services/` | Keep transition rules and side-effects here |
| Auth configuration | `app/core/security.py` + `app/services/auth_service.py` | OTP + cookie token behavior |
| DB session wiring | `app/db/session.py` | SQLModel engine/session dependency |
| Test DB isolation | `tests/conftest.py` | Overrides app session with test engine |

## CONVENTIONS
- Router handlers are thin; business rules live in `app/services/*`.
- Versioned routes live under `app/api/v1`; new admin endpoints belong in `app/api/v1/admin/`.
- Settings come from `app/core/config.py` (`BaseSettings`, env-driven values).
- Tests assert workflow and security invariants, not just endpoint status codes.

## ANTI-PATTERNS
- Do not import and use production engine inside tests.
- Do not place new admin features in legacy `app/api/v1/admin_v0.py`.
- Do not embed hardcoded API prefixes outside config (`API_V1_STR`).

## NOTES
- Test suite expects PostGIS extension setup from `tests/conftest.py`.
- MinIO initialization is startup-sensitive; keep `init_minio()` behavior intact.

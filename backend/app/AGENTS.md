# BACKEND APP KNOWLEDGE BASE

## OVERVIEW
Core FastAPI application package: APIs, domain services, models, schemas, config, and DB/session glue.

## STRUCTURE
```text
backend/app/
├── api/       # Versioned route modules + dependencies
├── core/      # Settings, middleware, security helpers
├── db/        # SQLModel session providers
├── models/    # SQLModel persistence models
├── schemas/   # Request/response contracts
└── services/  # Workflow and business logic
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Add endpoint | `api/v1/*` | Route registration via `api/v1/api.py` |
| Add role checks | `api/deps.py` + `core/security.py` | Keep auth and role guards centralized |
| Change lifecycle logic | `services/workflow_service.py` + `services/issue_service.py` | Preserve transition invariants |
| Add audit behavior | `services/audit.py` | Domain audit trail writes |
| Add analytics behavior | `services/analytics.py` + `services/analytics_service.py` | Public vs admin analytics split |

## CONVENTIONS
- Keep serializers in `schemas/`; avoid returning raw ORM entities.
- Keep domain side-effects in `services/`, not in router functions.
- Follow modular route pattern already used by `api/v1/admin/` package.

## ANTI-PATTERNS
- Avoid duplicate transition logic across multiple routers.
- Avoid placing non-security cross-cutting logic inside middleware.
- Avoid direct MinIO calls from routers; route through service helpers.

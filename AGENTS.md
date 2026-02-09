# PROJECT KNOWLEDGE BASE

**Generated:** 2026-02-10T00:09:40+0530
**Commit:** 8f35216
**Branch:** hardening/rbac-auth-offline-removal

## OVERVIEW
MARG is a full-stack civic issue workflow system with a FastAPI backend and React/Vite frontend.
Core flow is OTP auth plus role-gated lifecycle transitions from report to closure.

## STRUCTURE
```text
./
├── backend/                 # FastAPI app, domain services, pytest suite
├── frontend/                # React SPA, Vitest + Playwright tests
├── docs/                    # Auth and test runbooks
├── docker-compose.yml       # Full local stack orchestration
├── Makefile                 # Test wrappers
└── specs_final_requirements/ # Acceptance checklists and specs
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| API entry + middleware | `backend/app/main.py` | App init, CORS, startup hooks |
| Route wiring | `backend/app/api/v1/api.py` | Domain routers composed here |
| Business rules | `backend/app/services/` | Keep endpoint handlers thin |
| DB models/schemas | `backend/app/models/`, `backend/app/schemas/` | SQLModel + response contracts |
| Frontend routing shell | `frontend/src/App.jsx` | Role routes and route guards |
| Frontend API client | `frontend/src/services/api.js` | Cookie auth + refresh queue |
| Backend tests | `backend/tests/` | Integration-first pytest suite |
| Frontend tests | `frontend/tests/` | Playwright E2E, auth + lifecycle rigor |

## CODE MAP
| Symbol | Type | Location | Refs | Role |
|--------|------|----------|------|------|
| `app` | variable | `backend/app/main.py` | high | FastAPI application root |
| `on_startup` | function | `backend/app/main.py` | medium | Initializes MinIO dependency |
| `api_router` | variable | `backend/app/api/v1/api.py` | high | V1 route composition point |
| `queryClient` | constant | `frontend/src/main.jsx` | medium | React Query cache root |
| `App` | function | `frontend/src/App.jsx` | high | Frontend route tree + auth shell |

## CONVENTIONS
- Backend keeps request handling in routers and domain behavior in `services`.
- Frontend auth state is cookie-based; browser sends credentials (`withCredentials: true`).
- API base URL defaults to `/api/v1`; override only through `VITE_API_URL`.
- Tests are split by domain intent (`auth`, `workflow`, `analytics`, `rigor`) rather than unit-only naming.

## ANTI-PATTERNS (THIS PROJECT)
- Do not reintroduce JWT/local auth state in browser storage.
- Do not bypass refresh-queue logic on 401 handling in `frontend/src/services/api.js`.
- Do not wire backend tests to production DB engine; use `backend/tests/conftest.py` fixtures.
- Do not add role-protected UI routes outside `PrivateRoute` wrappers.

## UNIQUE STYLES
- OTP login is first-class and test helpers validate full OTP request->lookup->login flow.
- Evidence/media flow is part of state transitions, not a separate upload subsystem.
- Backend test rigor favors lifecycle invariants and audit trail correctness.

## COMMANDS
```bash
# full stack
docker compose up --build

# backend tests (inside backend environment)
cd backend && python -m pytest tests -v --tb=short

# frontend unit/integration tests
cd frontend && npm test

# frontend e2e tests
cd frontend && npx playwright test --reporter=list

# make wrappers
make test-backend
make test-frontend
make test-e2e
```

## NOTES
- `docker_data/` includes local DB volume data; avoid indexing/scanning it during analysis.
- Root `pyrightconfig.json` points to `backend/.venv`; local type-check setup is backend-centric.
- `backend/app/api/v1/admin_v0.py` exists alongside modular admin routes; prefer modular `admin/` package.

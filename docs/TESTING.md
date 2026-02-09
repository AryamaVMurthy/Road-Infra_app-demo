# Testing Guide

This document defines how to run all test layers and interpret results.

## Test Matrix

| Layer | Tooling | Location |
|---|---|---|
| Backend unit/integration | pytest | `backend/tests` |
| Frontend unit/integration | Vitest + Testing Library | `frontend/src/test` |
| Frontend end-to-end | Playwright | `frontend/tests` |

## 1) Backend Tests

```bash
cd backend
source venv/bin/activate
POSTGRES_HOST=172.21.0.2 POSTGRES_SERVER=172.21.0.2 MINIO_ENDPOINT=localhost:9010 python -m pytest tests/ -v --tb=short
```

Notes:

- Test fixtures override app DB dependencies to isolate test DB state.
- Full suite currently includes workflow, RBAC, analytics, geo, audit, media, auth, and concurrency coverage.

## 2) Frontend Unit/Integration Tests

```bash
cd frontend
npm test
```

Covers:

- Auth context/interceptor behavior
- Login component behavior
- Worker modal components

## 3) Frontend E2E (Playwright)

Install browser binaries once per environment:

```bash
cd frontend
npx playwright install
```

Run all E2E tests:

```bash
npx playwright test --reporter=list
```

Run only lifecycle golden thread:

```bash
npx playwright test tests/lifecycle_golden_thread.spec.js --reporter=list
```

## Determinism Principles Used in E2E

- Request-based OTP login helper (`otp-request` -> DB OTP lookup -> `login`) to avoid UI timing flake.
- Strict SQL helper output (`psql -qAt -v ON_ERROR_STOP=1`) for reliable DB assertions.

## Failure Triage Checklist

1. Confirm frontend container is up on `http://localhost:3011`.
2. Confirm backend container is healthy.
3. Reinstall Playwright binaries if executables are missing.
4. Re-run failed test in isolation.
5. If an E2E assertion fails, verify DB state with `frontend/tests/helpers/db.js` queries.

## Last Verified Status

- Backend: `148 passed`
- Frontend Vitest: `16 passed`
- Playwright: `19 passed`

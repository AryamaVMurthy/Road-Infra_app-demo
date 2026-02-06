# MARG Handoff

This handoff is the operational quick-reference for running, testing, and validating the current MARG system.

## 1) Current Baseline

- Branch work has been merged with comprehensive backend and frontend tests.
- Auth is OTP + HttpOnly cookie JWT (access + refresh).
- Worker dashboard fetch-loop bug has been fixed.
- Playwright tests were hardened for deterministic execution.

## 2) Local Run

```bash
docker compose up --build
```

Endpoints:

- App: `http://localhost:3011`
- API (proxied): `http://localhost:3011/api/v1`
- MinIO API: `http://localhost:9010`
- MinIO Console: `http://localhost:9011`

## 3) Auth and OTP

### Auth endpoints

- `POST /api/v1/auth/otp-request`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

### OTP behavior

- In `DEV_MODE=true`, OTP is printed to backend logs and email is skipped.
- In `DEV_MODE=false`, SMTP send is attempted with configured `MAIL_*` values.

Read OTP from logs:

```bash
docker compose logs backend --tail=200 | grep -i otp
```

## 4) Seeded Accounts

| Email | Role |
|---|---|
| `citizen@example.com` | CITIZEN |
| `admin@authority.gov.in` | ADMIN |
| `worker@authority.gov.in` | WORKER |
| `worker2@authority.gov.in` | WORKER |
| `worker3@authority.gov.in` | WORKER |
| `sysadmin@marg.gov.in` | SYSADMIN |

## 5) Testing Commands

### Backend

```bash
cd backend
source venv/bin/activate
POSTGRES_HOST=172.21.0.2 POSTGRES_SERVER=172.21.0.2 MINIO_ENDPOINT=localhost:9010 python -m pytest tests/ -v --tb=short
```

### Frontend Unit/Integration

```bash
cd frontend
npm test
```

### Frontend E2E

```bash
cd frontend
npx playwright install
npx playwright test --reporter=list
```

## 6) Last Verified Totals

- Backend: `148 passed`
- Frontend Vitest: `16 passed`
- Playwright E2E: `19 passed`

## 7) Key Notes for Maintainers

- E2E auth in tests uses request-based login helpers to avoid OTP/UI instability where unnecessary.
- Service worker registration is skipped in automation contexts (`navigator.webdriver`) to reduce flake.
- SQL helper for tests uses strict psql options (`-qAt -v ON_ERROR_STOP=1`) for deterministic assertions.

## 8) Known Operational Caveats

- On fresh machines, Playwright binaries may be missing; run `npx playwright install`.
- Real OTP email delivery requires valid SMTP and `DEV_MODE=false`.

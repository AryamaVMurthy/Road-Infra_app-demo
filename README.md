# MARG (Monitoring Application for Road Governance)

MARG is a full-stack platform for reporting and managing city infrastructure issues (potholes, drainage, street lights, and garbage).

It supports role-based operations for CITIZEN, ADMIN, WORKER, and SYSADMIN with a full issue lifecycle:

`REPORTED -> ASSIGNED -> ACCEPTED -> IN_PROGRESS -> RESOLVED -> CLOSED`

## Tech Stack

- Backend: FastAPI, SQLModel, PostgreSQL + PostGIS, MinIO
- Frontend: React 18, Vite, Tailwind CSS, Leaflet, Recharts
- Auth: OTP login + JWT access/refresh tokens in HttpOnly cookies
- Testing: pytest, Vitest, Playwright

## Quick Start (Docker)

### Prerequisites

- Docker
- Docker Compose v2+

### Run

```bash
git clone https://github.com/AryamaVMurthy/Road-Infra_app-demo.git
cd Road-Infra_app-demo
docker compose up --build
```

### Service URLs

- Frontend: `http://localhost:3011`
- API (via frontend proxy): `http://localhost:3011/api/v1`
- MinIO API: `http://localhost:9010`
- MinIO Console: `http://localhost:9011`

## Authentication and OTP

### Current Auth Model

- OTP request: `POST /api/v1/auth/otp-request`
- OTP login: `POST /api/v1/auth/login`
- Refresh: `POST /api/v1/auth/refresh`
- Logout: `POST /api/v1/auth/logout`
- Session introspection: `GET /api/v1/auth/me`

Access and refresh tokens are issued as HttpOnly cookies. Frontend no longer reads JWT from localStorage.

### OTP Delivery Behavior

- `DEV_MODE=true` (default in docker-compose): OTP email send is skipped and OTP is printed in backend logs.
- `DEV_MODE=false`: backend attempts real SMTP delivery using `MAIL_*` settings.

### Read OTP in DEV_MODE

```bash
docker compose logs backend --tail=200 | grep -i otp
```

## Seeded User Accounts

| Email | Role | Dashboard |
|---|---|---|
| `citizen@example.com` | CITIZEN | `/citizen` |
| `admin@authority.gov.in` | ADMIN | `/authority` |
| `worker@authority.gov.in` | WORKER | `/worker` |
| `worker2@authority.gov.in` | WORKER | `/worker` |
| `worker3@authority.gov.in` | WORKER | `/worker` |
| `sysadmin@marg.gov.in` | SYSADMIN | `/admin` |

## Core User Flows

### Citizen

1. Request OTP and login.
2. Report issue with location and photo.
3. Track reports in My Reports.

### Admin / Authority

1. Review issues on Operations Map and Kanban Triage.
2. Assign/reassign/unassign workers.
3. Approve or reject resolved issues.

### Worker

1. View assigned tasks.
2. Accept task with ETA date.
3. Resolve task with photo evidence.

Note: Backend has `start` transition endpoint (`/worker/tasks/{id}/start`). UI may present resolve action directly depending on status.

## API Reference (High Value Endpoints)

### Auth

- `POST /api/v1/auth/otp-request`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/google-mock` (test/dev utility)
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

### Issues (Citizen)

- `POST /api/v1/issues/report`
- `GET /api/v1/issues/my-reports`

### Admin

- `GET /api/v1/admin/issues`
- `GET /api/v1/admin/workers`
- `GET /api/v1/admin/workers-with-stats`
- `GET /api/v1/admin/worker-analytics`
- `POST /api/v1/admin/assign?issue_id=<uuid>&worker_id=<uuid>`
- `POST /api/v1/admin/bulk-assign`
- `POST /api/v1/admin/approve?issue_id=<uuid>`
- `POST /api/v1/admin/reject?issue_id=<uuid>&reason=<text>`
- `POST /api/v1/admin/update-status?issue_id=<uuid>&status=<state>`

### Worker

- `GET /api/v1/worker/tasks`
- `POST /api/v1/worker/tasks/{issue_id}/accept?eta_date=<ISO-8601>`
- `POST /api/v1/worker/tasks/{issue_id}/start`
- `POST /api/v1/worker/tasks/{issue_id}/resolve` (multipart `photo`)

### Analytics + Media

- `GET /api/v1/analytics/stats`
- `GET /api/v1/analytics/heatmap`
- `GET /api/v1/analytics/issues-public`
- `GET /api/v1/analytics/audit/{entity_id}`
- `GET /api/v1/media/{issue_id}/before`
- `GET /api/v1/media/{issue_id}/after`

## Testing

### Frontend Unit/Integration (Vitest)

```bash
cd frontend
npm test
```

### Frontend E2E (Playwright)

```bash
cd frontend
npx playwright install
npx playwright test --reporter=list
```

### Backend (pytest)

If running against dockerized DB/backend network setup used in this repo:

```bash
cd backend
source venv/bin/activate
POSTGRES_HOST=172.21.0.2 POSTGRES_SERVER=172.21.0.2 MINIO_ENDPOINT=localhost:9010 python -m pytest tests/ -v --tb=short
```

## Current Verified Test Status

- Backend: `148 passed`
- Frontend Vitest: `16 passed`
- Playwright E2E: `19 passed`

## Additional Documentation

- Auth details: `docs/AUTHENTICATION.md`
- Test execution and triage: `docs/TESTING.md`
- Handoff runbook: `HANDOFF.md`
- Architecture overview: `DESIGN.md`

## Development Notes

- Service worker registration is skipped under browser automation (`navigator.webdriver`) to reduce E2E flakiness.
- E2E tests use deterministic API-request login helper (`page.request.post(...)`) where appropriate.
- `frontend/tests/helpers/db.js` uses strict psql flags (`-qAt -v ON_ERROR_STOP=1`) to avoid false positives in SQL assertions.

## Project Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   └── tests/
├── frontend/
│   ├── src/
│   └── tests/
├── docker-compose.yml
├── DESIGN.md
├── HANDOFF.md
└── README.md
```

## Production Checklist

- Set `DEV_MODE=false`.
- Configure valid SMTP (`MAIL_SERVER`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_FROM`).
- Set strong `SECRET_KEY`.
- Configure HTTPS.
- Restrict CORS to production domains.

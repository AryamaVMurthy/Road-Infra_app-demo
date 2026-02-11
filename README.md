# MARG (Monitoring Application for Road Governance)

MARG is a full-stack civic infrastructure management platform for reporting and resolving city issues (potholes, drainage, street lights, garbage). It supports role-based operations for **CITIZEN**, **ADMIN**, **WORKER**, and **SYSADMIN** with a complete issue lifecycle:

```
REPORTED → ASSIGNED → ACCEPTED → IN_PROGRESS → RESOLVED → CLOSED
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, SQLModel, PostgreSQL + PostGIS, MinIO |
| Frontend | React 18, Vite, Tailwind CSS, Mapbox GL, Recharts |
| Auth | OTP login + JWT access/refresh tokens in HttpOnly cookies |
| Infra | Docker Compose, Nginx reverse proxy |
| Testing | pytest (154 tests), Vitest (17 tests), Playwright E2E (38 tests) |

---

## Quick Start (Development)

### Prerequisites

- Docker & Docker Compose v2+
- Node.js 20+
- Python 3.12+

### 1. Clone and configure

```bash
git clone https://github.com/AryamaVMurthy/Road-Infra_app-demo.git
cd Road-Infra_app-demo

# Copy env templates
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Edit `backend/.env` and `frontend/.env` with your values. For development, the defaults work out of the box.

### 2. Start with Docker Compose

```bash
docker compose up --build
```

### 3. Access the application

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3011 |
| API (via frontend proxy) | http://localhost:3011/api/v1 |
| API Docs (dev only) | http://localhost:3011/api/v1/docs |
| MinIO Console | http://localhost:9011 |

---

## Production Deployment

### 1. Configure environment

Create a `.env` file in the project root:

```bash
# Required — generate with: openssl rand -hex 32
SECRET_KEY=your-64-char-random-string

# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=strong-password-here
POSTGRES_DB=app

# MinIO (Object Storage)
MINIO_ACCESS_KEY=your-minio-access-key
MINIO_SECRET_KEY=your-minio-secret-key

# CORS — set to your production domain
BACKEND_CORS_ORIGINS=["https://yourdomain.com"]
DOMAIN=yourdomain.com

# SMTP for OTP emails
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_FROM=info@yourdomain.com
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587

# Frontend
FRONTEND_PORT=3011
VITE_MAPBOX_TOKEN=your-mapbox-public-token
```

### 2. Deploy

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

### 3. Production vs Development differences

| Feature | Development | Production |
|---------|------------|------------|
| `DEV_MODE` | `true` (OTP printed to logs) | `false` (OTP sent via SMTP) |
| API Docs | Enabled at `/api/v1/docs` | Disabled |
| Cookies | `Secure=false` | `Secure=true` |
| Console logs | Visible | Stripped by Vite build |
| Source maps | Generated | Disabled |
| DB volumes | Local `docker_data/` | Named Docker volumes |
| Ports | Exposed to all interfaces | Bound to `127.0.0.1` |
| Backend process | Single worker | 2 workers, non-root user |
| Nginx | Basic proxy | Gzip, static caching, security headers |

### 4. HTTPS (recommended)

Place a reverse proxy (e.g., Caddy, Traefik, or Nginx with certbot) in front of the frontend container:

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:3011;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Authentication

### Auth Endpoints

All tokens are HttpOnly cookies. The frontend never reads JWT from localStorage.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/otp-request` | POST | Request OTP for email |
| `/api/v1/auth/login` | POST | Login with email + OTP |
| `/api/v1/auth/refresh` | POST | Rotate refresh token |
| `/api/v1/auth/logout` | POST | Revoke refresh token + clear cookies |
| `/api/v1/auth/me` | GET | Current user session |

### OTP in Development

```bash
# OTP is printed in backend logs when DEV_MODE=true
docker compose logs backend --tail=200 | grep -i otp
```

### Seeded User Accounts

| Email | Role | Dashboard |
|-------|------|-----------|
| `citizen@example.com` | CITIZEN | `/citizen` |
| `admin@authority.gov.in` | ADMIN | `/authority` |
| `worker@authority.gov.in` | WORKER | `/worker` |
| `worker2@authority.gov.in` | WORKER | `/worker` |
| `worker3@authority.gov.in` | WORKER | `/worker` |
| `sysadmin@marg.gov.in` | SYSADMIN | `/admin` |

---

## Core User Flows

### Citizen
1. Request OTP and login
2. Report issue with photo, category, and map location
3. Track reports in My Reports with audit trail

### Admin / Authority
1. Review issues on Operations Map and Kanban Triage
2. Assign/reassign/unassign workers
3. Approve or reject resolved issues
4. View worker analytics and heatmap

### Worker
1. View assigned tasks
2. Accept task with ETA date
3. Resolve task with photo evidence

### SysAdmin
1. Register new authorities with jurisdiction
2. Manage issue types (CRUD)
3. Onboard workers via invite or bulk CSV
4. View system-wide audit logs

---

## API Reference

### Auth
- `POST /api/v1/auth/otp-request` — Request OTP
- `POST /api/v1/auth/login` — Login with OTP
- `POST /api/v1/auth/refresh` — Rotate tokens
- `POST /api/v1/auth/logout` — Revoke and clear
- `GET /api/v1/auth/me` — Session info

### Categories (Public)
- `GET /api/v1/categories` — List active issue categories

### Issues (Citizen)
- `POST /api/v1/issues/report` — Report new issue (multipart)
- `GET /api/v1/issues/my-reports` — List citizen's reports

### Admin
- `GET /api/v1/admin/issues` — All issues
- `POST /api/v1/admin/update-status` — Update issue status
- `POST /api/v1/admin/approve` — Approve resolved issue
- `POST /api/v1/admin/reject` — Reject resolution
- `POST /api/v1/admin/update-priority` — Update issue priority
- `POST /api/v1/admin/assign` — Assign worker to issue
- `POST /api/v1/admin/bulk-assign` — Bulk assign issues
- `POST /api/v1/admin/reassign` — Reassign to different worker
- `POST /api/v1/admin/unassign` — Remove assignment

### Admin - Workers
- `GET /api/v1/admin/workers` — All workers
- `GET /api/v1/admin/workers-with-stats` — Workers with task counts
- `POST /api/v1/admin/deactivate-worker` — Deactivate worker
- `POST /api/v1/admin/activate-worker` — Activate worker
- `POST /api/v1/admin/bulk-register` — Bulk register workers
- `POST /api/v1/admin/invite` — Invite single worker
- `POST /api/v1/admin/bulk-invite` — Bulk invite workers

### Admin - Analytics
- `GET /api/v1/admin/worker-analytics` — Worker performance data
- `GET /api/v1/admin/dashboard-stats` — Dashboard statistics

### Admin - System (SYSADMIN only)
- `GET /api/v1/admin/authorities` — List authorities
- `POST /api/v1/admin/authorities` — Create authority
- `PUT /api/v1/admin/authorities/{org_id}` — Update authority
- `DELETE /api/v1/admin/authorities/{org_id}` — Delete authority
- `GET /api/v1/admin/issue-types` — List issue types
- `POST /api/v1/admin/issue-types` — Create issue type
- `PUT /api/v1/admin/issue-types/{category_id}` — Update issue type
- `DELETE /api/v1/admin/issue-types/{category_id}` — Deactivate issue type
- `POST /api/v1/admin/manual-issues` — Create manual issue

### Worker
- `GET /api/v1/worker/tasks` — Assigned tasks
- `POST /api/v1/worker/tasks/{id}/accept?eta_date=<ISO-8601>` — Accept task
- `POST /api/v1/worker/tasks/{id}/start` — Start task
- `POST /api/v1/worker/tasks/{id}/resolve` — Resolve with photo (multipart)

### Analytics & Media
- `GET /api/v1/analytics/stats` — City-wide statistics
- `GET /api/v1/analytics/heatmap` — Issue heatmap data
- `GET /api/v1/analytics/issues-public` — Public issue feed
- `GET /api/v1/analytics/audit/{entity_id}` — Entity audit trail
- `GET /api/v1/analytics/audit-all` — Full audit log (admin only)
- `GET /api/v1/media/{issue_id}/before` — Before photo
- `GET /api/v1/media/{issue_id}/after` — After photo

---

## Testing

### Run all tests

```bash
# Backend (154 tests)
cd backend
source ../.venv/bin/activate
PYTHONPATH=. pytest tests/ -q --tb=short

# Frontend lint (0 errors)
cd frontend
npm run lint

# Frontend unit/integration (17 tests)
cd frontend
npm test

# Frontend E2E (38 tests)
cd frontend
npx playwright test --reporter=list
```

### Verified Test Status

| Suite | Tests | Coverage |
|-------|-------|----------|
| Backend pytest | 154 passed | Auth, RBAC, workflow lifecycle, audit, analytics, media, bulk ops |
| Frontend ESLint | 0 errors | All source files |
| Frontend Vitest | 17 passed | Auth interceptor, context, login, modals |
| Playwright E2E | 38 passed | Full lifecycle, RBAC security, mobile responsiveness, maps, analytics |

---

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Versioned route handlers
│   │   │   ├── admin/       # Admin-specific endpoints
│   │   │   ├── auth.py      # OTP + JWT auth
│   │   │   ├── issues.py    # Citizen issue reporting
│   │   │   ├── worker.py    # Worker task management
│   │   │   └── api.py       # Router composition
│   │   ├── core/            # Config, middleware, security
│   │   ├── db/              # SQLModel session providers
│   │   ├── models/          # Database models
│   │   ├── schemas/         # Request/response contracts
│   │   └── services/        # Business logic layer
│   ├── tests/               # pytest integration suite
│   ├── Dockerfile
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # Shared UI (ErrorBoundary, maps, modals)
│   │   ├── features/        # Domain UI (authority, worker)
│   │   ├── hooks/           # Auth context, geolocation
│   │   ├── pages/           # Route pages by role
│   │   ├── services/        # API client with refresh queue
│   │   └── config/          # Centralized Mapbox config
│   ├── tests/               # Playwright E2E suite
│   ├── Dockerfile
│   ├── nginx.conf           # Production reverse proxy
│   ├── .env.example
│   └── vite.config.js
├── docker-compose.yml        # Development stack
├── docker-compose.prod.yml   # Production stack
├── docs/                     # Auth and test runbooks
└── README.md
```

---

## Security

- **HttpOnly cookies** — Tokens never exposed to JavaScript (XSS protection)
- **Refresh token rotation** — Old tokens revoked on use; replay triggers full revocation
- **Bcrypt hashing** — Refresh tokens stored as bcrypt hashes with SHA-256 lookup index
- **Rate limiting** — OTP requests limited to 3 per 10-minute window (production mode)
- **RBAC enforcement** — Role checks on every protected endpoint; cross-role access returns 403
- **Security headers** — HSTS, X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy
- **Non-root containers** — Backend runs as unprivileged user in Docker
- **CORS** — Configurable via `BACKEND_CORS_ORIGINS` environment variable
- **No source maps** — Production builds exclude source maps
- **Error boundary** — Global React ErrorBoundary catches and handles UI crashes gracefully

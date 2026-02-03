# Urban Infrastructure Reporting System

A full-stack application for reporting and managing city infrastructure issues (potholes, drainage problems, street lights, garbage) in Hyderabad, India. Built for GHMC (Greater Hyderabad Municipal Corporation).

## Features

- **Citizen Portal**: Report infrastructure issues with GPS location and photo evidence
- **Authority Dashboard**: View issues on map, assign to workers, approve resolutions
  - **Kanban Triage View**: Visual workflow with REPORTED → ASSIGNED → IN_PROGRESS → RESOLVED → CLOSED columns
  - **Quick-Assign**: One-click worker assignment with real-time task count display
  - **Worker Analytics**: Embedded workforce overview with top performers leaderboard
  - **ETA Tracking**: Display estimated completion times on issue cards
  - **Auto-Refresh**: Dashboard updates every 30 seconds with manual refresh option
- **Worker Dashboard**: Accept assigned tasks with ETA, submit resolution proof
- **Analytics Dashboard**: Real-time city health metrics, heatmaps, and trends
- **Audit Trail**: Complete transparency with full mutation history

## Tech Stack

### Backend
- **FastAPI** - High-performance Python web framework
- **PostgreSQL + PostGIS** - Spatial database for geolocation data
- **SQLModel** - ORM with Pydantic integration
- **MinIO** - S3-compatible object storage for images
- **JWT** - Secure token-based authentication

### Frontend
- **React 18** + **Vite** - Modern frontend tooling
- **Tailwind CSS** - Utility-first styling
- **Leaflet** - Interactive maps with heatmap support
- **Recharts** - Data visualization
- **Framer Motion** - Smooth animations

## Prerequisites

- **Docker** and **Docker Compose** (v2.0+)

That's it! Everything runs in containers.

## Quick Start (Docker - Recommended)

```bash
# Clone and start
git clone https://github.com/AryamaVMurthy/Road-Infra_app-demo.git
cd Road-Infra_app-demo
docker compose up --build
```

Open **http://localhost:3001** - the app is ready!

The first build takes 2-3 minutes. Subsequent starts are instant.

### What's Running

| Service | Container | Port |
|---------|-----------|------|
| Frontend | Nginx serving React | `3001` |
| Backend | FastAPI + Uvicorn | `8088` (internal) |
| Database | PostgreSQL + PostGIS | `5432` (internal) |
| Storage | MinIO API | `9000` |
| Storage Console | MinIO Dashboard | `9001` |

### Persistence

Data is stored in the `./docker_data` directory in the project root. This ensures all reports, users, and images persist even if containers are deleted.

- `./docker_data/postgres`: Database records
- `./docker_data/minio`: Uploaded images and evidence

---

## Alternative: Local Development Setup

If you prefer hot-reload during development:

### Prerequisites
- Python 3.12+
- Node.js 18+

### 1. Start Database Services Only

```bash
docker-compose -f docker-compose.dev.yml up -d
```

### 2. Setup Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python seed.py
uvicorn app.main:app --host 0.0.0.0 --port 8088 --reload
```

### 3. Setup Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

---

## Test Users

In DEV_MODE, OTPs are printed to the backend console instead of being emailed.

| Email | Role | Dashboard |
|-------|------|-----------|
| `sysadmin@urbaninfra.gov.in` | SYSADMIN | `/admin` |
| `admin@ghmc.gov.in` | ADMIN | `/authority` |
| `worker@ghmc.gov.in` | WORKER | `/worker` |
| `resident@hyderabad.in` | CITIZEN | `/citizen` |
| Any new email | CITIZEN | `/citizen` |

### Login Flow
1. Enter email on login page
2. Click "Request Access"
3. Check backend console for OTP: `[DEV MODE] Skipping email send. OTP for email@example.com: 123456`
4. Enter the 6-digit OTP
5. You'll be redirected to your role-based dashboard

## API Endpoints

### Authentication
- `POST /api/v1/auth/otp-request` - Request OTP
- `POST /api/v1/auth/login` - Verify OTP and get JWT

### Issues
- `POST /api/v1/issues/report` - Report new issue (multipart form)
- `GET /api/v1/issues/my-reports?email=` - Get user's reports

### Admin
- `GET /api/v1/admin/issues` - List all issues
- `GET /api/v1/admin/workers` - List all workers
- `GET /api/v1/admin/workers-with-stats` - Workers with active task counts (sorted by workload)
- `GET /api/v1/admin/worker-analytics` - Detailed worker performance metrics
- `POST /api/v1/admin/assign` - Quick-assign single issue to worker
- `POST /api/v1/admin/bulk-assign` - Assign multiple issues to worker
- `POST /api/v1/admin/approve` - Approve resolved issue
- `POST /api/v1/admin/reject` - Reject with reason

### Worker
- `GET /api/v1/worker/tasks` - Get assigned tasks
- `POST /api/v1/worker/tasks/{id}/accept` - Accept task with ETA
- `POST /api/v1/worker/tasks/{id}/resolve` - Submit resolution proof

### Analytics (Public)
- `GET /api/v1/analytics/stats` - Dashboard statistics
- `GET /api/v1/analytics/heatmap` - Issue heatmap data
- `GET /api/v1/analytics/issues-public` - Public issue list

### Media
- `GET /api/v1/media/{issue_id}/before` - Before image
- `GET /api/v1/media/{issue_id}/after` - After image

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API route handlers
│   │   ├── core/            # Config, security, database
│   │   ├── models/          # SQLModel domain models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   └── services/        # Business logic services
│   ├── seed.py              # Database seeder
│   ├── Dockerfile           # Backend container
│   └── requirements.txt
├── frontend/
│   ├── public/
│   │   └── sw.js            # Service Worker for offline
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/           # Route pages by role
│   │   ├── hooks/           # Custom React hooks (offline sync)
│   │   └── services/        # API client, auth, offline storage
│   ├── Dockerfile           # Frontend container (Nginx)
│   ├── nginx.conf           # Nginx config with API proxy
│   └── package.json
├── docker-compose.yml       # Full stack deployment
├── docker-compose.dev.yml   # Dev mode (DB + MinIO only)
├── DESIGN.md                # Technical architecture
├── HANDOFF.md               # Quick reference guide
└── README.md
```

## Issue Lifecycle

```
REPORTED → ASSIGNED → ACCEPTED → IN_PROGRESS → RESOLVED → CLOSED
    ↓         ↓                       ↓            ↓
 (Citizen)  (Admin)     ←←←←←←   (Worker)     (Admin approves)
```

1. **REPORTED**: Citizen submits issue with photo and GPS
2. **ASSIGNED**: Authority assigns to field worker
3. **ACCEPTED**: Worker accepts with ETA
4. **IN_PROGRESS**: Worker starts on-site work
5. **RESOLVED**: Worker submits "after" photo proof
6. **CLOSED**: Authority approves resolution

## Development

### Running Tests

```bash
# Backend tests (requires local setup)
cd backend
source venv/bin/activate
pytest

# Frontend tests
cd frontend
npm test
```

### Rebuilding Containers

```bash
# Rebuild specific service
docker-compose build backend
docker-compose up -d backend

# Rebuild all
docker-compose up --build
```

## Troubleshooting

### Docker Issues
```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs backend
docker-compose logs frontend

# Rebuild from scratch
docker-compose down -v
docker-compose up --build
```

### OTP Not Received
- In DEV_MODE, OTPs are printed to the backend console, not emailed
- Check logs: `docker-compose logs backend | grep OTP`

### Database Connection Issues
```bash
# Check if PostgreSQL is healthy
docker-compose ps

# Reset database
docker-compose down -v
docker-compose up --build
```

### MinIO Issues
```bash
# Access MinIO Console (dev mode only)
# http://localhost:9001
# Login: minioadmin / minioadmin
```

## License

MIT License - See LICENSE file for details.

## Contributors

Built for DASS (Design and Analysis of Software Systems) course project.

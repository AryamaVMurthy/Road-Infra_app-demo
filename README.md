# Urban Infrastructure Reporting System

A full-stack application for reporting and managing city infrastructure issues (potholes, drainage problems, street lights, garbage) in Hyderabad, India. Built for GHMC (Greater Hyderabad Municipal Corporation).

## Features

- **Citizen Portal**: Report infrastructure issues with GPS location and photo evidence
- **Authority Dashboard**: View issues on map, assign to workers, approve resolutions
  - **Kanban Triage View**: Visual workflow with REPORTED → ASSIGNED → IN_PROGRESS → RESOLVED → CLOSED columns
  - **Quick-Assign**: One-click worker assignment with real-time task count display
  - **Worker Analytics**: Embedded workforce overview with real-time stats
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

---

## 🚀 Deployment Guide

### Prerequisites

- **Docker** and **Docker Compose** (v2.0+)

That's it! Everything runs in containers.

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/AryamaVMurthy/Road-Infra_app-demo.git
cd Road-Infra_app-demo

# 2. Start all services
docker compose up --build

# 3. Wait for startup (first build takes 2-3 minutes)
# You'll see: "Uvicorn running on http://0.0.0.0:8088"
```

Open **http://localhost:3001** in your browser - the app is ready!

### Services Running

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:3001 | Main application UI |
| **Backend API** | http://localhost:3001/api/v1/ | REST API (proxied through Nginx) |
| **MinIO Console** | http://localhost:9001 | Object storage dashboard |

### Data Persistence

All data persists in `./docker_data/`:
- `./docker_data/postgres/` - Database records
- `./docker_data/minio/` - Uploaded images and evidence

To reset everything: `docker compose down -v && rm -rf docker_data/`

---

## 🔐 Authentication & OTP System

### How Authentication Works

This application uses **OTP (One-Time Password)** based authentication:
1. User enters their email address
2. System generates a 6-digit OTP
3. In **DEV_MODE** (default), OTP is printed to backend console (not emailed)
4. User enters OTP to login and receive JWT token

### Getting Your OTP

#### Step 1: Open the App
Navigate to http://localhost:3001

#### Step 2: Enter Email
Enter one of the test user emails (see below) and click **"Request Access"**

#### Step 3: Get OTP from Backend Logs

**Option A: Watch logs in real-time**
```bash
docker compose logs -f backend
```
Look for:
```
[DEV MODE] Skipping email send. OTP for admin@ghmc.gov.in: 845669
```

**Option B: Search logs for OTP**
```bash
docker compose logs backend | grep OTP
```

**Option C: Get most recent OTP**
```bash
docker compose logs backend --tail=20 | grep OTP
```

#### Step 4: Enter OTP
Copy the 6-digit code and enter it in the verification screen.

### Test User Accounts

| Email | Role | Dashboard URL | Capabilities |
|-------|------|---------------|--------------|
| `admin@ghmc.gov.in` | ADMIN | `/authority` | Assign issues, approve resolutions, view analytics |
| `worker@ghmc.gov.in` | WORKER | `/worker` | Accept tasks, set ETA, submit resolution proof |
| `worker2@ghmc.gov.in` | WORKER | `/worker` | Same as above (additional worker) |
| `worker3@ghmc.gov.in` | WORKER | `/worker` | Same as above (additional worker) |
| `sysadmin@urbaninfra.gov.in` | SYSADMIN | `/admin` | Platform monitoring |
| Any email (e.g., `test@example.com`) | CITIZEN | `/citizen` | Report issues, track status |

---

## 📱 Usage Guide

### For Citizens (Reporting Issues)

1. **Login** with any email (new users auto-registered as CITIZEN)
2. **Report Issue**:
   - Allow location access when prompted
   - Select issue category (Pothole, Drainage, Street Light, Garbage)
   - Take or upload a photo
   - Submit the report
3. **Track Status**: View your reported issues and their current status

### For Authority/Admin (Managing Issues)

1. **Login** as `admin@ghmc.gov.in`
2. **Operations Map**: View all issues on interactive map
   - Toggle between Markers and Heatmap view
   - Click markers to see issue details
3. **Kanban Triage**: Manage issue workflow
   - Each card has a **⋮ menu** with admin actions:
     - **Assign/Reassign Worker**: Change who's working on it
     - **Unassign Worker**: Remove worker and reset to REPORTED
     - **Move to Status**: Manually change status (REPORTED, ASSIGNED, IN_PROGRESS, RESOLVED, CLOSED)
   - **REPORTED**: New issues awaiting assignment
     - Click **"Assign"** button to quick-assign to a worker
     - Use checkbox + dropdown for bulk assignment
   - **ASSIGNED/ACCEPTED**: Issues assigned to workers
   - **IN_PROGRESS**: Workers actively resolving
   - **RESOLVED**: Awaiting admin approval
     - Click card to review before/after photos
     - **Approve** to close or **Reject** with reason
   - **CLOSED**: Completed issues
4. **Field Force**: View worker performance
   - Active task counts per worker
   - Weekly resolution statistics
5. **City Analytics**: View city-wide metrics (links to `/analytics`)

### For Workers (Resolving Issues)

1. **Login** as `worker@ghmc.gov.in` (or worker2/worker3)
2. **View Tasks**: See assigned issues on your dashboard
3. **Accept Task**:
   - Click on an assigned task
   - Set **ETA** (estimated hours to resolve)
   - Click **Accept**
4. **Start Work**: Click **"Start"** when you begin on-site
5. **Resolve**:
   - Take "after" photo showing the fix
   - Click **"Mark Resolved"**
   - Upload the resolution photo
6. **Wait for Approval**: Admin reviews and closes the issue

---

## 🔄 Complete Workflow Demo

Here's how to test the full issue lifecycle:

### 1. Report an Issue (as Citizen)
```bash
# Login as citizen
# Email: citizen@example.com
# Get OTP: docker compose logs backend | grep OTP
```
- Report a pothole with photo and location

### 2. Assign to Worker (as Admin)
```bash
# Login as admin
# Email: admin@ghmc.gov.in
# Get OTP: docker compose logs backend | grep OTP
```
- Go to **Kanban Triage**
- Find issue in **REPORTED** column
- Click **Assign** → Select worker (shows task counts)

### 3. Accept & Resolve (as Worker)
```bash
# Login as worker
# Email: worker@ghmc.gov.in
# Get OTP: docker compose logs backend | grep OTP
```
- See assigned task
- Click **Accept** with ETA (e.g., 4 hours)
- Click **Start** when beginning work
- Click **Resolve** and upload "after" photo

### 4. Approve Resolution (as Admin)
- Login as admin again
- Go to **Kanban Triage**
- Find issue in **RESOLVED** column
- Click to review before/after photos
- Click **Approve** to close

---

## 🛠️ API Reference

### Authentication
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/otp-request` | POST | Request OTP for email |
| `/api/v1/auth/login` | POST | Verify OTP, get JWT token |
| `/api/v1/auth/google-mock` | POST | Dev-only: Instant login (bypass OTP) |

### Issues
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/issues/report` | POST | Report new issue (multipart form) |
| `/api/v1/issues/my-reports?email=` | GET | Get user's reported issues |

### Admin
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/admin/issues` | GET | List all issues |
| `/api/v1/admin/workers` | GET | List all workers |
| `/api/v1/admin/workers-with-stats` | GET | Workers with task counts (sorted by workload) |
| `/api/v1/admin/worker-analytics` | GET | Detailed worker performance metrics |
| `/api/v1/admin/assign?issue_id=&worker_id=` | POST | Quick-assign single issue |
| `/api/v1/admin/bulk-assign` | POST | Assign multiple issues |
| `/api/v1/admin/update-status?issue_id=&status=` | POST | Move issue to any status |
| `/api/v1/admin/unassign?issue_id=` | POST | Remove worker, reset to REPORTED |
| `/api/v1/admin/reassign?issue_id=&worker_id=` | POST | Change assigned worker |
| `/api/v1/admin/approve?issue_id=` | POST | Approve resolved issue |
| `/api/v1/admin/reject?issue_id=&reason=` | POST | Reject with reason |

### Worker
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/worker/tasks` | GET | Get assigned tasks |
| `/api/v1/worker/tasks/{id}/accept?eta=` | POST | Accept task with ETA (hours) |
| `/api/v1/worker/tasks/{id}/start` | POST | Mark task as in-progress |
| `/api/v1/worker/tasks/{id}/resolve` | POST | Submit resolution (multipart with photo) |

### Analytics (Public)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/analytics/stats` | GET | Dashboard statistics |
| `/api/v1/analytics/heatmap` | GET | Issue heatmap data |
| `/api/v1/analytics/issues-public` | GET | Public issue list |

### Media
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/media/{issue_id}/before` | GET | Before image (report photo) |
| `/api/v1/media/{issue_id}/after` | GET | After image (resolution photo) |

---

## 📊 Issue Lifecycle

```
REPORTED → ASSIGNED → ACCEPTED → IN_PROGRESS → RESOLVED → CLOSED
    ↓         ↓          ↓            ↓            ↓
 Citizen    Admin     Worker      Worker       Admin
 reports   assigns   accepts &   starts      approves
  issue    to worker  sets ETA   on-site    resolution
```

| Status | Who Changes It | Action |
|--------|---------------|--------|
| REPORTED | Citizen | Submits issue with photo + GPS |
| ASSIGNED | Admin | Assigns to field worker |
| ACCEPTED | Worker | Accepts with ETA estimate |
| IN_PROGRESS | Worker | Starts on-site work |
| RESOLVED | Worker | Submits "after" photo proof |
| CLOSED | Admin | Approves resolution (or rejects) |

---

## 🗂️ Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API route handlers
│   │   ├── core/            # Config, security, database
│   │   ├── models/          # SQLModel domain models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   └── services/        # Business logic services
│   ├── seed.py              # Database seeder (creates test users)
│   ├── Dockerfile           # Backend container
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/           # Route pages by role
│   │   │   ├── authority/   # Admin dashboard
│   │   │   ├── worker/      # Worker dashboard
│   │   │   └── citizen/     # Citizen portal
│   │   ├── hooks/           # Custom React hooks
│   │   └── services/        # API client, auth
│   ├── Dockerfile           # Frontend container (Nginx)
│   └── nginx.conf           # Nginx config with API proxy
├── docker-compose.yml       # Full stack deployment
├── docker-compose.dev.yml   # Dev mode (DB + MinIO only)
├── docker_data/             # Persistent data (git-ignored)
├── DESIGN.md                # Technical architecture
├── HANDOFF.md               # Quick reference guide
└── README.md                # This file
```

---

## 🔧 Development

### Local Development Setup (Hot Reload)

```bash
# 1. Start database services only
docker compose -f docker-compose.dev.yml up -d

# 2. Backend (Terminal 1)
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python seed.py
uvicorn app.main:app --host 0.0.0.0 --port 8088 --reload

# 3. Frontend (Terminal 2)
cd frontend
npm install
npm run dev
```

Frontend runs at http://localhost:5173 with hot reload.

### Rebuilding Containers

```bash
# Rebuild specific service
docker compose build backend
docker compose up -d backend

# Rebuild all
docker compose up --build

# Full reset (removes all data)
docker compose down -v
rm -rf docker_data/
docker compose up --build
```

---

## 🐛 Troubleshooting

### OTP Not Showing in Logs

```bash
# Check if backend is running
docker compose ps

# View backend logs
docker compose logs backend --tail=50

# Search for OTP
docker compose logs backend | grep -i otp
```

### Login Stuck / Token Issues

```bash
# Clear browser localStorage and try again
# Or open incognito window
```

### Database Connection Issues

```bash
# Check container health
docker compose ps

# View database logs
docker compose logs db

# Reset database
docker compose down -v
docker compose up --build
```

### Frontend Not Loading

```bash
# Check frontend logs
docker compose logs frontend

# Verify nginx is running
docker compose exec frontend nginx -t
```

### MinIO/Image Issues

```bash
# Access MinIO Console
# URL: http://localhost:9001
# Username: minioadmin
# Password: minioadmin

# Check MinIO logs
docker compose logs minio
```

### Port Already in Use

```bash
# Check what's using the port
lsof -i :3001

# Kill the process or change port in docker-compose.yml
```

---

## 📄 License

MIT License - See LICENSE file for details.

## 👥 Contributors

Built for DASS (Design and Analysis of Software Systems) course project.

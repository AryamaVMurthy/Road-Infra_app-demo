# Urban Infrastructure Reporting System - Handoff Document

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12+
- Node.js 18+

### 1. Start Infrastructure
```bash
docker-compose up -d
```
This starts PostgreSQL (port 5432) and MinIO (ports 9000/9001).

### 2. Setup Backend
```bash
python3 -m venv venv
source venv/bin/activate
cd backend
pip install -r requirements.txt
python seed.py
uvicorn app.main:app --host 0.0.0.0 --port 8088
```

### 3. Setup Frontend
```bash
cd frontend
npm install
npm run dev
```

Access the app at `http://localhost:5173`

## Test Accounts

| Email | Role | Dashboard |
|-------|------|-----------|
| `admin@ghmc.gov.in` | ADMIN | `/authority` |
| `worker@ghmc.gov.in` | WORKER | `/worker` |
| `resident@hyderabad.in` | CITIZEN | `/citizen` |

**Login Flow**: Enter email → Check backend console for OTP → Enter 6-digit code

In DEV_MODE, OTPs are printed to console: `[DEV MODE] Skipping email send. OTP for email: 123456`

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Route handlers
│   │   │   ├── auth.py      # OTP authentication
│   │   │   ├── issues.py    # Citizen reporting (5m dedup)
│   │   │   ├── admin.py     # Authority operations
│   │   │   ├── worker.py    # Field force tasks
│   │   │   ├── analytics.py # Stats & heatmaps
│   │   │   └── media.py     # Image serving
│   │   ├── core/
│   │   │   ├── config.py    # Settings (DEV_MODE here)
│   │   │   └── security.py  # JWT utilities
│   │   ├── models/
│   │   │   └── domain.py    # SQLModel entities
│   │   └── services/
│   │       ├── email.py     # OTP delivery
│   │       ├── minio_client.py
│   │       ├── exif.py      # Image metadata
│   │       ├── audit.py     # Mutation logging
│   │       └── analytics.py # Stats computation
│   ├── seed.py              # DB seeder
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── citizen/     # ReportIssue, MyReports
│   │   │   ├── authority/   # AuthorityDashboard
│   │   │   ├── worker/      # WorkerHome (offline-capable)
│   │   │   └── admin/       # AdminDashboard
│   │   ├── services/
│   │   │   ├── api.js       # Axios client
│   │   │   ├── auth.js      # JWT management
│   │   │   └── offline.js   # IndexedDB service
│   │   └── hooks/
│   │       ├── useOfflineSync.js
│   │       └── useWorkerOfflineSync.js
│   ├── public/
│   │   └── sw.js            # Service Worker
│   └── package.json
├── docker-compose.yml
├── DESIGN.md                # Technical architecture
└── README.md                # Setup guide
```

## Key Features Implemented

### 1. Silent 5m Duplicate Aggregation
- **Location**: `backend/app/api/v1/issues.py`
- When a citizen reports an issue, PostGIS checks for existing issues within 5 meters
- Duplicates increment `report_count` instead of creating new issues
- User sees "Report submitted successfully" - no indication of deduplication

### 2. Offline-First Worker Resolution
- **Location**: `frontend/src/pages/worker/WorkerHome.jsx`
- Workers can resolve tasks offline (tunnels, basements, remote areas)
- Photos stored in IndexedDB (`workerResolutions` store)
- Service Worker + Background Sync API uploads when connectivity returns
- Visual indicators: "Pending Sync" badge, offline banner, toast notifications

### 3. EXIF Verification
- **Location**: `backend/app/services/exif.py`
- Extracts GPS and timestamp from uploaded photos
- Validates location proximity and timestamp recency
- Prevents fraud by ensuring photos are captured on-site

### 4. Complete Audit Trail
- **Location**: `backend/app/services/audit.py`
- Every status change logged with actor, timestamp, before/after values
- Immutable record for accountability

### 5. Real-Time Analytics
- **Location**: `backend/app/services/analytics.py`
- Heatmap data via PostGIS spatial queries
- Trend charts with actual database data (last 7 days)
- No mock/fake numbers in production views

## Environment Configuration

### Backend (`backend/.env`)
```env
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=toto
POSTGRES_DB=app
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
SECRET_KEY=your-secret-key
DEV_MODE=True
```

### Frontend (`frontend/.env`)
```env
VITE_API_URL=http://localhost:8088/api/v1
```

## Issue Lifecycle

```
REPORTED → ASSIGNED → ACCEPTED → IN_PROGRESS → RESOLVED → CLOSED
```

1. **Citizen** reports issue with photo and GPS location
2. **Admin** views on map/kanban, assigns to worker
3. **Worker** accepts with ETA (30m, 1h, 2h, 4h, 1d, 2d)
4. **Worker** starts on-site work
5. **Worker** submits "after" photo (works offline!)
6. **Admin** reviews before/after, approves or rejects

## API Quick Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/otp-request` | POST | Request OTP |
| `/auth/login` | POST | Verify OTP, get JWT |
| `/issues/report` | POST | Report issue (multipart) |
| `/issues/my-reports` | GET | Citizen's reports |
| `/admin/issues` | GET | All issues |
| `/admin/bulk-assign` | POST | Assign to worker |
| `/admin/approve` | POST | Approve resolution |
| `/worker/tasks` | GET | Worker's tasks |
| `/worker/tasks/{id}/accept` | POST | Accept with ETA |
| `/worker/tasks/{id}/resolve` | POST | Submit resolution |
| `/analytics/stats` | GET | Dashboard stats |
| `/analytics/heatmap` | GET | Heatmap data |

## Production Checklist

- [ ] Set `DEV_MODE=False` and configure real SMTP
- [ ] Use HTTPS (required for Service Workers)
- [ ] Set strong `SECRET_KEY`
- [ ] Configure MinIO access policies
- [ ] Set up PostgreSQL backups
- [ ] Enable CORS for production domain only
- [ ] Add rate limiting for OTP requests

## Troubleshooting

### OTP Not Working
In DEV_MODE, check backend console for printed OTP.

### Database Connection Issues
```bash
docker-compose ps          # Check if containers running
docker-compose logs db     # View PostgreSQL logs
```

### MinIO Issues
Access console at `http://localhost:9001` (minioadmin/minioadmin)

### Offline Sync Not Working
- Service Workers require HTTPS in production
- Check browser DevTools → Application → Service Workers
- Verify IndexedDB stores have pending data

### Maps Not Loading
- Check network for tile requests
- Verify geolocation permissions granted
- Default fallback: Hyderabad center [17.4447, 78.3483]

## Files Modified in Latest Update

### Backend (5m Dedup - Already Implemented)
- `backend/app/api/v1/issues.py` - PostGIS ST_DWithin query

### Frontend (Offline Capabilities)
- `frontend/src/services/offline.js` - IndexedDB for resolutions
- `frontend/public/sw.js` - Service Worker with Background Sync
- `frontend/src/hooks/useWorkerOfflineSync.js` - Sync hook
- `frontend/src/pages/worker/WorkerHome.jsx` - Offline resolve modal
- `frontend/src/main.jsx` - Service Worker registration

## Contact

Built for DASS course project - GHMC Infrastructure Reporting System.

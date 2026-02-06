# MARG (Monitoring Application for Road Governance) - Technical Design Document

## 1. System Overview

The MARG (Monitoring Application for Road Governance) is a full-stack platform for Municipal Authorities that enables citizens to report infrastructure issues with GPS-verified photo evidence, and provides authorities with transparent, auditable workflows for assignment, resolution, and analytics. The system is offline-capable for field workers, supports silent duplicate aggregation, and publishes public analytics with heatmaps.

---

## 2. End-to-End Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT TIER                                     │
│  ┌──────────────┐  ┌───────────────┐  ┌───────────────┐  ┌────────────────┐ │
│  │ Citizen App  │  │ Authority Ops │  │ Worker App    │  │ Analytics Dash │ │
│  │ (React)      │  │ (React)       │  │ (React + SW)  │  │ (React)        │ │
│  └──────┬───────┘  └───────┬───────┘  └───────┬───────┘  └───────┬────────┘ │
│         │                 │                  │                  │          │
│         └───────────────┬─┴──────────────────┴──────────────────┘          │
│                         │ HTTPS (REST)                                     │
└─────────────────────────┼───────────────────────────────────────────────────┘
                          ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              APPLICATION TIER                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │ FastAPI Application (Python 3.12)                                        │ │
│  │  ┌──────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐     │ │
│  │  │ Auth     │ │ Issues  │ │ Worker   │ │ Admin    │ │ Analytics    │     │ │
│  │  │ (OTP/JWT)│ │ Reporting│ │ Tasks    │ │ Ops      │ │ Stats/Heatmap│     │ │
│  │  └────┬─────┘ └────┬────┘ └────┬─────┘ └────┬─────┘ └────┬────────┘     │ │
│  │       │            │          │            │            │              │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐ │ │
│  │  │ Service Layer                                                      │ │ │
│  │  │ - Audit logging                                                    │ │ │
│  │  │ - EXIF validation                                                  │ │ │
│  │  │ - MinIO client                                                     │ │ │
│  │  │ - Analytics aggregation                                            │ │ │
│  │  └───────────────────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────┬───────────────────────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                                DATA TIER                                     │
│  ┌──────────────────────────────┐    ┌────────────────────────────────────┐ │
│  │ PostgreSQL + PostGIS          │    │ MinIO (S3-compatible object store) │ │
│  │ - Users, Issues, AuditLogs    │    │ - Issue evidence (before/after)    │ │
│  │ - Spatial data (POINT/POLYGON)│    │ - EXIF metadata                    │ │
│  └──────────────────────────────┘    └────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Network flow (Docker Compose):**
```
Browser → Nginx (frontend) → /api/* proxied → FastAPI backend → PostGIS / MinIO
```

---

## 3. Tech Stack (Full Breadth)

### 3.1 Frontend
| Category | Technology | Version | Purpose |
|---------|------------|---------|---------|
| UI Framework | React | 18.2 | Component-based UI |
| Build Tool | Vite | 5.0 | HMR + bundling |
| Styling | Tailwind CSS | 3.3 | Utility-first styles |
| Animations | Framer Motion | 12.x | UI transitions |
| Maps | Leaflet + React-Leaflet | 1.9/4.2 | Maps + markers |
| Heatmaps | leaflet.heat | 0.2 | Density overlays |
| Geocoding | leaflet-control-geocoder | 3.3 | Address search |
| Charts | Recharts | 2.9 | Data visualization |
| HTTP | Axios | 1.6 | REST client |
| State | React Query | 3.39 | Server state cache |
| Routing | React Router DOM | 6.18 | Client routing |
| PWA | Service Worker | native | Offline cache + sync |

### 3.2 Backend
| Category | Technology | Version | Purpose |
|---------|------------|---------|---------|
| Framework | FastAPI | Latest | API server |
| ORM | SQLModel | Latest | Models + DB access |
| DB Driver | psycopg2-binary | Latest | PostgreSQL driver |
| Geo | PostGIS + GeoAlchemy2 + Shapely | 3.3 | Spatial storage + ops |
| Auth | python-jose | Latest | JWT tokens |
| Passwords | passlib[bcrypt] | Latest | Hashing (if enabled) |
| Storage | MinIO | Latest | Image storage |
| Images | Pillow | Latest | EXIF parsing |
| Email | fastapi-mail | Latest | OTP delivery |

### 3.3 Infrastructure
| Service | Image | Purpose |
|---------|-------|---------|
| PostgreSQL | postgis/postgis:14-3.3 | Primary DB |
| MinIO | minio/minio | Object storage |
| Nginx | frontend container | Static hosting + API proxy |
| Docker Compose | docker-compose.yml | Multi-service orchestration |

---

## 4. Core Domain Model

### 4.1 Entities (SQLModel)
```
User ──< Issue >── Evidence
 │          │
 │          └── Category
 │
Organization ──< User
Organization ──< Issue
Zone ──< Organization
AuditLog (entity_id → Issue/User/etc.)
```

### 4.2 Spatial Fields
- **Issue.location** → `POINT (SRID 4326)`
- **Zone.boundary** → `POLYGON (SRID 4326)`

### 4.3 Key Tables (Summary)
| Table | Purpose |
|-------|---------|
| user | roles (CITIZEN, ADMIN, WORKER, SYSADMIN) |
| issue | workflow state, location, priority |
| evidence | photo links + EXIF metadata |
| auditlog | immutable mutation trail |

---

## 5. Maps & Geospatial: What is Used and How It Works

### 5.1 Map Provider & Tiles
- **Tile Provider**: CartoDB Voyager
- **URL**: `https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png`
- **Attribution**: OpenStreetMap + CARTO

### 5.2 Frontend Mapping Stack
- **Leaflet + React-Leaflet** for MapContainer, TileLayer, Marker
- **leaflet.heat** for heatmap layer (`HeatmapLayer.jsx`)
- **leaflet-control-geocoder** for address search (`SearchField.jsx`)
- **LocateControl.jsx** adds GPS button and accuracy ring
- **Geolocation Hook**: `useGeolocation.js` (fallback to default center if denied)

### 5.3 Backend Geospatial Stack
- **PostGIS** stores issue location as POINT geometry.
- **GeoAlchemy2** integrates geometry with SQLModel.
- **Issue.lat/lng properties** extract coordinates via `to_shape()`.

### 5.4 Heatmap Data Flow (End-to-End)
```
Frontend (Authority/Analytics/Worker) → GET /api/v1/analytics/heatmap
Backend → SELECT Issue WHERE status != CLOSED
Service → [{lat, lng, intensity}]
Frontend → HeatmapLayer (leaflet.heat) renders overlay
```

---

## 6. End-to-End Workflows

### 6.1 Citizen Report Flow
```
Citizen UI → Select Category + Location + Photo → POST /issues/report
  └─ Backend: EXIF parse → PostGIS 5m dedup → Save Issue + Evidence
  └─ MinIO: store report photo
Return: issue_id (existing if duplicate)
```

### 6.2 Authority Assignment Flow
```
Authority UI → View map + kanban → Assign worker
  └─ POST /admin/assign or /admin/bulk-assign
  └─ AuditLog written for assignment
```

### 6.3 Worker Resolution Flow (Online)
```
Worker UI → Accept task → Start work → Resolve with photo
  └─ POST /worker/tasks/{id}/accept (ETA)
  └─ POST /worker/tasks/{id}/start
  └─ POST /worker/tasks/{id}/resolve (multipart)
  └─ MinIO stores resolution photo
  └─ AuditLog records state transitions
```

### 6.4 Worker Resolution Flow (Offline)
```
Offline → photo saved in IndexedDB (workerResolutions)
Service Worker registers 'sync-resolutions'
On reconnect → SW uploads multipart to /worker/tasks/{id}/resolve
On success → resolution removed from IndexedDB
Client notified via postMessage
```

### 6.5 Audit Trail Flow
```
Any status/assignment change → AuditService.log
Stored in auditlog table → retrieved via /analytics/audit/{entity_id}
```

---

## 7. API Surface (Grouped)

### Auth
| Method | Endpoint | Notes |
|--------|----------|------|
| POST | `/api/v1/auth/otp-request` | email → OTP |
| POST | `/api/v1/auth/login` | OTP → JWT |
| POST | `/api/v1/auth/google-mock` | Dev-only shortcut |

### Issues (Citizen)
| Method | Endpoint | Notes |
|--------|----------|------|
| POST | `/api/v1/issues/report` | multipart with photo |
| GET | `/api/v1/issues/my-reports` | by email |

### Authority/Admin
| Method | Endpoint | Notes |
|--------|----------|------|
| GET | `/api/v1/admin/issues` | all issues |
| GET | `/api/v1/admin/workers` | workers list |
| GET | `/api/v1/admin/workers-with-stats` | active task count |
| POST | `/api/v1/admin/assign` | quick assign |
| POST | `/api/v1/admin/bulk-assign` | batch assign |
| POST | `/api/v1/admin/approve` | close issue |
| POST | `/api/v1/admin/reject` | reject to in-progress |
| POST | `/api/v1/admin/update-status` | manual status change |

### Worker
| Method | Endpoint | Notes |
|--------|----------|------|
| GET | `/api/v1/worker/tasks` | assigned tasks |
| POST | `/api/v1/worker/tasks/{id}/accept` | accept + ETA |
| POST | `/api/v1/worker/tasks/{id}/start` | start work |
| POST | `/api/v1/worker/tasks/{id}/resolve` | resolve w/ photo |

### Analytics (Public)
| Method | Endpoint | Notes |
|--------|----------|------|
| GET | `/api/v1/analytics/stats` | global stats |
| GET | `/api/v1/analytics/heatmap` | map heat data |
| GET | `/api/v1/analytics/issues-public` | issue markers |
| GET | `/api/v1/analytics/audit/{id}` | audit trail |

### Media
| Method | Endpoint | Notes |
|--------|----------|------|
| GET | `/api/v1/media/{issue_id}/before` | report photo |
| GET | `/api/v1/media/{issue_id}/after` | resolution photo |

---

## 8. Service Worker & Offline Architecture

```
Browser (Worker) → IndexedDB → Background Sync → Service Worker
  └─ sync-resolutions → POST /worker/tasks/{id}/resolve
```

- Cache strategy: app shell caching for GET assets
- API calls bypass cache (no API caching)
- Offline queue uses IndexedDB `workerResolutions`

---

## 9. Security & Access Control

### 9.1 Authentication
- OTP email flow (`/auth/otp-request`)
- JWT access + refresh issued on login (`/auth/login`)
- Tokens stored as HttpOnly cookies (`access_token`, `refresh_token`)
- Refresh rotation via `/auth/refresh`
- Session identity resolved by `/auth/me`

### 9.2 Authorization
- Role-based gates in frontend routes
- Backend guards via `get_current_user` dependency

### 9.3 Data Protection
- Input validation with Pydantic/SQLModel
- Only image MIME types accepted for uploads
- AuditLog records immutable state changes
- Cookie auth reduces XSS exposure versus token-in-localStorage patterns

### 9.4 OTP Delivery Modes
- `DEV_MODE=true`: OTP generation is persisted and logged; email send is skipped.
- `DEV_MODE=false`: SMTP send attempted using configured `MAIL_*` values.

---

## 10. Deployment Topology

### 10.1 Docker Compose
```
frontend (Nginx) → proxy /api → backend (FastAPI)
backend → db (PostGIS)
backend → minio (S3)
```

### 10.2 Local Development (Hot Reload)
1. `docker compose -f docker-compose.dev.yml up -d`
2. Backend: `uvicorn app.main:app --reload --port 8088`
3. Frontend: `npm run dev` (Vite)

---

## 11. Technical Workflows (Flowcharts)

### 11.1 Report + Dedup + Evidence Flow
```
┌────────────┐   POST /issues/report   ┌────────────────────────────┐
│ Citizen UI │ ───────────────────────▶│ FastAPI issues.report_issue │
└────────────┘                         ├────────────────────────────┤
                                       │ 1. Fetch/Create User       │
                                       │ 2. EXIF Extract + Validate │
                                       │ 3. ST_DWithin 5m check     │
                                       │ 4. Save photo to MinIO     │
                                       │ 5. Create/Update Issue     │
                                       └────────────┬───────────────┘
                                                    │
                                                    ▼
                                           ┌──────────────────┐
                                           │ PostgreSQL/PostGIS│
                                           └──────────────────┘
```

### 11.2 Assignment + Worker Lifecycle
```
REPORTED → ASSIGNED → ACCEPTED → IN_PROGRESS → RESOLVED → CLOSED
   │           │          │            │            │
 Citizen     Admin       Worker       Worker       Admin
```

### 11.3 Offline Resolution Sync
```
Worker offline → IndexedDB (workerResolutions)
         ↓
Service Worker sync-resolutions
         ↓
POST /worker/tasks/{id}/resolve
         ↓
MinIO stores resolution + Issue marked RESOLVED
```

---

## 12. Testing Strategy

| Layer | Tools | Notes |
|------|------|------|
| Frontend Unit | Vitest | Component + hook testing |
| Frontend E2E | Playwright | UI flows + map checks |
| Backend Unit | pytest | Services & business logic |
| Backend Integration | pytest | API + DB interactions |

---

## 13. Key Implementation Locations

| Concern | File |
|---------|------|
| Issue report + dedup | `backend/app/api/v1/issues.py` |
| Worker resolve flow | `backend/app/api/v1/worker.py` |
| Admin operations | `backend/app/api/v1/admin.py` |
| Heatmap data | `backend/app/services/analytics.py` |
| Maps (UI) | `frontend/src/pages/*` |
| Heatmap layer | `frontend/src/components/HeatmapLayer.jsx` |
| Geocoding search | `frontend/src/components/SearchField.jsx` |
| GPS button | `frontend/src/components/LocateControl.jsx` |
| Offline queue | `frontend/src/services/offline.js` |
| Service Worker | `frontend/public/sw.js` |

---

## 14. Known Constraints & Notes

- Auth API base URL is `/api/v1` through Nginx proxy in docker-compose.
- Frontend `auth.js` uses `VITE_API_URL` or localhost fallback; keep aligned in envs.
- Map tiles and attribution are hardcoded per-page; consistency is required.
- Background Sync requires HTTPS in production.

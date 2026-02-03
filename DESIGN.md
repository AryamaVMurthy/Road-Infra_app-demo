# Urban Infrastructure Reporting System - Technical Design Document

## 1. System Overview

The Urban Infrastructure Issue Reporting System (UIRS) is a production-ready platform for GHMC (Greater Hyderabad Municipal Corporation) that enables citizens to report infrastructure issues with GPS-verified photo evidence. The system provides complete transparency through audit trails, automated duplicate detection, and offline-first resilience.

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION TIER                                │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │
│  │   Citizen   │ │  Authority  │ │   Worker    │ │  Analytics  │       │
│  │   Portal    │ │  Dashboard  │ │    App      │ │  Dashboard  │       │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘       │
│         └───────────────┴───────┬───────┴───────────────┘               │
│                    React 18 + Vite + Tailwind CSS                       │
│                    Service Worker + IndexedDB (Offline)                 │
└─────────────────────────────────┼───────────────────────────────────────┘
                                  │ HTTPS/REST API
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         APPLICATION TIER                                 │
│  ┌────────────────────────────────────────────────────────────────┐     │
│  │                     FastAPI Application                         │     │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │     │
│  │  │   Auth   │ │  Issues  │ │  Admin   │ │ Analytics│          │     │
│  │  │  Module  │ │  Module  │ │  Module  │ │  Module  │          │     │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘          │     │
│  │       └────────────┴─────┬──────┴────────────┘                 │     │
│  │  ┌──────────────────────────────────────────────────────┐      │     │
│  │  │              Service Layer (Business Logic)           │      │     │
│  │  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐         │      │     │
│  │  │  │ Email  │ │  EXIF  │ │ MinIO  │ │ Audit  │         │      │     │
│  │  │  │Service │ │Service │ │Client  │ │Service │         │      │     │
│  │  │  └────────┘ └────────┘ └────────┘ └────────┘         │      │     │
│  │  └──────────────────────────────────────────────────────┘      │     │
│  └────────────────────────────────────────────────────────────────┘     │
│                    Python 3.12 + FastAPI + SQLModel                      │
└─────────────────────────────────┼───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           DATA TIER                                      │
│  ┌─────────────────────────────┐    ┌─────────────────────────────┐    │
│  │   PostgreSQL + PostGIS      │    │         MinIO               │    │
│  │  • User Management          │    │   (Object Storage)          │    │
│  │  • Issue Lifecycle          │    │  • Before Images            │    │
│  │  • Geospatial Data          │    │  • After Images             │    │
│  │  • Audit Logs               │    │  • EXIF Metadata            │    │
│  └─────────────────────────────┘    └─────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

## 3. Technology Stack

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **Frontend Framework** | React | 18.2 | Component-based UI |
| **Build Tool** | Vite | 5.0 | Fast HMR, ESM bundling |
| **Styling** | Tailwind CSS | 3.3 | Utility-first CSS |
| **Animations** | Framer Motion | 12.x | Declarative animations |
| **Maps** | Leaflet + React-Leaflet | 1.9/4.2 | Interactive mapping |
| **Heatmaps** | Leaflet.heat | 0.2 | Density visualization |
| **Geocoding** | Leaflet-control-geocoder | 3.3 | Address search |
| **Charts** | Recharts | 2.9 | Data visualization |
| **HTTP Client** | Axios | 1.6 | API communication |
| **Data Fetching** | React Query | 3.39 | Server state management |
| **Routing** | React Router DOM | 6.18 | Client-side routing |
| **Icons** | Lucide React | 0.292 | Icon library |
| **Backend Framework** | FastAPI | Latest | High-performance Python API |
| **ORM** | SQLModel | Latest | Pydantic + SQLAlchemy |
| **Database** | PostgreSQL | 14 | Primary database |
| **Geospatial** | PostGIS | 3.3 | Spatial extension |
| **Object Storage** | MinIO | Latest | S3-compatible storage |
| **Authentication** | python-jose | Latest | JWT tokens |
| **Image Processing** | Pillow | Latest | EXIF extraction |
| **ASGI Server** | Uvicorn | Latest | Production server |

## 4. Core Features

### 4.1 Silent 5m Duplicate Aggregation

When a citizen reports an issue, the backend performs a PostGIS proximity check:

```python
point_wkt = f"SRID=4326;POINT({lng} {lat})"
statement = select(Issue).where(
    Issue.status != "CLOSED",
    func.ST_DWithin(Issue.location, func.ST_GeomFromText(point_wkt), 5.0 / 111320.0)
)
duplicate_issue = session.exec(statement).first()

if duplicate_issue:
    duplicate_issue.report_count += 1
    # Add new evidence, return existing issue_id
else:
    # Create new issue
```

### 4.2 Offline-First Architecture

The system uses Service Workers with Background Sync API for resilience in low-connectivity environments.

**Citizen Reports (Offline):**
1. User submits report while offline
2. Report saved to IndexedDB (`offlineReports` store)
3. Service Worker registers `sync-reports` event
4. When connectivity returns, Background Sync uploads pending reports

**Worker Resolutions (Offline):**
1. Worker resolves task while offline (tunnel, basement, remote area)
2. Resolution photo saved to IndexedDB (`workerResolutions` store)
3. UI shows optimistic "Pending Sync" badge on task card
4. Service Worker registers `sync-resolutions` event
5. Background Sync uploads resolution when device is back online
6. Toast notification confirms sync completion

**IndexedDB Schema:**
```javascript
const DB_NAME = 'UrbanInfraDB';
const DB_VERSION = 2;

// Stores:
// - offlineReports: Citizen issue reports
// - workerResolutions: Worker task resolutions with photos
```

### 4.3 EXIF Verification

All uploaded photos are validated for:
- GPS coordinates (must match submitted location within 5m)
- Timestamp (must be within 7 days)
- Device metadata (logged for audit trail)

### 4.4 Issue State Machine

```
REPORTED → ASSIGNED → ACCEPTED → IN_PROGRESS → RESOLVED → CLOSED
    ↓         ↓                       ↓            ↓
 (Citizen)  (Admin)     ←←←←←←   (Worker)     (Admin approves)
                                    ↓
                               REJECTED → IN_PROGRESS (re-work)
```

| State | Actor | Action |
|-------|-------|--------|
| REPORTED | Citizen | Submits issue with photo and GPS |
| ASSIGNED | Admin | Assigns to field worker |
| ACCEPTED | Worker | Accepts with ETA |
| IN_PROGRESS | Worker | Starts on-site work |
| RESOLVED | Worker | Submits "after" photo proof |
| CLOSED | Admin | Approves resolution |

## 5. Database Schema

### 5.1 Core Tables

**user**
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| email | TEXT | Unique, indexed |
| role | TEXT | CITIZEN, ADMIN, WORKER, SYSADMIN |
| org_id | UUID | FK to organization |
| status | TEXT | ACTIVE, INACTIVE |

**issue**
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| category_id | UUID | FK to category |
| status | TEXT | Current state |
| location | GEOMETRY(POINT) | PostGIS Point (SRID 4326) |
| reporter_id | UUID | FK to user |
| worker_id | UUID | FK to user (nullable) |
| report_count | INTEGER | Aggregated duplicate count |
| priority | TEXT | P1, P2, P3, P4 |
| eta_duration | TEXT | Worker's ETA |
| created_at | TIMESTAMP | Creation time |
| updated_at | TIMESTAMP | Last update |

**evidence**
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| issue_id | UUID | FK to issue |
| type | TEXT | REPORT or RESOLVE |
| file_path | TEXT | MinIO path |
| exif_timestamp | TIMESTAMP | From image metadata |
| exif_lat | FLOAT | From image metadata |
| exif_lng | FLOAT | From image metadata |

**auditlog**
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| action | TEXT | STATUS_CHANGE, ASSIGNMENT, etc. |
| entity_id | UUID | Affected record ID |
| actor_id | UUID | User who performed action |
| old_value | TEXT | Previous state |
| new_value | TEXT | New state |
| created_at | TIMESTAMP | When logged |

### 5.2 Spatial Indexes

```sql
CREATE INDEX idx_issue_location ON issue USING GIST(location);
CREATE INDEX idx_zone_boundary ON zone USING GIST(boundary);
```

## 6. API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/otp-request` | Generate and send OTP |
| POST | `/api/v1/auth/login` | Verify OTP, return JWT |

### Issues (Citizen)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/issues/report` | Submit new issue (multipart) |
| GET | `/api/v1/issues/my-reports` | Get user's reports |

### Admin (Authority)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/issues` | List all issues |
| GET | `/api/v1/admin/workers` | List workers |
| POST | `/api/v1/admin/bulk-assign` | Assign issues to worker |
| POST | `/api/v1/admin/approve` | Approve resolution |
| POST | `/api/v1/admin/reject` | Reject with reason |

### Worker
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/worker/tasks` | Get assigned tasks |
| POST | `/api/v1/worker/tasks/{id}/accept` | Accept with ETA |
| POST | `/api/v1/worker/tasks/{id}/start` | Start work |
| POST | `/api/v1/worker/tasks/{id}/resolve` | Submit resolution (multipart) |

### Analytics (Public)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/analytics/stats` | Dashboard statistics |
| GET | `/api/v1/analytics/heatmap` | Geospatial density data |
| GET | `/api/v1/analytics/issues-public` | Public issue list |

### Media
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/media/{issue_id}/before` | Before image |
| GET | `/api/v1/media/{issue_id}/after` | After image |

## 7. Frontend Architecture

### 7.1 Component Structure

```
src/
├── main.jsx                 # App entry, Service Worker registration
├── App.jsx                  # Router configuration
├── pages/
│   ├── Login.jsx            # OTP authentication
│   ├── AnalyticsDashboard.jsx
│   ├── citizen/
│   │   ├── CitizenHome.jsx
│   │   ├── ReportIssue.jsx  # 3-step wizard
│   │   └── MyReports.jsx
│   ├── authority/
│   │   └── AuthorityDashboard.jsx  # Map + Kanban
│   ├── worker/
│   │   └── WorkerHome.jsx   # Tasks + Offline resolve
│   └── admin/
│       └── AdminDashboard.jsx
├── components/
│   ├── LocateControl.jsx    # GPS button for maps
│   ├── SearchField.jsx      # Geocoding search
│   ├── HeatmapLayer.jsx     # Leaflet heatmap
│   └── EvidenceGallery.jsx  # Before/after viewer
├── services/
│   ├── api.js               # Axios instance
│   ├── auth.js              # JWT management
│   └── offline.js           # IndexedDB operations
├── hooks/
│   ├── useOfflineSync.js    # Citizen report sync
│   └── useWorkerOfflineSync.js  # Worker resolution sync
└── public/
    └── sw.js                # Service Worker
```

### 7.2 State Management

- **React useState/useEffect**: Component-local state
- **React Query**: Server state caching
- **localStorage**: JWT token persistence
- **IndexedDB**: Offline data persistence

### 7.3 Service Worker

The Service Worker (`public/sw.js`) handles:
- Static asset caching for offline app shell
- Background Sync for pending uploads
- Message passing for auth token retrieval
- Client notifications on sync completion

## 8. Security

### 8.1 Authentication Flow
1. User enters email → OTP sent (or printed in DEV_MODE)
2. OTP verified → JWT issued (7-day expiry)
3. JWT included in Authorization header for all API calls

### 8.2 Authorization (RBAC)
| Role | Permissions |
|------|-------------|
| CITIZEN | Create issues, view own reports |
| WORKER | View/accept/resolve assigned tasks |
| ADMIN | All issue management, worker assignment |
| SYSADMIN | Full system access, analytics, audit |

### 8.3 Data Protection
- HTTPS enforced in production
- Pydantic validation on all inputs
- SQL injection prevented via ORM
- File uploads restricted to image MIME types

## 9. Deployment

### Development
```bash
# Start database services
docker-compose up -d

# Backend
cd backend && source ../venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8088

# Frontend
cd frontend && npm run dev
```

### Production Considerations
- Use HTTPS for Service Worker support
- Configure real SMTP for OTP delivery
- Set up MinIO bucket policies
- Enable PostgreSQL replication
- Add CDN for static assets

## 10. Testing Strategy

| Layer | Tool | Focus |
|-------|------|-------|
| Backend Unit | pytest | Business logic, spatial queries |
| Backend Integration | pytest | API endpoints, DB transactions |
| Frontend Unit | Vitest | Component renders, hooks |
| E2E | Playwright | Full user flows, offline scenarios |

### Key Test Scenarios
- Duplicate detection: 4.9m (should aggregate) vs 5.1m (should create new)
- Offline sync: Network throttling, IndexedDB persistence
- Concurrent access: Multiple workers accepting same task
- Audit integrity: Every mutation creates exactly one AuditLog entry

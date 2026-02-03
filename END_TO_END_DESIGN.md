# Urban Infrastructure Issue Reporting System: End-to-End Design Document

## Part 1: High-Level Design (HLD)

### 1.1 Project Mission
The Urban Infrastructure Issue Reporting System is designed to provide a high-integrity, transparent, and resilient channel for citizens of Hyderabad (GHMC) to report municipal issues. The platform ensures that reporting is location-accurate, deduplicated, and professionally resolved by field workers under administrative supervision.

### 1.2 Architectural Goals
- **Geometric Precision**: Absolute accuracy in identifying issue locations using GPS and PostGIS.
- **Fraud Prevention**: Mandatory EXIF validation to ensure evidence is captured in-situ and in real-time.
- **Operational Efficiency**: Automated triage, bulk assignment, and SLA tracking.
- **Resilience**: A PWA-first approach that survives intermittent connectivity in urban canyons.
- **Accountability**: A non-repudiable audit trail of every state transition in the system.

### 1.3 System Context & Persona Roles
1.  **Citizen (The Reporter)**: Authenticates via OTP, captures evidence, and tracks resolution status.
2.  **Authority Admin (The Orchestrator)**: Manages a specific zone, triages incoming reports, and assigns tasks to workers.
3.  **Field Worker (The Resolver)**: Receives tasks, provides ETAs, and submits visual proof of resolution.
4.  **System Admin (The Governor)**: Monitors city-wide metrics, manages organizational onboarding, and audits system integrity.

### 1.4 High-Level Component Architecture
The system follows a **Domain-Driven Design (DDD)** pattern, strictly separating the core business rules from infrastructure concerns.

```text
[ Citizen PWA ]   [ Authority Dashboard ]   [ Worker App ]   [ Admin Suite ]
       |                   |                      |               |
       +-------------------+-----------+----------+---------------+
                                       |
                             [ Nginx / Reverse Proxy ]
                                       |
                             [ FastAPI Application ]
            +--------------------------+-------------------------+
            |                          |                         |
    [ Domain Logic ]           [ Application Services ]    [ API Interfaces ]
    - Entities                 - Audit Service             - Auth (JWT/OTP)
    - Value Objects            - EXIF Processor            - Issue Mgmt
    - Domain Services          - Notification Engine       - Analytics
            |                          |                         |
            +--------------------------+-------------------------+
                                       |
            +--------------------------+-------------------------+
            |                          |                         |
    [ Persistence Layer ]      [ Object Storage ]         [ External ]
    - Postgres + PostGIS       - Minio (S3 API)           - SMTP Relay
    - Redis (Cache)            - Local File Mock          - SMS Gateway
```

### 1.5 Core Data Flow (Reporting to Resolution)
1.  **Ingestion**: Citizen captures a photo. PWA extracts coordinates.
2.  **Spatial Analysis**: Backend performs an `ST_DWithin` query. If an issue exists within 5m, the report is aggregated (incrementing `report_count`).
3.  **Verification**: EXIF data is compared against provided metadata. Mismatches trigger flagging for manual review.
4.  **Triage**: Admin views the Kanban board. Issues are prioritized (P1-P4) based on category defaults or manual override.
5.  **Assignment**: Issues are assigned to workers (individually or in bulk).
6.  **Resolution**: Worker submits an "After" photo. System validates the location again.
7.  **Closure**: Admin performs a side-by-side review and marks the issue as `CLOSED`.

### 1.6 Resilience & Offline Strategy
The platform utilizes a **Service Worker + IndexedDB** architecture.
- **Store-and-Forward**: If the network is lost, the reporting form saves the binary image and metadata to IndexedDB.
- **Background Sync**: A listener in the PWA detects the `online` event and orchestrates a sequential upload of queued reports.

### 1.7 Security Framework
- **Identity**: Stateless JWT-based authentication.
- **Access Control**: Role-Based Access Control (RBAC) enforced at the API route level.
- **Brute Force Protection**: In-memory (transitional to Redis) rate limiting for OTP requests.
- **Data Integrity**: Geometric constraints in the database ensure no orphaned coordinates.

### 1.8 Infrastructure Strategy
- **Containerization**: Entire stack is dockerized for parity across environments.
- **Volumes**: Persistent storage for Postgres data and Minio buckets to prevent data loss.
- **Networking**: Isolated backend network with only the Reverse Proxy and Frontend exposed.

### 1.9 Governance & Transparency
- **Audit Logs**: Every mutation (actor, timestamp, before, after) is immutable.
- **Analytics**: Heatmaps for NGOs to identify systemic infrastructure failure points.

### 1.10 Data Evolution & Migrations
- **Schema Management**: The system utilizes Alembic for version-controlled database migrations.
- **Spatial Indexes**: GiST indexes are maintained on all geometry columns (`location` in `issue`, `boundary` in `zone`) to ensure O(log N) query performance for proximity searches.
- **Backfills**: Service-layer hooks are designed to backfill GHMC Zone associations if municipal boundaries are redrawn.

### 1.11 Scalability & Performance Bottlenecks
- **Spatial Query Load**: As the `issue` table grows to 100k+ rows, `ST_DWithin` is optimized using bounding box intersections before fine-grained distance calculation.
- **Image Serving**: Minio is configured with a Content Delivery Network (CDN) or a cache layer to reduce load on the object storage engine during high-traffic administrative reviews.
- **Concurrency**: The FastAPI engine uses `async` drivers for both Postgres and Minio to maximize I/O throughput.

### 1.12 Disaster Recovery & High Availability
- **DB Replication**: Production environments employ a Primary-Standby architecture for PostgreSQL.
- **Object Storage Redundancy**: Minio buckets are replicated across availability zones (standard S3 protocol).
- **Session Resilience**: JWT tokens are stateless, allowing any backend node to handle any request without shared session state.

### 1.13 Compliance & Accessibility
- **UX4G Standards**: The frontend follows the Indian Government's UX4G Handbook, prioritizing high contrast, clear typography (Inter/Geist), and accessibility for low-literacy users.
- **GDPR/Privacy**: PII (Emails/Locations) is encrypted at rest, and data retention policies automatically anonymize closed reports after 24 months.

---

## Part 2: Low-Level Design (LLD)

### 2.1 Detailed Domain Model Spec
The domain is modeled using **SQLModel (SQLAlchemy + Pydantic)** to ensure type safety from DB to API.

#### **User Entity**
- `id`: UUID (Primary Key)
- `email`: String (Unique, Indexed)
- `role`: RoleEnum (CITIZEN, ADMIN, WORKER, SYSADMIN)
- `org_id`: UUID (Nullable, Foreign Key to Organization)
- `status`: StatusEnum (ACTIVE, INACTIVE)
- `last_login_at`: DateTime (Nullable)

#### **Issue Entity**
- `id`: UUID (Primary Key)
- `category_id`: UUID (Foreign Key to Category)
- `status`: IssueStatusEnum (REPORTED, ASSIGNED, IN_PROGRESS, RESOLVED, CLOSED)
- `location`: Geometry(POINT, 4326) (GIST Indexed)
- `address`: String (Optional)
- `reporter_id`: UUID (Foreign Key to User)
- `worker_id`: UUID (Nullable, Foreign Key to User)
- `org_id`: UUID (Nullable, Foreign Key to Organization)
- `priority`: PriorityEnum (P1, P2, P3, P4)
- `report_count`: Integer (Default: 1)
- `eta_duration`: String (e.g., "2h", "1d")
- `created_at`: DateTime
- `updated_at`: DateTime

### 2.2 Database Schema (PostgreSQL/PostGIS)
PostgreSQL is the source of truth, enhanced by PostGIS for spatial computation.

| Table | Column | Type | Index |
| :--- | :--- | :--- | :--- |
| **issue** | `location` | `GEOMETRY(Point, 4326)` | GiST |
| **zone** | `boundary` | `GEOMETRY(Polygon, 4326)` | GiST |
| **user** | `email` | `VARCHAR` | B-Tree |
| **otp** | `code` | `VARCHAR(6)` | B-Tree |
| **audit_log**| `actor_id` | `UUID` | B-Tree |

### 2.3 Key Algorithms & Logic

#### **Silent Duplicate Aggregation**
Implemented in `backend/app/api/v1/issues.py`:
```python
# Proximity check at the DB level
point_wkt = f"SRID=4326;POINT({lng} {lat})"
# 5m in degrees approx (1 degree ~ 111km)
DISTANCE_THRESHOLD = 5.0 / 111320.0 
statement = select(Issue).where(
    Issue.status != "CLOSED",
    func.ST_DWithin(Issue.location, func.ST_GeomFromText(point_wkt), DISTANCE_THRESHOLD)
)
duplicate = session.exec(statement).first()
```

#### **EXIF Metadata Extraction**
Using **Pillow** in `backend/app/services/exif.py`:
- Parses `GPSInfo` (lat/lng/alt) and `DateTimeOriginal` tags.
- Handles rational number conversions for coordinate precision.
- Returns a normalized dictionary for validation against user-provided metadata.

### 2.4 API Specification (Request/Response)

#### **Issue Reporting**
- `POST /api/v1/issues/report`
- **Body**: `multipart/form-data`
  - `photo`: Binary
  - `category_id`: UUID
  - `lat`: Float
  - `lng`: Float
- **Logic**: If `duplicate`, returns 200 OK with `issue_id` (increments count). If new, creates and returns 201 Created.

#### **Issue State Transitions Table**
| Start State | Action | Actor | End State | Side Effect |
| :--- | :--- | :--- | :--- | :--- |
| (None) | Create | Citizen | `REPORTED` | Deduplication check |
| `REPORTED` | Assign | Admin | `ASSIGNED` | Audit log created |
| `ASSIGNED` | Accept | Worker | `ACCEPTED` | `accepted_at` timestamp |
| `ACCEPTED` | Start | Worker | `IN_PROGRESS` | `updated_at` heartbeat |
| `IN_PROGRESS` | Resolve | Worker | `RESOLVED` | Image upload to Minio |
| `RESOLVED` | Close | Admin | `CLOSED` | Issue removed from active Kanban |
| `RESOLVED` | Reject | Admin | `IN_PROGRESS` | `rejection_reason` logged |
| `REPORTED` | Dismiss | Admin | `DISMISSED` | Reason required |

### 2.5 Frontend Component architecture

#### **State Management (React)**
- **Auth Context (React useState/localStorage)**: Manages the JWT, role detection, and logout logic.
- **Offline Queue (IndexedDB)**:
  - `reports`: Stores objects containing `FormData` blobs and metadata.
  - `synced`: Temporary log of successfully synced items for local UI updates.

#### **Visual Layer (Tailwind CSS + Lucide React)**
- **Layout Personas**: Dynamic wrappers that switch between the Citizen's mobile-first layout and the Admin's sidebar-centric view.
- **KanbanBoard**: Built using `framer-motion` for fluid drag-and-drop visuals, mapped to status columns.
- **MapLayer**: A Leaflet wrapper that provides a unified interface for "Click-to-lock" (Citizen) and "Cluster-view" (Admin).

### 2.6 Resilience: Offline Logic Diagram
1. User clicks **Submit**.
2. Service checks `navigator.onLine`.
3. **Branch Offline**:
   - Save report to `IndexedDB.offlineReports`.
   - Trigger `Toast: Report saved locally`.
4. **Window 'online' Event**:
   - `useEffect` hook in `App.jsx` triggers `useOfflineSync`.
   - Service iterates through `offlineReports`.
   - Sequential `POST` requests executed.
   - On success: `IndexedDB.delete(id)` + `Toast: Reports Synced`.

### 2.7 Testing & Quality Assurance
- **Geometric Rigor**: Pytest suite specifically testing points at 4.9m (should group) and 5.1m (should create new).
- **Concurrency**: Integration tests simulating multiple workers accepting the same task simultaneously (Row-level locking verification).
- **PWA Integrity**: Playwright suite with network throttling and manual "Stop Server" injection to verify IndexedDB persistence.
- **Audit Compliance**: Verification that every `PATCH` to an Issue generates exactly one `AuditLog` entry with the correct `actor_id`.

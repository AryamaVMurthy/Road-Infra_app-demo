# MARG (Monitoring Application for Road Governance) - V0-Handoff-1

## 1. System Architecture Overview

MARG is a high-integrity, full-stack municipal infrastructure management system designed for scale, transparency, and offline resilience.

- **Frontend**: React 18, Vite, Tailwind CSS, Leaflet (Maps), Framer Motion (Animations).
- **Backend**: FastAPI (Python), SQLModel (ORM), Pydantic (Validation).
- **Database**: PostgreSQL with **PostGIS** for geospatial operations.
- **Storage**: MinIO (S3-compatible) for issue evidence and resolution photos.
- **Infrastructure**: Dockerized multi-container setup (Frontend, Backend, DB, MinIO, Nginx).

---

## 2. Authentication & Role-Based Access Control (RBAC)

### Authentication Flow
1. **OTP Request**: User submits email -> 6-digit OTP generated and stored in DB (valid for 10 mins).
2. **Login/Verify**: User submits OTP -> JWT token issued containing `user_id` and `role`.
3. **Session**: JWT stored in `localStorage` and sent in `Authorization: Bearer <token>` headers.

### Roles & Permissions
Currently, roles are defined in the `User` model and enforced at the controller level:

| Role | Scope | Key Capabilities |
|------|-------|------------------|
| **CITIZEN** | Public / Self | Report issues, track own reports, view public analytics. |
| **WORKER** | Assigned Tasks | Accept tasks, set ETA, start work, resolve tasks (with photo proof). |
| **ADMIN** | Jurisdiction | Triage issues, assign workers, approve/reject resolutions, view audit trails. |
| **SYSADMIN**| Platform | System-wide configuration, audit logs, advanced metrics. |

---

## 3. Backend Controller Specifications

### 3.1 Authentication (`/auth`)
- `POST /otp-request`: Generates OTP. In `DEV_MODE`, prints to console.
- `POST /login`: Validates OTP and returns JWT.
- `POST /google-mock`: (Dev Only) Instant login for any email to facilitate testing.

### 3.2 Issue Management (`/issues`)
- `POST /report`: The primary citizen entry point. 
  - **Deduplication**: Uses PostGIS `ST_DWithin` to check if an issue of the same category exists within 5 meters. If found, it increments `report_count` instead of creating a new record.
  - **Media**: Uploads photo to MinIO.
  - **Metadata**: Stores GPS coordinates and address.
- `GET /my-reports`: Retrieves issues reported by the authenticated user.

### 3.3 Worker Operations (`/worker`)
- `GET /tasks`: Returns issues assigned to the current worker.
- `POST /tasks/{id}/accept`: Transitions status to `ACCEPTED`. Requires `eta_date`.
- `POST /tasks/{id}/start`: Transitions status to `IN_PROGRESS`.
- `POST /tasks/{id}/resolve`: 
  - **Photo Proof**: Requires "after" photo upload.
  - **EXIF Verification**: (Optional Service) Extracts GPS/Timestamp from photo to ensure worker was on-site.
  - Transitions status to `RESOLVED`.

### 3.4 Admin Operations (`/admin`)
- `GET /issues`: Full list of issues with relationships for Kanban board.
- `POST /assign`: Manual assignment of worker to issue.
- `POST /bulk-assign`: Assigns multiple issues to a single worker.
- `POST /update-status`: Manual status override (Audit logged).
- `POST /approve`: Transitions `RESOLVED` -> `CLOSED`.
- `POST /reject`: Transitions `RESOLVED` -> `ASSIGNED` with reason.
- `POST /update-priority`: Updates issue priority (P1-P4).

### 3.5 Analytics (`/analytics`)
- `GET /stats`: Aggregated counts for dashboards.
- `GET /heatmap`: GeoJSON-like points for Leaflet heatmap layer.
- `GET /audit-all`: (Admin) Full platform mutation history.

---

## 4. Key Engineering Features

### 4.1 Geospatial Engine
The system uses **PostGIS** for all location-based logic:
- `ST_SetSRID(ST_MakePoint(lng, lat), 4326)` for storage.
- Spatial indexing for fast proximity searches (Deduplication).

### 4.2 Offline Persistence (Worker Flow)
Designed for workers in areas with poor connectivity:
- **IndexedDB**: Resolutions are saved locally if the browser is offline.
- **Service Workers**: Background sync mechanism attempts to push pending resolutions when a connection is restored.
- **Visual Feedback**: "Pending Sync" indicators on tasks.

### 4.3 Audit Logging
The `AuditService` automatically records every significant state change:
- `actor_id`: Who made the change.
- `action`: e.g., STATUS_CHANGE, ASSIGNMENT.
- `old_value` vs `new_value`: Full diff of the change.

### 4.4 Media Pipeline
- **MinIO**: Images are stored in an S3 bucket.
- **Signed URLs**: Frontend retrieves images via secure temporary links or proxy.
- **Resolution Proof**: Forced requirement for a photo when marking a task as resolved.

---

## 5. Development & Handoff Checklist

### Database Management
- `python reset_db.py`: Cleans all tables and re-seeds basic data.
- `python seed.py`: Creates default users (admin, workers, citizen).
- `python load_mock_data.py`: Loads 60+ realistic issues with history.

### Security Note
- Always ensure `SECRET_KEY` is changed in production.
- `DEV_MODE` should be set to `False` to enable real email sending (requires SMTP config).

---
**Version**: 1.0 (V0-handoff-1)
**Project**: MARG - Monitoring Application for Road Governance

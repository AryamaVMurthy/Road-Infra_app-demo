# Urban Infrastructure Reporting System - Final Handoff

## 1. System Overview
A high-integrity, production-ready platform for GHMC municipal operations. The system features four specialized dashboards (Citizen, Authority, Worker, Admin) and is built on a robust, spatially-aware backend.

## 2. Production Architecture
- **Backend**: FastAPI (Python 3.12) with modular service-layer architecture.
- **Frontend**: High-fidelity React PWA using **Shadcn UI**, **Tailwind CSS**, and **Framer Motion**.
- **Database**: **PostgreSQL 14 + PostGIS** for high-precision spatial operations.
- **Storage**: **Minio** (S3-compatible) for multi-source image evidence.
- **Resilience**: Integrated **IndexedDB** for offline submission logic.

## 3. High-Integrity Features
- **Silent 5m Aggregation**: Backend uses PostGIS `ST_DWithin` to automatically aggregate duplicate reports within 5 meters.
- **Top-Level Map Search**: Integrated Geocoder allows searching for addresses and landmarks directly on the reporting map.
- **Infrastructure Heatmaps**: Real-time visualization of city-wide issue density for System Admins.
- **EXIF Verification**: Real-time extraction of GPS and Timestamp from images using **Pillow** to prevent fraud.
- **Audit Engine**: Complete log of every state change, unassigned tasks, and administrative action in the `audit_logs` table.
- **Field-Force Mobility**: "Accept + ETA" workflow and high-contrast light UI optimized for outdoor field use.
- **Administrative Control**: Bulk issue assignment and side-by-side Before/After review modal.

## 4. Execution Manual

### Prerequisites
- Docker & Docker Compose
- Node.js 24+
- Python 3.12+

### Quick Start
1.  **Infrastructure**: `docker compose up -d`
2.  **Environment**: `python3 -m venv venv && source venv/bin/activate && pip install -r backend/requirements.txt`
3.  **Database**: `export PYTHONPATH=$PYTHONPATH:. && python3 backend/reset_db.py`
4.  **Frontend**: `cd frontend && npm install && cd ..`
5.  **Run**: `./start_servers.sh`

### Accessing Personas
Logins use **Email OTP**. Since this is a local build, codes are logged to the console.
- **Authority**: `admin@ghmc.gov.in` (Operations Map, Kanban, Bulk Assign)
- **Worker**: `worker@ghmc.gov.in` (Task Pool, ETA, Resolution)
- **Citizen**: `citizen@test.com` (Reporting, Offline Mode, My Reports)
- **System Admin**: `sysadmin@test.com` (Analytics, Governance, Audit)

## 5. Testing & Verification
The system is backed by a rigorous multi-persona test suite:
- **Backend**: `pytest backend/tests` (Geometric logic, Audit log integrity, SLA tracking).
- **Frontend**: `npm run test` (Service-worker state, Component renders).
- **E2E**: `npx playwright test tests/` (Complete citizen flow, Duplicate aggregation, Offline sync verification).

## 6. Last-Mile production (Optional)
- Replace dummy SMTP credentials in `app/core/config.py` with a real provider (AWS SES/SendGrid).
- Deploy with HTTPS for full PWA feature support.

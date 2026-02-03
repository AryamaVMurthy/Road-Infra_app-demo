# Production Service Integration Documentation

The system has moved from mocked services to production-grade integrations.

## 1. Database (PostgreSQL + PostGIS)
- **Integration**: Replaced SQLite with PostgreSQL 14.
- **Spatial Features**: Uses the **PostGIS** extension for high-precision geolocation.
- **Proximity Logic**: 5m duplicate detection is enforced using `ST_DWithin`.

## 2. Object Storage (Minio)
- **Integration**: Direct integration with Minio via the official SDK.
- **Buckets**: `infrastructure-evidence` bucket is automatically initialized on startup.
- **Pathing**: Evidence is stored using UUID-based paths for collision resistance.

## 3. Authentication (Email OTP)
- **Integration**: Full Email OTP lifecycle implemented.
- **Flow**: Request OTP -> Generate 6-digit code -> Store in DB with 10m expiry -> Verify during login.
- **Rate Limiting**: In-memory rate limiting prevents brute-forcing (3 attempts per 10m window).

## 4. Image Metadata (EXIF)
- **Integration**: Integrated **Pillow** for real EXIF parsing.
- **Verification**: Reports and Resolutions extract GPS and Timestamp from the binary blob for proximity validation.

## 5. Offline Capabilities (PWA)
- **Integration**: **IndexedDB** store-and-forward.
- **Behavior**: Reports submitted while offline are queued locally and automatically synced via the `useOfflineSync` hook once the browser detects an `online` event.

## 6. Audit Logging
- **Integration**: Centralized Audit service logs all critical state changes (status, assignment, priority) to the `audit_logs` table.

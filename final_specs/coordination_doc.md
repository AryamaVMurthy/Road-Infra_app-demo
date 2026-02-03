# Project Coordination Spec: Rules of the Road

**Objective:** Ensure all modules (Citizen, Authority, Worker, System Admin, Analytics) follow the same lifecycle, data rules, and validation standards.

---

## 1. The 5 Players

| Role | Description | Key Function/Needs |
| --- | --- | --- |
| **Citizen** | Reports issues. | Accurate location + verified photo. |
| **Govt Admin** | Manages a zone. | Assigns work, sets priority. |
| **Field Worker** | Fixes issues. | Needs verified evidence capture. |
| **System Admin** | Platform owner. | Onboards authorities, configures categories. |
| **Analytics Viewer** | Public/NGO. | Read-only transparency data. |

---

## 2. Issue Lifecycle (Single Source of Truth)

1. **REPORTED (Start)**
   - **Action:** Citizen submits location + photo.
   - **Rule:** System performs silent duplicate check within 5m.
     - If duplicate -> append evidence and increment report count.
     - If new -> create ticket.
2. **ASSIGNED**
   - **Action:** Govt Admin assigns a worker.
3. **IN_PROGRESS**
   - **Action:** Worker taps "Start Work".
4. **RESOLVED**
   - **Action:** Worker uploads verified "After" photo.
5. **CLOSED (End)**
   - **Action:** Admin closes after review.

---

## 3. Core Properties of Issues

### A. Identity & Location
- **Issue ID:** Unique identifier.
- **Category:** Type of issue.
- **Status:** REPORTED, ASSIGNED, IN_PROGRESS, RESOLVED, CLOSED, DISMISSED.
- **GPS Location:** Exact latitude/longitude.
- **Zone ID:** GHMC area (Hyderabad only for now).
- **Address:** Human-readable address.

### B. Evidence & Verification
- **Report Photo:** Required at creation.
- **Resolve Photo:** Required to resolve.
- **EXIF Rules:**
  - Timestamp must be within 7 days of submission.
  - EXIF location must be within 5m of device GPS / issue location.
  - Missing/invalid EXIF blocks submission.

### C. People & Ownership
- **Reporter ID:** Citizen who reported.
- **Assigned Worker ID:** Worker handling the issue.
- **Organization ID:** Govt authority responsible.

### D. Priority & Metrics
- **Report Count:** Aggregated reports for the same issue.
- **Admin Priority:** P1-Critical to P4-Low.
- **Estimated Completion:** Provided by worker on acceptance.
- **Days Open:** Time since REPORTED.
- **Citizen Feedback:** Like/Dislike counts for resolved/closed issues.

---

## 4. Authentication & Access

- Email OTP login and Google OAuth only (no SMS/phone OTP) for Citizen, Worker, Authority, and System Admin logins.
- Role-based access control applies across all dashboards.

---

## 5. Worker Onboarding (Invite-Only)

- Govt Admin adds worker emails from the Authority dashboard.
- Workers can only register with an invited email.
- First login auto-links the worker to the org and sets status ACTIVE.
- Invites can be revoked to block registration.
- Invite lifecycle: INVITED -> ACTIVE -> INACTIVE.
- Invites expire after a configured window (default 7 days) and can be re-sent.
- Optional allowed-domain restriction (e.g., *@ghmc.gov.in) can be enforced.

---

## 6. Jurisdiction & Zones

- Use GHMC boundaries for Hyderabad (current target).
- Zone creation/editing is System Admin only.
- No custom zone drawing in the initial release.

---

## 7. Duplicate Detection & Report Aggregation

- Duplicate check is silent (no display to citizen during reporting).
- Match radius: 5m.
- If duplicate found, append evidence and increment the report count.
- Future phase: add computer vision matching to reduce false positives.

---

## 8. Maps & Base Tiles

- OpenStreetMap is the default base layer.
- Mapbox can be configured optionally for enhanced tiles.

---

## 9. Worker Lifecycle Rules

- Workers can be DEACTIVATED but never hard-deleted.
- Deactivated workers lose access, but historical tasks remain linked.

---

## 10. Citizen Feedback Loop

- Citizens can like/dislike resolved/closed issues only.
- Feedback is visible in authority and analytics dashboards.
- No upvoting on report creation; report count is only from duplicate aggregation.

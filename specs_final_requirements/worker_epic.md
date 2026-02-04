# EPIC: Field Force Mobility & Task Execution Suite

## Executive Summary
A mobile workflow for field workers to accept tasks, verify location, execute repairs, and submit verified evidence of completion.

## Stakeholders & Value
### User Personas
- **Primary Persona:** Field Worker (on-the-ground staff).
- **Stakeholders:** Govt Admin, Citizens, System Admin.

### User Value
Workers get a clear task queue, directions, and a simple way to prove work completion with verified evidence.

## Goal & Vision
Enable a high-accountability, low-friction field execution process with strong location integrity.

## Scope
### In Scope
- Worker onboarding and org linking.
- Task queue with map view and location verification.
- Task acceptance with worker-provided time estimates.
- Status transitions and timestamps.
- Mandatory camera capture for resolution evidence with EXIF validation.
- Email OTP login and Google OAuth only (no SMS/phone OTP).
- OpenStreetMap base tiles for map/directions (Mapbox optional).

### Out of Scope
- Native navigation.
- Payroll/inventory.
- Live GPS tracking.

## Success Metrics
- Faster transitions from ASSIGNED to IN_PROGRESS.
- Lower fix rejection rates.

## Stories Under This Epic
1. [USER STORY 1: Invite-Only Onboarding & Org Linking](#user-story-1-invite-only-onboarding--org-linking)
2. [USER STORY 2: Task Queue, Acceptance & Location Verification](#user-story-2-task-queue-acceptance--location-verification)
3. [USER STORY 3: In-Field Execution (Status Lifecycle)](#user-story-3-in-field-execution-status-lifecycle)
4. [USER STORY 4: Resolution Evidence & Mandatory Validation](#user-story-4-resolution-evidence--mandatory-validation)
5. [USER STORY 5: Personal Performance & Work History](#user-story-5-personal-performance--work-history)

---

# USER STORY 1: Invite-Only Onboarding & Org Linking

## Executive Summary
Allow workers to register using a pre-invited email and auto-join their organization.

## User Persona & Problem Statement
**Who:** As a Field Worker...
**Why:** I need a verified way to access my department's tasks.

## Scope (In & Out)
### In Scope
- Email OTP login or Google OAuth (invite-only).
- Invite-only registration with pre-approved email list.
- Auto-link to organization on first login.

### Out of Scope
- Bulk import.

## Features & Acceptance Criteria
### Feature: Invite-Only Org Linking
**User Story:** As a Field Worker, I want to register using my invited email so I can access my department's tasks.

**Acceptance Criteria:**
- [ ] Verify worker can only register with an email that was invited by the authority.
- [ ] Verify first login auto-links the worker to the correct org and sets status ACTIVE.
- [ ] Verify workers using non-invited emails are blocked.
- [ ] Verify login uses Email OTP or Google OAuth only.

## Functional Requirements
- Store `org_id` on worker profile at first login.
- Return HTTP 403 for workers without an invited/active status.
- Invite lifecycle: INVITED -> ACTIVE -> INACTIVE.
- Invites expire after a configured window (default 7 days) and can be re-sent.
- Optional allowed-domain restriction can be enforced (e.g., *@ghmc.gov.in).

## Edge Cases
- If an invite is expired or revoked, registration is blocked.

---

# USER STORY 2: Task Queue, Acceptance & Location Verification

## Executive Summary
Provide a centralized task list with map context, plus a required acceptance step that captures worker ETA.

## User Persona & Problem Statement
**Who:** As a Field Worker...
**Why:** I need clear location context and a way to estimate completion time when accepting tasks.

## Scope (In & Out)
### In Scope
- List view and map view.
- Before photo visibility.
- Accept task with time estimate.
- Location verification within 5m.

### Out of Scope
- Task re-assignment.

## Features & Acceptance Criteria
### Feature: Location Verification
**User Story:** As a Field Worker, I want to verify location accuracy before starting work.

**Acceptance Criteria:**
- [ ] Verify "Get Directions" opens external map apps.
- [ ] Verify the original "Before" photo is visible.
- [ ] Verify the app shows distance to issue and warns when beyond 5m.

### Feature: Task Acceptance with ETA
**User Story:** As a Field Worker, I want to provide an estimated completion time when I accept a task.

**Acceptance Criteria:**
- [ ] Verify an "Accept" action is required before starting work.
- [ ] Verify acceptance requires an estimated duration (minutes/hours).
- [ ] Verify ETA is saved to the issue and visible to Govt Admins.
- [ ] Verify acceptance sets `accepted_at` on the issue.

## UI/UX Design & User Flow
**Flow:** My Tasks -> Open Task -> Accept + ETA -> Navigate -> Start Work.

## Functional Requirements
- `POST /issues/{id}/accept` with payload `{ worker_id, estimated_minutes }`.
- Store `accepted_at` server timestamp.
- Expose ETA and elapsed time to authority dashboard.

## Edge Cases
- ETA changes require re-confirmation by worker.

---

# USER STORY 3: In-Field Execution (Status Lifecycle)

## Executive Summary
Allow workers to mark tasks as IN_PROGRESS once they begin work.

## User Persona & Problem Statement
**Who:** As a Field Worker...
**Why:** I need to show I am actively working on a task.

## Scope (In & Out)
### In Scope
- Manual "Start Work" action.
- Status transition to IN_PROGRESS.

### Out of Scope
- Manual time entry.

## Features & Acceptance Criteria
### Feature: Status Transition
**Acceptance Criteria:**
- [ ] Verify tapping "Start Work" changes status to IN_PROGRESS.
- [ ] Verify the button is disabled after starting work.
- [ ] Verify a "Working" badge is shown.

## Workflow & Entity State Lifecycle
**Lifecycle:** ASSIGNED -> IN_PROGRESS.

## Functional Requirements
- Record server-side timestamp on status change.
- Lock task to current worker during IN_PROGRESS.

## Edge Cases
- Accidental tap cannot be undone without admin intervention.

---

# USER STORY 4: Resolution Evidence & Mandatory Validation

## Executive Summary
Enforce verified evidence submission with EXIF validation and location proximity checks.

## User Persona & Problem Statement
**Who:** As a Field Worker...
**Why:** I need to prove I finished the job with valid evidence.

## Scope (In & Out)
### In Scope
- Mandatory camera capture (no gallery).
- EXIF validation for time and location.
- GPS coordinate capture on submit.

### Out of Scope
- Video evidence.
- Multi-photo uploads.

## Features & Acceptance Criteria
### Feature: Evidence Submission
**User Story:** As a Field Worker, I want to upload an "After" photo to resolve the ticket.

**Acceptance Criteria:**
- [ ] Verify Resolve is disabled until a photo is captured.
- [ ] Verify EXIF timestamp is within 7 days of submission.
- [ ] Verify EXIF location is within 5m of issue location.
- [ ] Verify submission is blocked if EXIF data is missing or invalid.
- [ ] Verify GPS coordinates are captured on submission.

## UI/UX Design & User Flow
**Flow:** Active Task -> Capture Photo -> Add Notes -> Submit Resolution -> Success.

## Workflow & Entity State Lifecycle
**Lifecycle:** IN_PROGRESS -> RESOLVED.

## Functional Requirements
- Update status to RESOLVED.
- Submit `exif_timestamp`, `exif_lat`, `exif_long`, and `device_location`.

## Non-Functional Requirements (Minimal)
- Optimize image upload size.

## Edge Cases
- Upload failure keeps status as IN_PROGRESS with retry.

---

# USER STORY 5: Personal Performance & Work History

## Executive Summary
Provide workers with a history of completed work and performance totals.

## User Persona & Problem Statement
**Who:** As a Field Worker...
**Why:** I need a record of my completed tasks for reviews.

## Scope (In & Out)
### In Scope
- Historical list of RESOLVED/CLOSED tasks.
- Date-based filtering.
- Total resolved count.

### Out of Scope
- Public leaderboards.

## Features & Acceptance Criteria
### Feature: Work History
**User Story:** As a Field Worker, I want to view my completed tasks.

**Acceptance Criteria:**
- [ ] Verify a History tab shows RESOLVED and CLOSED tasks only.
- [ ] Verify total resolved count is displayed on profile.

## UI/UX Design & User Flow
**Flow:** Profile -> My History -> Filter by Date -> View Details.

## Success Metrics
- Increased daily access to the task history view.

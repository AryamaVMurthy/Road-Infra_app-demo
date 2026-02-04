# EPIC: Authority Operations Dashboard & Zone Management

**Source of Truth:** This file is authoritative. `EPIC_Authority_Operations_Dashboard.md` is a generated copy and should not be edited directly.

## Executive Summary
A web operations console for Government Admins to manage the full lifecycle of issues within their jurisdiction, from map-based triage to worker assignment and resolution review.

## Stakeholders & Value
### User Personas
- **Primary Persona:** Govt Admin (manages a jurisdiction, assigns work, reviews fixes).
- **Stakeholders:** Field Workers, Citizens, System Admin.

### User Value
Admins can see what is happening in their zone, prioritize by impact, assign efficiently, and enforce quality control.

## Goal & Vision
Provide a clear, accountable command center that reduces time-to-fix while keeping jurisdiction boundaries explicit and immutable.

## Scope
### In Scope
- Geospatial operations map with jurisdiction overlay.
- Zone-of-interest filter using GHMC areas (Hyderabad only for now).
- Kanban workflow with bulk assignment and priority setting.
- Active load view (worker task counts).
- Worker onboarding, approval, and deactivation (no deletion).
- Resolution review with audit logging.
- Public audit log integrations.
- Invitation-based authority registration (via System Admin onboarding).
- Authority profile management.
- Email OTP login and Google OAuth only (no SMS/phone OTP).
- OpenStreetMap base tiles (Mapbox optional).
- Time estimates captured from workers and displayed to authorities.

### Out of Scope
- Category management (System Admin only).
- Zone creation or editing (System Admin only).
- AI-based priority scoring.
- Push notifications.

## Success Metrics
- Reduced time from REPORTED to ASSIGNED using bulk assignment.
- Fast review turnaround for RESOLVED tickets.
- Visible reasons for dismissed tickets.

## Stories Under This Epic
1. [USER STORY 1: Geospatial Operations Map](#user-story-1-geospatial-operations-map)
2. [USER STORY 2: Kanban Dashboard & Bulk Assignment](#user-story-2-kanban-dashboard--bulk-assignment)
3. [USER STORY 3: Worker Onboarding & Team Management](#user-story-3-worker-onboarding--team-management)
4. [USER STORY 4: Resolution Review & Quality Control](#user-story-4-resolution-review--quality-control)
5. [USER STORY 5: Authority Settings & Profile Management](#user-story-5-authority-settings--profile-management)

---

# USER STORY 1: Geospatial Operations Map

## Executive Summary
Render the Admin's jurisdiction as a read-only boundary, overlay active issues as pins, and allow focused viewing by GHMC sub-areas.

## User Persona & Problem Statement
**Who:** As a Govt Admin...
**Why:** I need to see where issues are relative to my official boundary and focus on specific sub-areas quickly.

## Scope (In & Out)
### In Scope
- Zone boundary overlay (read-only).
- GHMC zone-of-interest filter (dropdown).
- Color-coded pins with report_count and priority.
- Quick-view actions from map pins.

### Out of Scope
- Drawing/editing zones.
- Heatmap density analysis (handled in analytics dashboard).
- Real-time worker tracking.

## Features & Acceptance Criteria
### Feature: Zone Context Overlay
**User Story:** As a Govt Admin, I want to see my zone clearly marked on the map so I know my operational limits.

**Acceptance Criteria:**
- [ ] Verify the map auto-zooms to the assigned zone boundary at login.
- [ ] Verify the zone is rendered as a read-only polygon (no edits).
- [ ] Verify the zone name is displayed in the header.
- [ ] Verify the zone boundary source is GHMC KML/GeoJSON for Hyderabad (no custom zones in Phase 1).

### Feature: Zone-of-Interest Filter (GHMC)
**User Story:** As a Govt Admin, I want to filter the map to a GHMC area so I can focus on hotspots.

**Acceptance Criteria:**
- [ ] Verify a dropdown lists GHMC areas within the assigned jurisdiction.
- [ ] Verify selecting an area zooms the map to that boundary and filters pins to that area.
- [ ] Verify clearing the selection resets the view to the full zone.

### Feature: Operational Issue Visualization
**User Story:** As a Govt Admin, I want to see all active issues as pins so I can identify clusters.

**Acceptance Criteria:**
- [ ] Verify pins show all active tickets for this zone.
- [ ] Verify pin colors reflect status (REPORTED, ASSIGNED/IN_PROGRESS, RESOLVED).
- [ ] Verify pins are not clustered and represent unique issue IDs.
- [ ] Verify each pin includes report_count and priority in its quick-view.
- [ ] Verify filters by category/status update the map pins.

### Feature: Map-to-Action
**User Story:** As a Govt Admin, I want to click a pin to see details and take action.

**Acceptance Criteria:**
- [ ] Verify clicking a pin opens a quick-view with photo, status, report_count, priority, and assigned worker.
- [ ] Verify quick-view shows worker ETA and time since issue creation when available.
- [ ] Verify quick-view links to the full issue detail modal.
- [ ] Verify quick-view includes an \"Open Ticket\" action.

## UI/UX Design & User Flow
**Flow:** Login -> Map loads -> Zone overlay -> Optional GHMC area filter -> Select pin -> Quick view -> Open issue.

## Functional Requirements
**Zone Data:**
- `GET /zones/{assigned_zone_id}` returns GeoJSON derived from GHMC KML.
- Zone polygons are read-only in the UI.

**Issue Data:**
- `GET /issues?zone_id={id}&status=active` returns active issues for pins.
- Pin payload includes: `issue_id`, `lat`, `long`, `status`, `category_icon`, `report_count`, `priority`, `created_at`, `assigned_worker`, `estimated_minutes`.

**Map Provider:**
- Use OpenStreetMap tiles by default; Mapbox optional.

**Viewport Logic:**
- Fit map to zone bounding box on load.

**Deduplication Assumption:**
- Backend aggregates duplicates within 5m and increments `report_count`.

**Filtering:**
- Map responds to global category/status filters from the dashboard.

## RBAC & Permissions
| Role | Can View Map | Can See Zone | Can Edit Zone |
| --- | --- | --- | --- |
| Govt Admin | Yes | Yes | No |
| System Admin | Yes | Yes | Yes |

## Dependencies
- System Admin zone data must exist before map loads.

## Non-Functional Requirements (Minimal)
- Map interaction should remain responsive at expected pin volumes.

## Edge Cases
- Zone missing returns a "No Zone Configured" message.
- Issues outside the polygon are shown with a warning icon.

---

# USER STORY 2: Kanban Dashboard & Bulk Assignment

## Executive Summary
A Kanban board for high-volume triage with bulk assignment, priority management, and visibility into worker estimates.

## User Persona & Problem Statement
**Who:** As a Govt Admin...
**Why:** I need to assign many issues quickly and prioritize the most reported ones.

## Scope (In & Out)
### In Scope
- Kanban board with drag-and-drop.
- Bulk select and assignment.
- Priority setting per issue.
- Sorting by report_count, priority, and created_at.
- Worker ETA visibility.

### Out of Scope
- AI-based sorting.
- Push notifications.

## Features & Acceptance Criteria
### Feature: Kanban Board
**User Story:** As a Govt Admin, I want a column view of issue status.

**Acceptance Criteria:**
- [ ] Verify cards display issue_id, category, photo thumbnail, report_count, priority, and days open.
- [ ] Verify columns support sorting by report_count (default), priority, or created_at.
- [ ] Verify drag-and-drop from REPORTED to ASSIGNED triggers assignment modal.

### Feature: Smart Assignment (Single & Bulk)
**User Story:** As a Govt Admin, I want to assign multiple issues to a worker efficiently.

**Acceptance Criteria:**
- [ ] Verify bulk selection of multiple REPORTED cards.
- [ ] Verify assignment modal lists workers with active task counts.
- [ ] Verify assignment updates cards to ASSIGNED and stores assigned worker.
- [ ] Verify re-assignment is possible even when a task is IN_PROGRESS.

### Feature: Priority Management
**User Story:** As a Govt Admin, I want to set priority per issue so crews focus on critical work.

**Acceptance Criteria:**
- [ ] Verify each card has a priority selector (P1-Critical to P4-Low).
- [ ] Verify priority changes are saved immediately and visible on map and Kanban.
- [ ] Verify priority sorting is available in the Kanban header.

### Feature: Time Estimate Visibility
**User Story:** As a Govt Admin, I want to see worker-provided estimates so I can track timelines.

**Acceptance Criteria:**
- [ ] Verify cards show estimated completion time when provided by worker.
- [ ] Verify the UI shows time since issue creation and time remaining vs estimate.

## UI/UX Design & User Flow
**Flow:** Load board -> Select cards -> Assign -> Monitor priority and ETA fields.

## Workflow & Entity State Lifecycle
**Lifecycle:** REPORTED -> ASSIGNED -> IN_PROGRESS -> RESOLVED -> CLOSED.

## Functional Requirements
**Data Fetching:**
- `GET /issues?zone_id={id}&status=active` for board data.

**Card Fields:**
- `issue_id`, `category_icon`, `created_at`, `report_count`, `priority`, `thumbnail_url`.
- `accepted_at`, `estimated_minutes`, `assigned_worker` (if available).

**Sorting Logic:**
- Default sort by `report_count` desc.
- Toggle to `priority` or `created_at` as needed.

**Priority Updates:**
- `PATCH /issues/{id}/priority` with payload `{ priority: P1|P2|P3|P4 }`.

**Bulk Assignment:**
- `POST /assignments/bulk` accepts issue_ids[] and worker_id, transactional.

**Worker Load Tracking:**
- Assignment modal displays active task counts per worker.

**Validation:**
- Prevent assignment for RESOLVED/CLOSED issues.

**Audit Logging:**
- Log assignment and priority changes with actor, timestamp.
- Track previous_worker and new_worker for re-assignments.

## RBAC & Permissions
| Role | Can Assign | Can Re-Assign | Can View Board |
| --- | --- | --- | --- |
| Govt Admin | Yes | Yes | Yes (own zone only) |
| Field Worker | No | No | No |

## Dependencies
- Worker list from Story 3.

## Non-Functional Requirements (Minimal)
- Kanban interactions remain responsive for expected ticket volumes.

## Edge Cases
- Deactivated workers are hidden from assignment list.
- Concurrent updates may cause conflicts and require refresh.

---

# USER STORY 3: Worker Onboarding & Team Management

## Executive Summary
Invite, manage, and deactivate workers while preserving historical work records.

## User Persona & Problem Statement
**Who:** As a Govt Admin...
**Why:** I must control who can access tasks and ensure workers who quit are disabled without losing history.

## Scope (In & Out)
### In Scope
- Invite workers by email.
- Auto-activation when invited email registers.
- Active staff list.
- Deactivate worker access (no deletion).

### Out of Scope
- Bulk user import.
- Push notifications.

## Features & Acceptance Criteria
### Feature: Invite-Only Worker Onboarding
**User Story:** As a Govt Admin, I want to add worker emails so only approved staff can join my org.

**Acceptance Criteria:**
- [ ] Verify Admin can add worker emails from the dashboard.
- [ ] Verify the system sends an invite email with registration link.
- [ ] Verify workers can only register with an invited email.
- [ ] Verify first login auto-links the worker to the org and sets status ACTIVE.
- [ ] Verify invite revocation blocks registration.

### Feature: Worker Deactivation (No Deletion)
**User Story:** As a Govt Admin, I want to disable workers who leave without deleting their ID.

**Acceptance Criteria:**
- [ ] Verify each active worker has a "Deactivate" action.
- [ ] Verify deactivation revokes login access immediately.
- [ ] Verify the worker record is retained (no hard delete).
- [ ] Verify historical tasks remain linked to the worker_id.
- [ ] Verify tasks assigned to a deactivated worker are unassigned and reset to REPORTED.

## Functional Requirements
- `GET /workers?org_id={id}&status=ACTIVE` for active list.
- `POST /workers/invite` adds invited emails for the org.
- `DELETE /workers/invite/{id}` revokes an invite.
- On first login, invited email auto-links org_id and sets status ACTIVE.
- `PATCH /workers/{id}/deactivate` sets status INACTIVE and `deactivated_at`.
- Hard deletes are disallowed for workers.
- A worker cannot be in INVITED state for multiple organizations simultaneously.
 - Invite lifecycle: INVITED -> ACTIVE -> INACTIVE.
 - Invites expire after a configured window (default 7 days) and can be re-sent.
 - Optional allowed-domain restriction can be enforced per authority (e.g., *@authority.gov.in).

## Workflow & Entity State Lifecycle
**Lifecycle:** INVITED -> ACTIVE -> INACTIVE.

## Success Metrics
- High verification rate for active workers.

## Edge Cases
- Deactivation during an active upload results in an "Unauthorized" error.

---

# USER STORY 4: Resolution Review & Quality Control

## Executive Summary
Require before/after photo review before closure and enforce transparent rejection reasons.

## User Persona & Problem Statement
**Who:** As a Govt Admin...
**Why:** I need to verify fix quality and document reasons for rejection.

## Scope (In & Out)
### In Scope
- Side-by-side photo comparison.
- Reject fix with reason.
- Close ticket.
- Dismiss issue with reason.

### Out of Scope
- Automated image quality detection.

## Features & Acceptance Criteria
### Feature: Resolution Review
**User Story:** As a Govt Admin, I want to compare before/after photos before closing.

**Acceptance Criteria:**
- [ ] Verify before and after photos are shown side-by-side.
- [ ] Verify reject requires a reason and returns status to IN_PROGRESS.
- [ ] Verify close sets status to CLOSED and finalizes analytics.

### Feature: Dismissal Transparency
**User Story:** As a Govt Admin, I want to dismiss spam with a reason visible to citizens.

**Acceptance Criteria:**
- [ ] Verify dismissal requires a reason code or custom note.
- [ ] Verify dismissed tickets are removed from active board but preserved in DB.
- [ ] Verify rejection reason is exposed to the citizen app.

### Feature: Citizen Feedback Visibility
**User Story:** As a Govt Admin, I want to see citizen like/dislike counts for closed issues.

**Acceptance Criteria:**
- [ ] Verify the issue detail view displays aggregated like/dislike counts.

## Functional Requirements
- `POST /issues/{id}/reject_fix` requires reason.
- `POST /issues/{id}/dismiss` requires reason_code.
- `public_status_message` stores citizen-visible rejection reason.
- Closing a ticket triggers analytics update jobs.
- Dismissal reason_code enum includes: DUPLICATE, SPAM, OUT_OF_ZONE.
- Audit logs capture ISSUE_CLOSED and FIX_REJECTED with timestamps and reasons.

## Dependencies
- Citizen app must display rejection reasons and collect feedback votes.

## Non-Functional Requirements (Minimal)
- Once CLOSED, photos are immutable.

## Edge Cases
- Corrupted "After" photo requires rejection with reason.

---

# USER STORY 5: Authority Settings & Profile Management

## Executive Summary
Allow admins to manage profile details with email/Google login only.

## User Persona & Problem Statement
**Who:** As a Govt Admin...
**Why:** I need to keep my contact details updated without breaking login access.

## Scope (In & Out)
### In Scope
- Edit name and phone (contact only).
- Email OTP login or Google OAuth for authentication.

### Out of Scope
- Zone editing.
- Category management.

## Features & Acceptance Criteria
### Feature: Profile Management
**User Story:** As a Govt Admin, I want to update profile details safely.

**Acceptance Criteria:**
- [ ] Verify email (login ID) is read-only.
- [ ] Verify restricted fields (zone_id, role) cannot be updated.
- [ ] Verify profile edits require a recent authenticated session.

## Functional Requirements
- `PATCH /admin/me` updates profile fields.
- Profile changes require a recent authenticated session (email OTP or Google OAuth).

## Edge Cases
- Stale sessions require re-authentication before profile updates.

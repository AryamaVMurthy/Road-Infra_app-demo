# 10-Slide Presentation Template (Final Specs Only)

## Slide 1 — System Overview & Vision
- Purpose: end‑to‑end civic infrastructure reporting, resolution, and transparency
- Modules: Citizen Reporting, Authority Operations, Field Worker Execution, System Admin Governance, Public Analytics
- Stakeholders: Citizens, Govt Admins, Field Workers, System Admins, NGOs/Public Viewers
- Core outcomes: location accuracy, verified evidence, silent duplicate control, accountability, measurable performance
- Maps: OpenStreetMap base tiles by default; Mapbox optional
- Jurisdiction: GHMC areas for Hyderabad; no custom zone drawing in initial release
- Success focus: high upload success in low bandwidth, reduced duplicate creation, faster assignment and resolution, transparent auditability

## Slide 2 — Cross‑Module Standards
- Single lifecycle enforced: REPORTED → ASSIGNED → IN_PROGRESS → RESOLVED → CLOSED
- End‑to‑end issue flow: report (silent 5m duplicate check) → assign worker → worker accepts ETA → start work → resolve with verified after photo → admin review/close → analytics update → citizen feedback (resolved/closed only)
- Duplicate logic: silent 5m check; if match, append evidence and increment report count
- No upvoting on report creation; report count only from duplicate aggregation
- Evidence rules: photo required at report and resolution; EXIF time within 7 days; EXIF location within 5m
- Core issue data: unique issue ID, category, status, GPS location, zone, address
- Operational metrics: report count, priority (P1–P4), days open, worker ETA, time since creation
- Authentication: Email OTP or Google OAuth only (no SMS/phone OTP)
- Worker lifecycle: invite‑only onboarding; INVITED → ACTIVE → INACTIVE; expiry (default 7 days), resend, optional domain restriction
- Maps & zones: GHMC boundaries, read‑only zones for authorities
- Feedback loop: like/dislike only for RESOLVED/CLOSED issues; visible to authorities and analytics

## Slide 3 — Citizen App: Location Confirmation & Silent Duplicate
- Flow: Home → Report Issue → Confirm Location → Capture/Select Photo → Submit
- 5m location lock with accuracy indicator; retry if accuracy worse than 5m
- “Confirm Location” step with address confirmation (Swiggy‑like)
- Reporting UI hides existing issues and report counts to keep flow simple
- System performs silent nearby match within 5m before creating a new issue
- If duplicate found: append evidence and increment report count; user sees normal success
- If no match: create a new issue with current GPS as source of truth
- Permissions: block reporting if location permission is denied
- Edge handling: GPS drift beyond 5m blocks submission until accuracy improves

## Slide 4 — Citizen App: Report Creation, Offline Sync, Feedback
- Evidence: photo capture or gallery selection with EXIF validation (time ≤ 7 days, location within 5m)
- Category: dynamic list, required selection; optional description
- Submission includes: location + accuracy, category, description, photo, EXIF metadata for validation
- Assignment: backend assigns the issue to the correct authority based on location
- Offline store‑and‑forward: queue reports when connectivity fails and retry on reconnect
- Local storage cap: warn user before accepting new offline reports
- “My Reports” dashboard: status timeline, before/after photos, dismissal reasons
- Feedback: like/dislike only for RESOLVED/CLOSED issues; one vote per user per issue
- Out of scope: video reporting, remote pin placement, SMS/Email notifications

## Slide 5 — Authority Ops: Geospatial Map & Zone Focus
- Read‑only GHMC boundary overlay with auto‑zoom to assigned zone
- Zone‑of‑interest dropdown for GHMC sub‑areas; clear resets to full zone
- Pins show status, report count, priority, category icon, and key details
- Quick view includes: photo, status, report count, priority, assigned worker, ETA, time since creation
- “Open Ticket” action from quick view to full issue detail
- Filters by category and status update visible pins
- No clustering: each pin represents a unique issue
- Edge cases: “No Zone Configured” message; out‑of‑bounds issues flagged

## Slide 6 — Authority Ops: Kanban, Priority, Time Tracking
- Kanban columns: REPORTED, ASSIGNED, IN_PROGRESS, RESOLVED, CLOSED
- Cards show: issue ID, category, thumbnail, report count, priority, days open
- Sorting: default by report count; optional by priority or creation time
- Bulk assignment: select multiple issues; assign to one worker as a single transaction
- Worker load visibility: show active task counts in assignment modal
- Priority control: P1–P4; changes visible on map and Kanban
- Time tracking: worker ETA, elapsed time, time remaining vs estimate
- Validation: prevent assignment for RESOLVED/CLOSED issues
- Audit logging for assignment and priority changes

## Slide 7 — Authority Ops: Workforce, Review, Profile
- Invite‑only onboarding: Admin invites emails; only invited emails can register
- First login auto‑links worker to organization and sets ACTIVE
- Invite lifecycle: INVITED → ACTIVE → INACTIVE; expiry, resend, optional domain restriction
- Deactivation: revoke access immediately; history retained; tasks reset to REPORTED
- Resolution review: compare before/after photos; reject fix with reason; close ticket to finalize analytics
- Dismissal: reason codes (DUPLICATE, SPAM, OUT_OF_ZONE) with optional note; dismissed removed from active board
- Citizen transparency: rejection reasons visible to citizen app
- Profile management: edit name/phone only; email read‑only; re‑auth required for changes

## Slide 8 — Worker App: Task Execution & Evidence
- Task queue with list/map view, before photo, and location context
- Location verification within 5m; warnings when outside range
- Accept task requires ETA before starting work
- Start Work sets IN_PROGRESS and locks the task to the worker
- Resolution requires camera capture only (no gallery)
- EXIF checks: time within 7 days; location within 5m of issue
- GPS location captured on submission; retry on upload failures
- Personal history: resolved/closed tasks list with totals and date filters
- Out of scope: native navigation, payroll/inventory, live GPS tracking

## Slide 9 — Public Analytics & Transparency
- Read‑only portal with lifecycle funnel and before/after gallery
- Filters by issue type, GHMC area, and time range
- Hotspots and redzones for unresolved clusters
- Average Resolution Time metrics; dismissed issues excluded
- Data export in CSV/JSON for external analysis
- Kepler.gl map layers; OpenStreetMap base tiles
- Privacy: public view is read‑only and excludes restricted data

## Slide 10 — System Admin Governance
- Authority onboarding with GHMC boundary selection and assigned zone storage
- Role management and RBAC for Govt Admin, Field Worker, NGO Viewer
- Category configuration: add/edit/deactivate; set priority defaults and expected resolution time
- Workflow state configuration: enforce valid states and admin approval option
- System monitoring: total reports, active users, storage, duplicate detection performance, flagged patterns
- Manual issue creation for internal inspections
- Audit logs for onboarding, role changes, category updates (immutable and viewable)
- Out of scope: direct citizen data manipulation, billing/financials

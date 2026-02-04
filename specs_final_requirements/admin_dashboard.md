# EPIC: Platform Administration & Governance

## Executive Summary
A centralized control layer for onboarding authorities, configuring system-wide metadata, and monitoring platform health.

## Stakeholders & Value
### User Personas
- **Primary Persona:** System Admin (platform owner).
- **Stakeholders:** Government Authorities, Field Workers.

### User Value
Ensures the platform stays secure, configurable, and scalable without code changes.

## Goal & Vision
Provide reliable governance and configuration of the platform's core entities and jurisdictions.

## Scope
### In Scope
- Authority onboarding and jurisdiction assignment.
- Role management and RBAC.
- Issue and category configuration (priority defaults, SLA).
- System monitoring and audit logs.
- Manual issue creation.
- Email OTP login and Google OAuth only (no SMS/phone OTP).
- GHMC jurisdiction selection (Hyderabad only for now).

### Out of Scope
- Direct manipulation of citizen user data.
- Billing/financials.
- Custom zone drawing or editing (Phase 1).

## Success Metrics
- Reduced time to onboard new authorities.
- Consistent audit trail coverage.

## Stories Under This Epic
1. [USER STORY 1: Authority & Role Management](#user-story-1-authority--role-management)
2. [USER STORY 2: Issue & Category Configuration](#user-story-2-issue--category-configuration)
3. [USER STORY 3: System Monitoring & Control](#user-story-3-system-monitoring--control)

---

# USER STORY 1: Authority & Role Management

## Executive Summary
Enable secure onboarding of authorities with predefined jurisdiction boundaries.

## User Persona & Problem Statement
**Who:** As a System Admin...
**Why:** I need to add new authorities and assign their GHMC jurisdiction without manual scripts.

## Scope (In & Out)
### In Scope
- Authority creation.
- Jurisdiction assignment from GHMC list.
- Role-based access control.

### Out of Scope
- External SSO integration.

## Features & Acceptance Criteria
### Feature: Authority Onboarding
**User Story:** As a System Admin, I want to onboard new authorities so they can start using the platform.

**Acceptance Criteria:**
- [ ] Verify Admin can add government departments/municipal bodies.
- [ ] Verify Admin can assign jurisdiction from a GHMC dropdown (Hyderabad only).
- [ ] Verify custom polygon drawing is not available in Phase 1.
- [ ] Verify the selected GHMC area is stored as the authority's zone_id.
- [ ] Verify authority accounts are created via invite and log in using Email OTP or Google OAuth only.

### Feature: Role Management
**User Story:** As a System Admin, I want to manage roles so access is restricted correctly.

**Acceptance Criteria:**
- [ ] Verify Admin can create/manage roles: Government Admin, Field Worker, NGO Viewer.
- [ ] Verify strict RBAC enforcement across the platform.

## Functional Requirements
- GHMC KML/GeoJSON must be loaded into the zone catalog.
- Authority records must reference zone_id from GHMC boundaries.

## Dependencies
- GHMC KML file and boundary list required before onboarding.

---

# USER STORY 2: Issue & Category Configuration

## Executive Summary
Manage issue categories and workflow metadata without code changes.

## User Persona & Problem Statement
**Who:** As a System Admin...
**Why:** I need to add categories and configure defaults without developer support.

## Scope (In & Out)
### In Scope
- Category CRUD.
- Priority defaults and expected resolution time.
- Workflow state configuration.

## Features & Acceptance Criteria
### Feature: Issue Type Management
**User Story:** As a System Admin, I want to configure categories so the citizen app stays relevant.

**Acceptance Criteria:**
- [ ] Verify Admin can add, edit, or deactivate categories.
- [ ] Verify deactivated categories are hidden from the citizen app.
- [ ] Verify Admin can configure metadata (priority default, expected resolution time).

### Feature: Workflow Configuration
**User Story:** As a System Admin, I want to define valid ticket states.

**Acceptance Criteria:**
- [ ] Verify Admin can define ticket states (REPORTED, ASSIGNED, IN_PROGRESS, RESOLVED, CLOSED).
- [ ] Verify Admin can toggle "Admin Approval Required" for resolution.

---

# USER STORY 3: System Monitoring & Control

## Executive Summary
Provide visibility into platform health and data integrity.

## User Persona & Problem Statement
**Who:** As a System Admin...
**Why:** I need to see if the system is healthy and audits are complete.

## Scope (In & Out)
### In Scope
- Health stats.
- Duplicate detection monitoring.
- Manual issue creation.
- Audit logs.

## Features & Acceptance Criteria
### Feature: Platform Health Overview
**User Story:** As a System Admin, I want to see high-level stats so I can monitor usage.

**Acceptance Criteria:**
- [ ] Verify dashboard shows total reports, active users, storage usage.
- [ ] Verify duplicate detection performance indicators are visible.
- [ ] Verify flagged reporting patterns are visible.

### Feature: Manual Issue Creation
**User Story:** As a System Admin, I want to create issues manually.

**Acceptance Criteria:**
- [ ] Verify Admin can create issues on behalf of authorities.
- [ ] Verify these issues enter the standard workflow.

### Feature: Audit Trail
**User Story:** As a System Admin, I want a log of changes.

**Acceptance Criteria:**
- [ ] Verify role updates, category changes, and onboarding events are logged.
- [ ] Verify logs are immutable and viewable.

## Functional Requirements
- Central config store for permissions/workflows.
- Admin-only access to storage metadata.

# EPIC: Aggregated Public Analytics & Transparency

## Executive Summary
A read-only analytics portal that visualizes issue lifecycle data, hotspot density, and resolution performance for public accountability.

## Stakeholders & Value
### User Personas
- **Primary Persona:** NGO / Public Viewer.
- **Stakeholders:** Government Officials.

### User Value
Enables transparent, city-wide visibility into infrastructure performance and unresolved hotspots.

## Goal & Vision
Turn government operations into transparent, data-backed public insights.

## Scope
### In Scope
- Lifecycle funnel visualization.
- Before/After photo gallery.
- Filtering by location, time, and issue type.
- Heatmaps, hotspots, and redzone overlays.
- Data export (CSV/JSON).
- Zone-of-interest selection (GHMC areas, Hyderabad only for now).
- Kepler.gl-based map layers.
- OpenStreetMap base tiles (Mapbox optional).

### Out of Scope
- Real-time worker tracking.
- Write access to issues.

## Success Metrics
- High traffic on transparency portal.
- Increased downloads of open data exports.

## Stories Under This Epic
1. [USER STORY 1: End-to-End Lifecycle Visualization](#user-story-1-end-to-end-lifecycle-visualization)
2. [USER STORY 2: Advanced Filtering & Scoping](#user-story-2-advanced-filtering--scoping)
3. [USER STORY 3: NGO & Advocacy Features](#user-story-3-ngo--advocacy-features)

---

# USER STORY 1: End-to-End Lifecycle Visualization

## Executive Summary
Show the journey of issues from REPORTED to CLOSED with verifiable photos and counts.

## User Persona & Problem Statement
**Who:** As a Citizen/NGO...
**Why:** I want evidence and numbers, not just summaries.

## Scope (In & Out)
### In Scope
- Pipeline funnel.
- Before/After side-by-side.
- Report_count visibility (aggregated).

## Features & Acceptance Criteria
### Feature: Issue Pipeline
**User Story:** As a Viewer, I want to see the volume of issues at each stage.

**Acceptance Criteria:**
- [ ] Verify funnel shows REPORTED -> IN_PROGRESS -> RESOLVED -> CLOSED.
- [ ] Verify counts are accurate and near real-time.

### Feature: Before/After Transparency
**User Story:** As a Viewer, I want to compare before and after photos.

**Acceptance Criteria:**
- [ ] Verify public access to before/after photos for closed tickets.
- [ ] Verify photos are displayed side-by-side.
- [ ] Verify sensitive data is redacted if required.

## UI/UX Design & User Flow
**Flow:** Landing -> Funnel -> Select Resolved -> Gallery -> Compare.

---

# USER STORY 2: Advanced Filtering & Scoping

## Executive Summary
Provide multi-dimensional filtering for detailed analysis of problem areas.

## User Persona & Problem Statement
**Who:** As a Researcher...
**Why:** I need to compare performance across wards and time windows.

## Scope (In & Out)
### In Scope
- Type filter.
- Geo filter by GHMC areas.
- Time filter.

## Features & Acceptance Criteria
### Feature: Multi-Dimensional Filtering
**User Story:** As a Viewer, I want to filter by type, location, and time.

**Acceptance Criteria:**
- [ ] Verify filter by issue type (potholes, drainage).
- [ ] Verify drill-down by GHMC area via dropdown.
- [ ] Verify temporal filters (custom ranges, seasons).

## UI/UX Design & User Flow
**Flow:** Dashboard -> Filters -> Select GHMC area + type + date range -> Charts update.

---

# USER STORY 3: NGO & Advocacy Features

## Executive Summary
Provide hotspot and redzone analytics plus exportable datasets for advocacy.

## User Persona & Problem Statement
**Who:** As an NGO...
**Why:** I need hard data to advocate for neglected areas.

## Scope (In & Out)
### In Scope
- Hotspot and redzone overlays.
- Average resolution time metrics.
- Data export.

## Features & Acceptance Criteria
### Feature: Hotspots & Redzones
**User Story:** As an NGO, I want to see hotspot and redzone clusters of unresolved issues.

**Acceptance Criteria:**
- [ ] Verify hotspot layer highlights dense clusters of REPORTED/IN_PROGRESS issues.
- [ ] Verify redzones show areas with high unresolved ratios.
- [ ] Verify layers can be toggled independently.

### Feature: Average Resolution Time (ART)
**User Story:** As an NGO, I want to see how fast issues are fixed.

**Acceptance Criteria:**
- [ ] Verify ART is shown by GHMC area and issue type.
- [ ] Verify dismissed tickets are excluded from ART.

### Feature: Data Export
**User Story:** As an NGO, I want to download filtered data.

**Acceptance Criteria:**
- [ ] Verify export supports CSV and JSON.
- [ ] Verify exports respect active filters.

## Functional Requirements
- Use Kepler.gl for map layers (hotspots, redzones, heatmaps).
- Read-only access to analytics DB views.
- Default base tiles from OpenStreetMap (Mapbox optional).

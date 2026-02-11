# MARG API Specification

**Version:** 1.0.0  
**Base URL:** `/api/v1`  
**Authentication:** Cookie-based (with refresh token rotation)  
**Date Format:** ISO 8601 UTC  

---

## Table of Contents

1. [Authentication](#authentication)
2. [Categories](#categories)
3. [Issues](#issues)
4. [Admin](#admin)
5. [Worker](#worker)
6. [Media](#media)
7. [Analytics](#analytics)
8. [Common Schemas](#common-schemas)
9. [Error Handling](#error-handling)
10. [Rate Limits](#rate-limits)

---

## Authentication

All authenticated endpoints require a valid session cookie. The API uses cookie-based authentication with automatic refresh token rotation.

### Public Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/otp-request` | Request OTP for login |
| POST | `/auth/login` | Login with OTP |

### Authenticated Endpoints

| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| POST | `/auth/refresh` | Refresh access token | Any authenticated |
| POST | `/auth/logout` | Logout and revoke tokens | Any authenticated |
| GET | `/auth/me` | Get current user profile | Any authenticated |

### POST /auth/otp-request

Request an OTP to be sent to the user's email.

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response (200):**
```json
{
  "message": "OTP sent to your email"
}
```

**Error Responses:**
- `400` - Invalid email format
- `429` - Rate limit exceeded

### POST /auth/lookup

Check if a user exists and get their role information.

**Request Body:**
```json
{
  "identifier": "user@example.com"
}
```

**Response (200) - User Exists:**
```json
{
  "exists": true,
  "role": "CITIZEN",
  "user_id": 123
}
```

**Response (200) - User Not Found:**
```json
{
  "exists": false
}
```

### POST /auth/login

Login with OTP and establish session.

**Request Body:**
```json
{
  "email": "user@example.com",
  "otp": "123456"
}
```

**Response (200):**
```json
{
  "message": "Login successful"
}
```

**Response Headers:**
```
Set-Cookie: access_token=<jwt>; HttpOnly; Secure; SameSite=lax; Max-Age=1800
Set-Cookie: refresh_token=<token>; HttpOnly; Secure; SameSite=lax; Path=/api/v1/auth; Max-Age=604800
```

**Response Headers:**
```
Set-Cookie: refresh_token=<token>; HttpOnly; Secure; SameSite=strict; Max-Age=604800
```

**Error Responses:**
- `401` - Invalid OTP
- `429` - Too many attempts

### POST /auth/refresh

Refresh the access token using the refresh token cookie.

**Response (200):**
```json
{
  "access_token": "eyJhbG...",
  "token_type": "bearer"
}
```

**Error Responses:**
- `401` - Invalid or expired refresh token

### POST /auth/logout

Logout the current user and revoke refresh token.

**Response (200):**
```json
{
  "message": "Logged out successfully"
}
```

**Response Headers:**
```
Set-Cookie: refresh_token=; Max-Age=0
```

### GET /auth/me

Get the current authenticated user's profile.

**Response (200):**
```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "role": "CITIZEN",
  "full_name": "John Doe"
}
```

---

## Categories

Public endpoint to retrieve issue categories.

### GET /categories

Get all available issue categories.

**Response (200):**
```json
[
  {
    "id": "uuid-string",
    "name": "Pothole",
    "default_priority": "P3",
    "expected_sla_days": 7,
    "is_active": true
  }
]
```

---

## Issues

Citizen-facing issue reporting and management.

### GET /issues/my-reports

Get all issues reported by the current user (citizens only).

**Response (200):** Array of Issue objects with category and worker relationships

### POST /issues/report

Report a new issue (citizens only).

**Request Body (multipart/form-data):**
| Field | Type | Description |
|-------|------|-------------|
| category_id | UUID | Category ID |
| lat | float | Latitude |
| lng | float | Longitude |
| address | string | Human-readable address (optional) |
| photo | file | Issue photo (required) |

**Response (200):**
```json
{
  "message": "Report submitted successfully",
  "issue_id": "uuid-string"
}
```

**Error Responses:**
- `400` - Invalid category or location format
- `422` - Missing required fields

---

## Admin

Administrative operations for managing issues, workers, and system configuration.

### Admin Analytics

#### GET /admin/analytics/worker-analytics

Get worker performance analytics (Admin/SysAdmin only).

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| start_date | date | Filter from date (ISO 8601) |
| end_date | date | Filter to date (ISO 8601) |
| worker_id | int | Filter specific worker |

**Response (200):**
```json
{
  "summary": {
    "total_workers": 25,
    "active_workers": 20,
    "avg_resolution_time_hours": 48.5
  },
  "workers": [
    {
      "worker_id": 789,
      "name": "Worker Name",
      "tasks_completed": 45,
      "tasks_in_progress": 3,
      "avg_resolution_hours": 36.2,
      "satisfaction_score": 4.5
    }
  ]
}
```

#### GET /admin/analytics/dashboard-stats

Get dashboard statistics for admin view.

**Response (200):**
```json
{
  "issues": {
    "total": 1523,
    "open": 45,
    "in_progress": 78,
    "resolved": 1200,
    "closed": 200
  },
  "performance": {
    "avg_resolution_time": 52.3,
    "sla_compliance": 87.5,
    "issues_today": 12
  }
}
```

### Admin Assignments

#### POST /admin/assign

Assign an issue to a worker.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| issue_id | UUID | Issue ID to assign |
| worker_id | UUID | Worker ID to assign to |

**Response (200):**
```json
{
  "message": "Issue assigned successfully"
}
```

#### POST /admin/bulk-assign

Bulk assign multiple issues to a worker.

**Request Body:**
```json
{
  "issue_ids": ["uuid-1", "uuid-2", "uuid-3"],
  "worker_id": "worker-uuid"
}
```

**Response (200):**
```json
{
  "message": "Assigned 3 issues"
}
```

#### POST /admin/reassign

Reassign an issue to a different worker.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| issue_id | UUID | Issue ID to reassign |
| worker_id | UUID | New worker ID |

**Response (200):**
```json
{
  "message": "Issue reassigned to Worker Name"
}
```

#### POST /admin/unassign

Remove worker assignment and reset issue to REPORTED.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| issue_id | UUID | Issue ID to unassign |

**Response (200):**
```json
{
  "message": "Issue unassigned and returned to REPORTED"
}
```

### Admin Issues

#### GET /admin/issues

Get all issues with filtering and pagination (Admin/SysAdmin).

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| status | string | Filter by status |
| priority | string | Filter by priority |
| category | string | Filter by category code |
| zone_id | int | Filter by zone |
| assignee_id | int | Filter by assignee |
| limit | int | Results per page (default: 20) |
| offset | int | Pagination offset |
| sort_by | string | Sort field (created_at, updated_at, priority) |
| sort_order | string | asc or desc |

**Response (200):**
```json
{
  "issues": [
    {
      "id": 456,
      "title": "Large pothole",
      "status": "OPEN",
      "priority": "HIGH",
      "category": "POTHOLE",
      "reporter": {
        "id": 123,
        "name": "John Doe",
        "contact": "user@example.com"
      },
      "assignee": null,
      "created_at": "2024-02-10T08:00:00Z",
      "sla_deadline": "2024-02-13T08:00:00Z"
    }
  ],
  "total": 150,
  "filters": {
    "applied": ["status", "priority"]
  }
}
```

#### POST /admin/update-status

Update issue status (state machine enforced).

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| issue_id | UUID | Issue ID |
| status | string | New status (REPORTED, ASSIGNED, ACCEPTED, IN_PROGRESS, RESOLVED, CLOSED) |

**Valid Status Values:**
- `REPORTED` → `ASSIGNED` → `ACCEPTED` → `IN_PROGRESS` → `RESOLVED` → `CLOSED`

**Response (200):**
```json
{
  "message": "Issue status updated to IN_PROGRESS"
}
```

#### POST /admin/approve

Approve a resolved issue and close it.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| issue_id | UUID | Issue ID to approve |

**Response (200):**
```json
{
  "message": "Issue approved and closed"
}
```

#### POST /admin/reject

Reject a resolved issue and return it to worker.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| issue_id | UUID | Issue ID to reject |
| reason | string | Rejection reason |

**Response (200):**
```json
{
  "message": "Issue rejected and returned to worker"
}
```

#### POST /admin/update-priority

Update issue priority.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| issue_id | UUID | Issue ID |
| priority | string | Priority level (P1, P2, P3, P4) |

**Response (200):**
```json
{
  "message": "Issue priority updated to P1"
}
```

### Admin System (SYSADMIN only)

System administration endpoints for platform configuration.

#### GET /admin/authorities

List all authorities.

**Response (200):**
```json
[
  {
    "org_id": "uuid",
    "org_name": "Delhi Municipal Corporation",
    "zone_id": "uuid",
    "zone_name": "Zone A",
    "admin_email": "admin@dmc.gov.in",
    "jurisdiction": "polygon-geojson"
  }
]
```

#### POST /admin/authorities

Create a new authority.

**Request Body:**
```json
{
  "name": "New Municipal Authority",
  "admin_email": "admin@nma.gov.in",
  "jurisdiction_points": [[lat, lng], [lat, lng], ...],
  "zone_name": "Zone B"
}
```

#### PUT /admin/authorities/{org_id}

Update authority details.

**Request Body:**
```json
{
  "name": "Updated Authority Name",
  "jurisdiction_points": [[lat, lng], ...],
  "zone_name": "Zone C"
}
```

#### DELETE /admin/authorities/{org_id}

Delete an authority.

**Response (200):**
```json
{
  "message": "Authority deleted"
}
```

#### GET /admin/issue-types

Get all issue types/categories.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| include_inactive | bool | Include inactive categories (default: true) |

**Response (200):** Array of Category objects

#### POST /admin/issue-types

Create a new issue type.

**Request Body:**
```json
{
  "name": "Street Light",
  "default_priority": "P3",
  "expected_sla_days": 7
}
```

#### PUT /admin/issue-types/{category_id}

Update an issue type.

**Request Body:**
```json
{
  "name": "Street Light",
  "default_priority": "P2",
  "expected_sla_days": 5,
  "is_active": true
}
```

#### DELETE /admin/issue-types/{category_id}

Deactivate an issue type.

**Response (200):** Updated Category object

#### POST /admin/manual-issues

Create manual issue on behalf of a citizen (SYSADMIN only).

**Request Body:**
```json
{
  "category_id": "uuid",
  "lat": 28.6139,
  "lng": 77.2090,
  "address": "Main Road, New Delhi",
  "priority": "P2",
  "org_id": "uuid"
}
```

**Response (200):**
```json
{
  "issue_id": "uuid",
  "message": "Manual issue created",
  "created_at": "2024-02-11T10:00:00Z"
}
```

### Admin Workers

#### GET /admin/workers

List all workers in the organization.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| status | string | Filter by status (active, inactive) |
| zone_id | int | Filter by zone |
| search | string | Search by name/email |

**Response (200):**
```json
{
  "workers": [
    {
      "id": 789,
      "full_name": "Worker Name",
      "email": "worker@authority.gov.in",
      "phone": "+91-1234567890",
      "zone_id": 1,
      "zone_name": "Zone A",
      "status": "active",
      "tasks_assigned": 5,
      "tasks_completed": 45,
      "joined_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 25
}
```

#### GET /admin/workers/with-stats

Get workers with detailed statistics.

#### POST /admin/deactivate-worker

Deactivate a worker and unassign their active tasks.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| worker_id | UUID | Worker ID to deactivate |

**Response (200):**
```json
{
  "message": "Worker deactivated and tasks reset"
}
```

#### POST /admin/activate-worker

Activate an existing worker account.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| worker_id | UUID | Worker ID to activate |

**Response (200):**
```json
{
  "message": "Worker activated"
}
```

#### POST /admin/bulk-register

Bulk register workers from comma-separated emails.

**Request Body:**
```json
{
  "emails_csv": "worker1@authority.gov.in, worker2@authority.gov.in, worker3@authority.gov.in"
}
```

**Response (200):**
```json
{
  "created": 3,
  "emails": ["worker1@authority.gov.in", "worker2@authority.gov.in", "worker3@authority.gov.in"]
}
```

#### POST /admin/invite

Invite a single worker to an organization.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| email | string | Worker's email address |
| org_id | UUID | Organization ID |

**Response (200):**
```json
{
  "message": "Invite sent to worker@example.com"
}
```

#### POST /admin/bulk-invite

Bulk invite workers to the admin's organization.

**Request Body:**
```json
{
  "emails": ["worker1@authority.gov.in", "worker2@authority.gov.in"]
}
```

**Response (200):**
```json
{
  "message": "Invites sent to 2 workers"
}
```

---

## Worker

Worker endpoints for managing assigned tasks.

### GET /worker/tasks

Get all tasks assigned to the current worker.

**Response (200):** Array of Issue objects with category and worker loaded

### POST /worker/tasks/{issue_id}/accept

Accept a task assignment with ETA date.

**Path Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| issue_id | UUID | Issue ID |

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| eta_date | string | ETA date (ISO 8601 format) |

**Response (200):**
```json
{
  "message": "Task accepted"
}
```

### POST /worker/tasks/{issue_id}/start

Start working on a task.

**Path Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| issue_id | UUID | Issue ID |

**Response (200):**
```json
{
  "message": "Work started"
}
```

### POST /worker/tasks/{issue_id}/resolve

Resolve a task with photo evidence.

**Path Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| issue_id | UUID | Issue ID |

**Request Body (multipart/form-data):**
| Field | Type | Description |
|-------|------|-------------|
| photo | file | Resolution photo (required) |

**Response (200):**
```json
{
  "message": "Task resolved successfully"
}
```

---

## Media

File serving endpoints for issue evidence photos.

### GET /media/{issue_id}/{type}

Retrieve evidence photo for an issue.

**Path Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| issue_id | UUID | Issue ID |
| type | string | Photo type: `before` (REPORT) or `after` (RESOLVE) |

**Response (200):** JPEG image binary

**Error Responses:**
- `404` - Media not found
- `500` - Failed to retrieve from storage

---

## Analytics

Public and authenticated analytics endpoints.

### GET /analytics/heatmap

Get issue heatmap data for geographic visualization.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| lat | float | Center latitude |
| lng | float | Center longitude |
| radius | int | Search radius in meters (default: 5000) |
| category | string | Filter by category |
| days | int | Lookback period in days (default: 30) |
| status | string | Filter by status |

**Response (200):**
```json
{
  "points": [
    {
      "lat": 28.6139,
      "lng": 77.2090,
      "weight": 5,
      "issue_count": 3,
      "categories": ["POTHOLE", "GARBAGE"]
    }
  ],
  "bounds": {
    "north": 28.72,
    "south": 28.51,
    "east": 77.35,
    "west": 77.07
  }
}
```

### GET /analytics/stats

Get public statistics.

**Response (200):**
```json
{
  "overview": {
    "total_issues": 15000,
    "resolved_issues": 12000,
    "resolution_rate": 80.0,
    "avg_resolution_days": 4.5
  },
  "by_category": [
    {
      "category": "POTHOLE",
      "count": 5000,
      "avg_resolution_days": 3.2
    }
  ],
  "trend": {
    "period": "last_30_days",
    "issues_reported": 450,
    "issues_resolved": 420
  }
}
```

### GET /analytics/issues-public

Get anonymized public issue data.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| bounds | string | Geo bounds (n,s,e,w) |
| limit | int | Max results |

**Response (200):**
```json
{
  "issues": [
    {
      "id": 456,
      "category": "POTHOLE",
      "status": "RESOLVED",
      "location": {
        "lat": 28.6139,
        "lng": 77.2090
      },
      "created_at": "2024-02-01T00:00:00Z",
      "resolved_at": "2024-02-03T00:00:00Z"
    }
  ]
}
```

### GET /analytics/audit/{issue_id}

Get audit trail for a specific issue (authenticated).

**Response (200):**
```json
{
  "issue_id": 456,
  "audit_log": [
    {
      "id": 1,
      "action": "ISSUE_CREATED",
      "performed_by": 123,
      "performed_by_name": "John Doe",
      "performed_at": "2024-02-10T08:00:00Z",
      "details": {
        "title": "Large pothole"
      }
    },
    {
      "id": 2,
      "action": "STATUS_CHANGED",
      "performed_by": 321,
      "performed_at": "2024-02-11T10:00:00Z",
      "details": {
        "from": "OPEN",
        "to": "IN_PROGRESS"
      }
    }
  ]
}
```

### GET /analytics/audit-all

Get full system audit log (Admin/SysAdmin only).

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| action | string | Filter by action type |
| user_id | int | Filter by user |
| start_date | date | Filter from |
| end_date | date | Filter to |
| limit | int | Results per page |
| offset | int | Pagination offset |

**Response (200):**
```json
{
  "logs": [
    {
      "id": 1,
      "action": "ISSUE_CREATED",
      "entity_type": "issue",
      "entity_id": 456,
      "performed_by": 123,
      "performed_by_name": "John Doe",
      "performed_at": "2024-02-10T08:00:00Z",
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0..."
    }
  ],
  "total": 50000,
  "filters_applied": {}
}
```

---

## Common Schemas

### Issue Status Values
| Status | Description |
|--------|-------------|
| `OPEN` | Newly reported issue |
| `IN_PROGRESS` | Assigned and being worked on |
| `RESOLVED` | Work completed, pending verification |
| `CLOSED` | Verified and closed |
| `REJECTED` | Rejected/invalid report |

### Priority Levels
| Priority | SLA Hours | Description |
|----------|-----------|-------------|
| `URGENT` | 24 | Safety hazard |
| `HIGH` | 72 | Significant impact |
| `MEDIUM` | 168 | Moderate impact |
| `LOW` | 336 | Minor issue |

### User Roles
| Role | Description |
|------|-------------|
| `CITIZEN` | General public user |
| `WORKER` | Field worker assigned to tasks |
| `ADMIN` | Authority administrator |
| `SYSADMIN` | System administrator |

### Location Object
```json
{
  "lat": 28.6139,
  "lng": 77.2090,
  "address": "Human-readable address"
}
```

---

## Error Handling

### Standard Error Response

All errors follow this format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable message",
    "details": {
      "field": ["error description"]
    }
  }
}
```

### HTTP Status Codes
| Code | Meaning |
|------|---------|
| `200` | Success |
| `201` | Created |
| `400` | Bad Request - Invalid input |
| `401` | Unauthorized - Authentication required |
| `403` | Forbidden - Insufficient permissions |
| `404` | Not Found |
| `409` | Conflict - Resource state conflict |
| `413` | Payload Too Large |
| `415` | Unsupported Media Type |
| `422` | Unprocessable Entity - Validation failed |
| `429` | Too Many Requests |
| `500` | Internal Server Error |

### Error Codes
| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Input validation failed |
| `AUTHENTICATION_ERROR` | Invalid credentials or token |
| `AUTHORIZATION_ERROR` | Permission denied |
| `RESOURCE_NOT_FOUND` | Requested resource doesn't exist |
| `RESOURCE_CONFLICT` | State conflict (e.g., duplicate) |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `STATE_TRANSITION_INVALID` | Invalid status change attempted |
| `FILE_TOO_LARGE` | Upload exceeds size limit |
| `UNSUPPORTED_MEDIA_TYPE` | Invalid file type |

---

## Rate Limits

| Endpoint Type | Limit | Window |
|---------------|-------|--------|
| Authentication | 5 requests | 15 minutes |
| OTP Request | 3 requests | 1 hour |
| API (authenticated) | 1000 requests | 15 minutes |
| File Uploads | 10 requests | 1 minute |
| Public Analytics | 100 requests | 15 minutes |

Rate limit headers included in responses:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1707654000
```

---

## API Versioning

Current version: **v1**

The API version is included in the URL path: `/api/v1/`

Future versions will be available at `/api/v2/`, etc. while v1 remains supported with deprecation notice.

---

## Changelog

### v1.0.0 (2024-02-11)
- Initial API release
- Complete issue lifecycle management
- Worker assignment system
- Audit logging
- Analytics and heatmap
- Cookie-based authentication
- Media upload support

---

**Last Updated:** 2024-02-11  
**Documentation Version:** 1.0.0

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
| POST | `/auth/request-otp` | Request OTP for login |
| POST | `/auth/lookup` | Validate if email/phone exists |
| POST | `/auth/login` | Login with OTP |

### Authenticated Endpoints

| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| POST | `/auth/refresh` | Refresh access token | Any authenticated |
| POST | `/auth/logout` | Logout and revoke tokens | Any authenticated |
| GET | `/auth/me` | Get current user profile | Any authenticated |

### POST /auth/request-otp

Request an OTP to be sent to the user's email/phone.

**Request Body:**
```json
{
  "identifier": "user@example.com"
}
```

**Response (200):**
```json
{
  "message": "OTP sent successfully"
}
```

**Error Responses:**
- `400` - Invalid identifier format
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
  "identifier": "user@example.com",
  "otp": "123456"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbG...",
  "token_type": "bearer",
  "user": {
    "id": 123,
    "email": "user@example.com",
    "role": "CITIZEN",
    "full_name": "John Doe"
  }
}
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
  "id": 123,
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "CITIZEN",
  "phone": "+91-1234567890",
  "organization_id": null,
  "zone_id": null,
  "created_at": "2024-01-15T08:30:00Z",
  "last_login": "2024-02-11T10:00:00Z"
}
```

---

## Categories

Public endpoint to retrieve issue categories.

### GET /categories

Get all available issue categories.

**Response (200):**
```json
{
  "categories": [
    {
      "id": 1,
      "code": "POTHOLE",
      "display_name": "Pothole",
      "description": "Road surface damage with potholes",
      "icon_url": "/icons/pothole.svg",
      "requires_photo": true,
      "auto_assign": true,
      "estimated_days": 3,
      "priority": "HIGH",
      "sla_hours": 72
    }
  ]
}
```

---

## Issues

Citizen-facing issue reporting and management.

### GET /issues

Get all issues reported by the current user (citizens only).

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| status | string | Filter by status (OPEN, IN_PROGRESS, RESOLVED, CLOSED) |
| limit | int | Number of results (default: 20, max: 100) |
| offset | int | Pagination offset |

**Response (200):**
```json
{
  "issues": [
    {
      "id": 456,
      "title": "Large pothole on Main Road",
      "description": "Dangerous pothole causing accidents",
      "category_code": "POTHOLE",
      "status": "OPEN",
      "priority": "HIGH",
      "location": {
        "lat": 28.6139,
        "lng": 77.2090,
        "address": "Main Road, New Delhi"
      },
      "created_at": "2024-02-10T08:00:00Z",
      "updated_at": "2024-02-10T08:00:00Z",
      "reported_by": 123,
      "assignee_id": null,
      "evidence_count": 2
    }
  ],
  "total": 15,
  "limit": 20,
  "offset": 0
}
```

### POST /issues

Report a new issue (citizens only).

**Request Body:**
```json
{
  "title": "Large pothole on Main Road",
  "description": "Dangerous pothole causing accidents near the market",
  "category_code": "POTHOLE",
  "location": {
    "lat": 28.6139,
    "lng": 77.2090,
    "address": "Main Road, New Delhi"
  },
  "evidence_ids": ["uuid1", "uuid2"]
}
```

**Response (201):**
```json
{
  "id": 456,
  "title": "Large pothole on Main Road",
  "status": "OPEN",
  "created_at": "2024-02-11T10:30:00Z",
  "tracking_number": "MARG-2024-000456"
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

#### POST /admin/assignments/assign

Assign an issue to a worker.

**Request Body:**
```json
{
  "issue_id": 456,
  "worker_id": 789,
  "notes": "Priority fix needed before monsoon"
}
```

**Response (200):**
```json
{
  "assignment_id": 101,
  "issue_id": 456,
  "worker_id": 789,
  "assigned_at": "2024-02-11T11:00:00Z",
  "assigned_by": 321
}
```

#### POST /admin/assignments/bulk-assign

Bulk assign multiple issues to workers.

**Request Body:**
```json
{
  "assignments": [
    {
      "issue_id": 456,
      "worker_id": 789
    },
    {
      "issue_id": 457,
      "worker_id": 790
    }
  ]
}
```

**Response (200):**
```json
{
  "success": [
    {"issue_id": 456, "assignment_id": 101},
    {"issue_id": 457, "assignment_id": 102}
  ],
  "failed": []
}
```

#### POST /admin/assignments/{assignment_id}/reassign

Reassign an existing assignment to a different worker.

**Path Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| assignment_id | int | Assignment ID |

**Request Body:**
```json
{
  "new_worker_id": 791,
  "reason": "Original worker on leave"
}
```

#### DELETE /admin/assignments/{assignment_id}

Unassign a worker from an issue.

**Path Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| assignment_id | int | Assignment ID |

**Response (200):**
```json
{
  "message": "Assignment removed successfully"
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

#### PATCH /admin/issues/{issue_id}/status

Update issue status (state machine enforced).

**Path Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| issue_id | int | Issue ID |

**Request Body:**
```json
{
  "status": "IN_PROGRESS",
  "notes": "Worker has started repair work",
  "notify_reporter": true
}
```

**Valid Status Transitions:**
- `OPEN` → `IN_PROGRESS`
- `IN_PROGRESS` → `RESOLVED`
- `RESOLVED` → `CLOSED`
- `IN_PROGRESS` → `OPEN` (revert)

**Response (200):**
```json
{
  "id": 456,
  "previous_status": "OPEN",
  "status": "IN_PROGRESS",
  "updated_at": "2024-02-11T12:00:00Z",
  "updated_by": 321
}
```

#### POST /admin/issues/{issue_id}/approve

Approve a resolved issue for closure.

**Response (200):**
```json
{
  "message": "Issue approved for closure",
  "issue_id": 456
}
```

#### POST /admin/issues/{issue_id}/reject

Reject an issue resolution and return to worker.

**Request Body:**
```json
{
  "reason": "Work incomplete - pothole still visible",
  "reopen": true
}
```

#### PATCH /admin/issues/{issue_id}/priority

Update issue priority.

**Request Body:**
```json
{
  "priority": "URGENT",
  "reason": "Safety hazard"
}
```

### Admin System

System administration endpoints (SysAdmin only).

#### GET /admin/system/authorities

List all authorities.

**Response (200):**
```json
{
  "authorities": [
    {
      "id": 1,
      "name": "Delhi Municipal Corporation",
      "code": "DMC",
      "zones": [
        {
          "id": 1,
          "name": "Zone A",
          "code": "ZONE-A"
        }
      ]
    }
  ]
}
```

#### POST /admin/system/authorities

Create a new authority.

**Request Body:**
```json
{
  "name": "New Municipal Authority",
  "code": "NMA",
  "contact_email": "admin@nma.gov.in",
  "contact_phone": "+91-11-12345678"
}
```

#### PATCH /admin/system/authorities/{authority_id}

Update authority details.

#### DELETE /admin/system/authorities/{authority_id}

Deactivate an authority.

#### GET /admin/system/issue-types

Get all issue types/categories.

#### POST /admin/system/issue-types

Create a new issue type.

**Request Body:**
```json
{
  "code": "STREETLIGHT",
  "display_name": "Street Light",
  "description": "Street light not working",
  "priority": "MEDIUM",
  "sla_hours": 48,
  "requires_photo": true
}
```

#### PATCH /admin/system/issue-types/{type_id}

Update an issue type.

#### DELETE /admin/system/issue-types/{type_id}

Deactivate an issue type.

#### POST /admin/system/manual-issues

Create manual/issue on behalf of a citizen.

**Request Body:**
```json
{
  "title": "Road damage reported via phone",
  "description": "Citizen called to report...",
  "category_code": "POTHOLE",
  "location": {
    "lat": 28.6139,
    "lng": 77.2090,
    "address": "Main Road"
  },
  "citizen_contact": "+91-9876543210",
  "citizen_name": "Anonymous"
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

#### POST /admin/workers/{worker_id}/deactivate

Deactivate a worker.

**Request Body:**
```json
{
  "reason": "Resigned",
  "reassign_tasks": true
}
```

#### POST /admin/workers/{worker_id}/activate

Reactivate a deactivated worker.

#### POST /admin/workers/bulk-register

Bulk register workers.

**Request Body:**
```json
{
  "workers": [
    {
      "full_name": "New Worker 1",
      "email": "worker1@authority.gov.in",
      "phone": "+91-1111111111",
      "zone_id": 1
    }
  ],
  "send_invite": true
}
```

#### POST /admin/workers/invite

Invite a single worker.

**Request Body:**
```json
{
  "email": "newworker@authority.gov.in",
  "full_name": "New Worker",
  "zone_id": 1,
  "role": "WORKER"
}
```

#### POST /admin/workers/bulk-invite

Bulk invite workers via email.

**Request Body:**
```json
{
  "invites": [
    {
      "email": "worker1@authority.gov.in",
      "full_name": "Worker One",
      "zone_id": 1
    },
    {
      "email": "worker2@authority.gov.in",
      "full_name": "Worker Two",
      "zone_id": 2
    }
  ]
}
```

---

## Worker

Worker endpoints for managing assigned tasks.

### GET /worker/tasks

Get all tasks assigned to the current worker.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| status | string | Filter by status (assigned, in_progress, completed) |
| limit | int | Results per page |

**Response (200):**
```json
{
  "tasks": [
    {
      "id": 456,
      "issue_id": 789,
      "title": "Fix pothole on Main Road",
      "status": "assigned",
      "priority": "HIGH",
      "category": "POTHOLE",
      "location": {
        "lat": 28.6139,
        "lng": 77.2090,
        "address": "Main Road, New Delhi"
      },
      "assigned_at": "2024-02-11T10:00:00Z",
      "due_by": "2024-02-14T10:00:00Z",
      "evidence_required": true
    }
  ],
  "total": 5
}
```

### POST /worker/tasks/{task_id}/accept

Accept a task assignment.

**Path Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| task_id | int | Task ID |

**Response (200):**
```json
{
  "message": "Task accepted",
  "status": "in_progress",
  "accepted_at": "2024-02-11T11:00:00Z"
}
```

### POST /worker/tasks/{task_id}/start

Mark task as started.

**Response (200):**
```json
{
  "message": "Task started",
  "status": "in_progress",
  "started_at": "2024-02-11T12:00:00Z"
}
```

### POST /worker/tasks/{task_id}/resolve

Submit task resolution with evidence.

**Request Body (multipart/form-data):**
| Field | Type | Description |
|-------|------|-------------|
| notes | string | Resolution notes |
| evidence[] | file | Resolution photos (optional) |
| before_photos[] | file | Before work photos |
| after_photos[] | file | After work photos |

**Response (200):**
```json
{
  "message": "Task resolved successfully",
  "resolution_id": 202,
  "status": "resolved",
  "resolved_at": "2024-02-11T14:00:00Z"
}
```

---

## Media

File upload and management endpoints.

### POST /media/upload

Upload media files (photos, documents).

**Request Body (multipart/form-data):**
| Field | Type | Description |
|-------|------|-------------|
| file | file | The file to upload |
| type | string | File type hint (image, document) |
| issue_id | int | Optional: Associate with issue |

**Response (201):**
```json
{
  "id": "uuid-string",
  "url": "https://minio.example.com/bucket/filename.jpg",
  "thumbnail_url": "https://minio.example.com/bucket/thumb_filename.jpg",
  "filename": "filename.jpg",
  "mime_type": "image/jpeg",
  "size": 2048576,
  "uploaded_at": "2024-02-11T10:30:00Z"
}
```

**Supported Types:**
- Images: `image/jpeg`, `image/png`, `image/webp` (max 10MB)
- Documents: `application/pdf` (max 5MB)

**Error Responses:**
- `413` - File too large
- `415` - Unsupported media type

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

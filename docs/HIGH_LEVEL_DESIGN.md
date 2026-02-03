# High-Level Design Document
## Urban Infrastructure Reporting System (UIRS)

**Version:** 1.0  
**Last Updated:** February 2026  
**Document Type:** Technical Architecture & Design Specification

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [Technology Stack](#3-technology-stack)
4. [Module Architecture](#4-module-architecture)
5. [Data Architecture](#5-data-architecture)
6. [API Architecture](#6-api-architecture)
7. [Security Architecture](#7-security-architecture)
8. [Frontend Architecture](#8-frontend-architecture)
9. [Integration Architecture](#9-integration-architecture)
10. [Deployment Architecture](#10-deployment-architecture)
11. [Data Flow Diagrams](#11-data-flow-diagrams)
12. [Non-Functional Requirements](#12-non-functional-requirements)

---

## 1. Executive Summary

### 1.1 Purpose

The Urban Infrastructure Reporting System (UIRS) is a full-stack web application designed to digitize and streamline the reporting, tracking, and resolution of city infrastructure issues such as potholes, drainage problems, street light outages, and garbage accumulation. The system serves the Greater Hyderabad Municipal Corporation (GHMC) and its citizens.

### 1.2 Scope

The system encompasses:
- **Citizen Portal**: Mobile-first interface for reporting issues with GPS and photo evidence
- **Authority Dashboard**: Administrative interface for issue triage, worker assignment, and resolution approval
- **Worker Application**: Field force interface for task management and resolution proof submission
- **Analytics Platform**: Real-time city health monitoring with geospatial visualization

### 1.3 Key Objectives

| Objective | Description |
|-----------|-------------|
| **Transparency** | Complete audit trail of all system mutations |
| **Accountability** | GPS-verified locations and timestamped photo evidence |
| **Efficiency** | Streamlined workflow from report to resolution |
| **Accessibility** | Mobile-responsive, offline-capable citizen interface |
| **Scalability** | Architecture supporting city-wide deployment |

---

## 2. System Architecture Overview

### 2.1 Architectural Pattern

The system follows a **3-Tier Architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION TIER                                │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │
│  │   Citizen   │ │  Authority  │ │   Worker    │ │  Analytics  │       │
│  │   Portal    │ │  Dashboard  │ │    App      │ │  Dashboard  │       │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘       │
│         │               │               │               │               │
│         └───────────────┴───────┬───────┴───────────────┘               │
│                                 │                                        │
│                    React 18 + Vite + Tailwind CSS                       │
└─────────────────────────────────┼───────────────────────────────────────┘
                                  │ HTTPS/REST API
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         APPLICATION TIER                                 │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐     │
│  │                     FastAPI Application                         │     │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │     │
│  │  │   Auth   │ │  Issues  │ │  Admin   │ │ Analytics│          │     │
│  │  │  Module  │ │  Module  │ │  Module  │ │  Module  │          │     │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘          │     │
│  │       └────────────┴─────┬──────┴────────────┘                 │     │
│  │                          │                                      │     │
│  │  ┌──────────────────────────────────────────────────────┐      │     │
│  │  │              Service Layer (Business Logic)           │      │     │
│  │  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐         │      │     │
│  │  │  │ Email  │ │  EXIF  │ │ MinIO  │ │ Audit  │         │      │     │
│  │  │  │Service │ │Service │ │Client  │ │Service │         │      │     │
│  │  │  └────────┘ └────────┘ └────────┘ └────────┘         │      │     │
│  │  └──────────────────────────────────────────────────────┘      │     │
│  └────────────────────────────────────────────────────────────────┘     │
│                                                                          │
│                    Python 3.12 + FastAPI + SQLModel                      │
└─────────────────────────────────┼───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           DATA TIER                                      │
│                                                                          │
│  ┌─────────────────────────────┐    ┌─────────────────────────────┐    │
│  │   PostgreSQL + PostGIS      │    │         MinIO               │    │
│  │                             │    │   (Object Storage)          │    │
│  │  • User Management          │    │                             │    │
│  │  • Issue Lifecycle          │    │  • Before Images            │    │
│  │  • Geospatial Data          │    │  • After Images             │    │
│  │  • Audit Logs               │    │  • EXIF Metadata            │    │
│  │  • Categories & Zones       │    │                             │    │
│  └─────────────────────────────┘    └─────────────────────────────┘    │
│                                                                          │
│              PostgreSQL 14 + PostGIS 3.3 | MinIO (S3-Compatible)        │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Interaction Overview

```
                                    ┌──────────────┐
                                    │   Browser    │
                                    │  (React App) │
                                    └──────┬───────┘
                                           │
                           ┌───────────────┼───────────────┐
                           │               │               │
                           ▼               ▼               ▼
                    ┌──────────┐    ┌──────────┐    ┌──────────┐
                    │  Leaflet │    │   Axios  │    │ Recharts │
                    │   Maps   │    │  HTTP    │    │  Charts  │
                    └──────────┘    └────┬─────┘    └──────────┘
                                         │
                                         ▼
                              ┌─────────────────────┐
                              │    FastAPI Server   │
                              │    (Port 8088)      │
                              └──────────┬──────────┘
                                         │
              ┌──────────────────────────┼──────────────────────────┐
              │                          │                          │
              ▼                          ▼                          ▼
       ┌─────────────┐           ┌─────────────┐           ┌─────────────┐
       │  PostgreSQL │           │    MinIO    │           │   SMTP      │
       │   + PostGIS │           │   Storage   │           │  (Email)    │
       │  (Port 5432)│           │ (Port 9000) │           │             │
       └─────────────┘           └─────────────┘           └─────────────┘
```

---

## 3. Technology Stack

### 3.1 Complete Technology Matrix

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **Frontend Framework** | React | 18.2 | Component-based UI development |
| **Build Tool** | Vite | 5.0 | Fast HMR, ESM-based bundling |
| **Styling** | Tailwind CSS | 3.3 | Utility-first CSS framework |
| **UI Components** | Radix UI | Latest | Accessible component primitives |
| **Animations** | Framer Motion | 12.x | Declarative animations |
| **Maps** | Leaflet + React-Leaflet | 1.9/4.2 | Interactive mapping |
| **Heatmaps** | Leaflet.heat | 0.2 | Density visualization |
| **Geocoding** | Leaflet-control-geocoder | 3.3 | Address search |
| **Charts** | Recharts | 2.9 | Data visualization |
| **HTTP Client** | Axios | 1.6 | API communication |
| **Routing** | React Router DOM | 6.18 | Client-side routing |
| **State Management** | Zustand | 4.4 | Lightweight state management |
| **Icons** | Lucide React | 0.292 | Icon library |
| **Backend Framework** | FastAPI | Latest | High-performance Python API |
| **ORM** | SQLModel | Latest | Pydantic + SQLAlchemy fusion |
| **Database** | PostgreSQL | 14 | Primary relational database |
| **Geospatial** | PostGIS | 3.3 | Spatial data extension |
| **Object Storage** | MinIO | Latest | S3-compatible file storage |
| **Authentication** | python-jose | Latest | JWT token generation |
| **Password Hashing** | Passlib + bcrypt | Latest | Secure credential storage |
| **Email** | FastAPI-Mail | Latest | SMTP email delivery |
| **Image Processing** | Pillow | Latest | EXIF extraction |
| **Validation** | Pydantic | 2.x | Request/response validation |
| **ASGI Server** | Uvicorn | Latest | Production ASGI server |
| **Containerization** | Docker Compose | Latest | Multi-container orchestration |

### 3.2 Technology Selection Rationale

#### 3.2.1 Why FastAPI?

```
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Advantages                            │
├─────────────────────────────────────────────────────────────────┤
│  ✓ Automatic OpenAPI documentation generation                   │
│  ✓ Native async/await support for high concurrency              │
│  ✓ Pydantic integration for request validation                  │
│  ✓ Type hints for better IDE support and error prevention       │
│  ✓ Dependency injection system for clean architecture           │
│  ✓ 40% faster than Flask, comparable to Node.js                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.2.2 Why PostgreSQL + PostGIS?

```
┌─────────────────────────────────────────────────────────────────┐
│                 PostgreSQL + PostGIS Selection                   │
├─────────────────────────────────────────────────────────────────┤
│  RELATIONAL NEEDS:                                               │
│  • Complex relationships (User → Issue → Worker)                 │
│  • ACID compliance for audit integrity                           │
│  • Mature ecosystem and tooling                                  │
│                                                                  │
│  GEOSPATIAL NEEDS:                                               │
│  • Native POINT geometry for issue locations                     │
│  • POLYGON support for administrative zones                      │
│  • Spatial indexing (GiST) for proximity queries                 │
│  • ST_Contains, ST_Distance for zone-based routing               │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.2.3 Why React + Vite?

```
┌─────────────────────────────────────────────────────────────────┐
│                    React + Vite Selection                        │
├─────────────────────────────────────────────────────────────────┤
│  REACT:                                                          │
│  • Component reusability across dashboards                       │
│  • Large ecosystem (Leaflet, Recharts integrations)              │
│  • Hooks for clean state management                              │
│                                                                  │
│  VITE:                                                           │
│  • Sub-second hot module replacement                             │
│  • ESM-native, no bundling during development                    │
│  • Optimized production builds with Rollup                       │
│  • PWA plugin support for offline capability                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Module Architecture

### 4.1 Backend Module Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── deps.py              # Dependency injection (DB, Auth)
│   │   └── v1/
│   │       ├── auth.py          # Authentication endpoints
│   │       ├── issues.py        # Citizen issue reporting
│   │       ├── admin.py         # Authority operations
│   │       ├── worker.py        # Field force operations
│   │       ├── analytics.py     # Statistics & visualization
│   │       ├── media.py         # Image serving
│   │       └── api.py           # Router aggregation
│   │
│   ├── core/
│   │   ├── config.py            # Environment configuration
│   │   └── security.py          # JWT & password utilities
│   │
│   ├── db/
│   │   └── session.py           # Database connection management
│   │
│   ├── models/
│   │   └── domain.py            # SQLModel entity definitions
│   │
│   ├── schemas/
│   │   ├── auth.py              # Auth request/response schemas
│   │   ├── issue.py             # Issue schemas
│   │   └── admin.py             # Admin operation schemas
│   │
│   ├── services/
│   │   ├── email.py             # OTP email delivery
│   │   ├── minio_client.py      # Object storage operations
│   │   ├── exif.py              # Image metadata extraction
│   │   ├── audit.py             # Audit log recording
│   │   ├── admin.py             # Admin business logic
│   │   └── analytics.py         # Statistics computation
│   │
│   └── main.py                  # Application entry point
│
├── seed.py                      # Database initialization
└── requirements.txt             # Python dependencies
```

### 4.2 Module Descriptions

#### 4.2.1 Authentication Module (`auth.py`)

**Purpose:** Handles user identification via OTP-based passwordless authentication.

```
┌─────────────────────────────────────────────────────────────────┐
│                    AUTHENTICATION FLOW                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────┐      ┌─────────┐      ┌─────────┐      ┌───────┐ │
│   │  User   │──1──▶│ Request │──2──▶│ Generate│──3──▶│ Store │ │
│   │ (Email) │      │   OTP   │      │   OTP   │      │  OTP  │ │
│   └─────────┘      └─────────┘      └─────────┘      └───┬───┘ │
│                                                          │      │
│                                                          4      │
│                                                          ▼      │
│   ┌─────────┐      ┌─────────┐      ┌─────────┐      ┌───────┐ │
│   │  JWT    │◀──7──│ Create  │◀──6──│ Verify  │◀──5──│ Email │ │
│   │ Token   │      │  User   │      │   OTP   │      │  OTP  │ │
│   └─────────┘      └─────────┘      └─────────┘      └───────┘ │
│                                                                  │
│   TECHNOLOGIES:                                                  │
│   • python-jose: JWT token creation with HS256                  │
│   • FastAPI-Mail: SMTP delivery (DEV_MODE skips)                │
│   • PostgreSQL: OTP storage with expiry                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/otp-request` | Generate and send OTP to email |
| POST | `/auth/login` | Verify OTP, return JWT token |

**Security Features:**
- OTP expires after 10 minutes
- 6-digit cryptographically random codes
- JWT tokens expire after 7 days
- Auto-creates user on first login

---

#### 4.2.2 Issues Module (`issues.py`)

**Purpose:** Handles citizen issue reporting with geospatial and media data.

```
┌─────────────────────────────────────────────────────────────────┐
│                    ISSUE REPORTING FLOW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   CITIZEN INPUT                          SYSTEM PROCESSING       │
│   ─────────────                          ─────────────────       │
│                                                                  │
│   ┌──────────────┐                                              │
│   │  GPS coords  │────┐                                         │
│   │  (lat, lng)  │    │     ┌─────────────────────────────┐    │
│   └──────────────┘    │     │                             │    │
│                       ├────▶│  1. Validate coordinates    │    │
│   ┌──────────────┐    │     │  2. Create POINT geometry   │    │
│   │    Photo     │────┤     │  3. Extract EXIF metadata   │    │
│   │  (JPEG/PNG)  │    │     │  4. Upload to MinIO         │    │
│   └──────────────┘    │     │  5. Create Issue record     │    │
│                       │     │  6. Log to Audit Trail      │    │
│   ┌──────────────┐    │     │  7. Return Issue ID         │    │
│   │  Category    │────┤     │                             │    │
│   │  Selection   │    │     └─────────────────────────────┘    │
│   └──────────────┘    │                                         │
│                       │                                         │
│   ┌──────────────┐    │                                         │
│   │ Description  │────┘                                         │
│   │  (Optional)  │                                              │
│   └──────────────┘                                              │
│                                                                  │
│   TECHNOLOGIES:                                                  │
│   • PostGIS: ST_MakePoint for geometry creation                 │
│   • MinIO: S3 PutObject for image storage                       │
│   • Pillow: EXIF data extraction (GPS, timestamp)               │
│   • GeoAlchemy2: Python geometry type mapping                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/issues/report` | Submit new infrastructure issue |
| GET | `/issues/my-reports` | Get citizen's own reports |

**Data Processing:**
- Multipart form handling for file upload
- EXIF GPS validation against submitted coordinates
- Automatic issue clustering by proximity (future enhancement)

---

#### 4.2.3 Admin Module (`admin.py`)

**Purpose:** Authority operations including issue management, worker assignment, and resolution verification.

```
┌─────────────────────────────────────────────────────────────────┐
│                    ADMIN OPERATIONS MATRIX                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ISSUE MANAGEMENT                                                │
│  ────────────────                                                │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐         │
│  │  List   │   │ Filter  │   │ Triage  │   │ Assign  │         │
│  │ Issues  │──▶│by Status│──▶│Priority │──▶│ Worker  │         │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘         │
│                                                                  │
│  WORKER MANAGEMENT                                               │
│  ─────────────────                                               │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐                       │
│  │  List   │   │  View   │   │ Assign  │                       │
│  │ Workers │──▶│Workload │──▶│  Tasks  │                       │
│  └─────────┘   └─────────┘   └─────────┘                       │
│                                                                  │
│  RESOLUTION VERIFICATION                                         │
│  ───────────────────────                                         │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐         │
│  │ Review  │   │ Compare │   │ Approve │   │  Close  │         │
│  │  Proof  │──▶│Before/  │──▶│   OR    │──▶│  Issue  │         │
│  │         │   │ After   │   │ Reject  │   │         │         │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/issues` | List all issues with filters |
| GET | `/admin/workers` | List active field workers |
| GET | `/admin/categories` | Get issue categories |
| POST | `/admin/bulk-assign` | Assign multiple issues to worker |
| POST | `/admin/approve` | Approve resolved issue |
| POST | `/admin/reject` | Reject with feedback |

**Business Logic:**
- Bulk assignment updates all selected issues atomically
- Rejection sends feedback to worker for re-resolution
- Approval transitions issue to CLOSED state

---

#### 4.2.4 Worker Module (`worker.py`)

**Purpose:** Field force task management and resolution proof submission.

```
┌─────────────────────────────────────────────────────────────────┐
│                    WORKER TASK LIFECYCLE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│      ASSIGNED           ACCEPTED          IN_PROGRESS            │
│         │                  │                   │                 │
│         ▼                  ▼                   ▼                 │
│   ┌──────────┐      ┌──────────┐       ┌──────────┐            │
│   │ View     │      │ Provide  │       │ Navigate │            │
│   │ Task     │─────▶│   ETA    │──────▶│ to Site  │            │
│   │ Details  │      │          │       │          │            │
│   └──────────┘      └──────────┘       └──────────┘            │
│                                              │                   │
│                                              ▼                   │
│                                        ┌──────────┐             │
│                                        │ Perform  │             │
│                                        │  Repair  │             │
│                                        └────┬─────┘             │
│                                              │                   │
│                                              ▼                   │
│   ┌──────────────────────────────────────────────────────┐      │
│   │              RESOLUTION SUBMISSION                    │      │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │      │
│   │  │   Capture   │  │   Upload    │  │   Submit    │  │      │
│   │  │ After Photo │─▶│  to MinIO   │─▶│   Proof     │  │      │
│   │  └─────────────┘  └─────────────┘  └─────────────┘  │      │
│   └──────────────────────────────────────────────────────┘      │
│                              │                                   │
│                              ▼                                   │
│                         RESOLVED                                 │
│                    (Awaiting Approval)                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/worker/tasks` | Get worker's assigned tasks |
| POST | `/worker/tasks/{id}/accept` | Accept with ETA |
| POST | `/worker/tasks/{id}/start` | Mark as in-progress |
| POST | `/worker/tasks/{id}/resolve` | Submit resolution proof |

---

#### 4.2.5 Analytics Module (`analytics.py`)

**Purpose:** Real-time statistics, heatmap generation, and trend analysis.

```
┌─────────────────────────────────────────────────────────────────┐
│                    ANALYTICS ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   DATA SOURCES                      COMPUTED METRICS             │
│   ────────────                      ────────────────             │
│                                                                  │
│   ┌─────────────┐                   ┌─────────────────────┐     │
│   │   Issues    │──────────────────▶│ • Total Reported    │     │
│   │   Table     │                   │ • By Status         │     │
│   └─────────────┘                   │ • By Category       │     │
│                                     │ • Resolution Rate   │     │
│   ┌─────────────┐                   └─────────────────────┘     │
│   │   Users     │──────────────────▶┌─────────────────────┐     │
│   │   Table     │                   │ • Active Workers    │     │
│   └─────────────┘                   │ • Worker Workload   │     │
│                                     └─────────────────────┘     │
│   ┌─────────────┐                                               │
│   │  PostGIS    │──────────────────▶┌─────────────────────┐     │
│   │  Geometry   │                   │ • Heatmap Points    │     │
│   └─────────────┘                   │ • Intensity Values  │     │
│                                     └─────────────────────┘     │
│                                                                  │
│   TREND CALCULATION (Last 7 Days)                               │
│   ────────────────────────────────                              │
│   SELECT DATE(created_at), COUNT(*)                             │
│   FROM issue                                                     │
│   WHERE created_at >= NOW() - INTERVAL '7 days'                 │
│   GROUP BY DATE(created_at)                                     │
│                                                                  │
│   SLA COMPLIANCE                                                 │
│   ──────────────                                                 │
│   (Resolved + Closed) / Total Issues × 100                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/analytics/stats` | Dashboard summary statistics |
| GET | `/analytics/heatmap` | Geospatial density data |
| GET | `/analytics/issues-public` | Public issue list for markers |
| GET | `/analytics/audit/{id}` | Issue audit trail |

---

#### 4.2.6 Media Module (`media.py`)

**Purpose:** Secure image serving from MinIO storage.

```
┌─────────────────────────────────────────────────────────────────┐
│                    MEDIA SERVING FLOW                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Browser Request                                                │
│        │                                                         │
│        ▼                                                         │
│   /media/{issue_id}/{type}   type = "before" | "after"          │
│        │                                                         │
│        ▼                                                         │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐      │
│   │  Validate   │────▶│  Construct  │────▶│   Fetch     │      │
│   │  Issue ID   │     │  MinIO Path │     │  from MinIO │      │
│   └─────────────┘     └─────────────┘     └─────────────┘      │
│                                                  │               │
│                                                  ▼               │
│                            ┌─────────────────────────────┐      │
│                            │  Return StreamingResponse   │      │
│                            │  Content-Type: image/jpeg   │      │
│                            └─────────────────────────────┘      │
│                                                                  │
│   STORAGE PATH CONVENTION:                                       │
│   ────────────────────────                                       │
│   {bucket}/issues/{issue_id}/before.jpg                         │
│   {bucket}/issues/{issue_id}/after.jpg                          │
│                                                                  │
│   FALLBACK (DEV MODE):                                           │
│   ────────────────────                                           │
│   mock_storage/issues/{issue_id}/before.jpg                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

### 4.3 Service Layer Architecture

#### 4.3.1 Email Service (`email.py`)

```python
# Service Interface
class EmailService:
    async def send_otp(email: str, otp: str) -> bool
    
# Implementation Details
┌─────────────────────────────────────────────────────────────────┐
│  DEV_MODE = True                                                 │
│  ─────────────────                                               │
│  → Prints OTP to console: [DEV MODE] OTP for email: 123456      │
│  → Returns immediately (no SMTP connection)                      │
│                                                                  │
│  DEV_MODE = False                                                │
│  ──────────────────                                              │
│  → Connects to SMTP server (smtp.example.com:587)               │
│  → Sends HTML email with OTP                                     │
│  → Uses TLS encryption                                           │
└─────────────────────────────────────────────────────────────────┘
```

#### 4.3.2 MinIO Client (`minio_client.py`)

```python
# Service Interface
class MinioService:
    def upload_evidence(issue_id: UUID, file: UploadFile, type: str) -> str
    def get_evidence(issue_id: UUID, type: str) -> bytes
    def delete_evidence(issue_id: UUID) -> bool

# Configuration
┌─────────────────────────────────────────────────────────────────┐
│  MINIO_ENDPOINT:    localhost:9000                               │
│  MINIO_ACCESS_KEY:  minioadmin                                   │
│  MINIO_SECRET_KEY:  minioadmin                                   │
│  MINIO_BUCKET:      infrastructure-evidence                      │
│  MINIO_SECURE:      False (True in production with HTTPS)       │
└─────────────────────────────────────────────────────────────────┘
```

#### 4.3.3 EXIF Service (`exif.py`)

```python
# Service Interface
class ExifService:
    def extract_metadata(image_bytes: bytes) -> dict
    def validate_gps(exif_gps: tuple, submitted_coords: tuple) -> bool

# Extracted Fields
┌─────────────────────────────────────────────────────────────────┐
│  GPS_LATITUDE:       Decimal degrees                             │
│  GPS_LONGITUDE:      Decimal degrees                             │
│  DATETIME_ORIGINAL:  Photo capture timestamp                     │
│  DEVICE_MAKE:        Camera manufacturer                         │
│  DEVICE_MODEL:       Camera model                                │
└─────────────────────────────────────────────────────────────────┘
```

#### 4.3.4 Audit Service (`audit.py`)

```python
# Service Interface
class AuditService:
    def log(
        session: Session,
        action: str,
        entity_id: UUID,
        actor_id: UUID,
        old_value: str,
        new_value: str
    ) -> AuditLog

# Audit Log Entry Structure
┌─────────────────────────────────────────────────────────────────┐
│  id:          UUID (Primary Key)                                 │
│  action:      "STATUS_CHANGE" | "ASSIGNMENT" | "CREATED" | ...  │
│  entity_id:   UUID of affected record                            │
│  actor_id:    UUID of user performing action                     │
│  old_value:   Previous state (nullable)                          │
│  new_value:   New state                                          │
│  created_at:  Timestamp with timezone                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Data Architecture

### 5.1 Entity-Relationship Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         DATABASE SCHEMA                                   │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────────┐         ┌─────────────────┐                         │
│  │   Organization  │         │      Zone       │                         │
│  ├─────────────────┤         ├─────────────────┤                         │
│  │ id: UUID (PK)   │◀────────│ org_id: UUID(FK)│                         │
│  │ name: String    │         │ id: UUID (PK)   │                         │
│  │ code: String    │         │ name: String    │                         │
│  │ created_at      │         │ boundary: POLY  │◀──── PostGIS Polygon   │
│  └────────┬────────┘         └─────────────────┘                         │
│           │                                                               │
│           │ 1:N                                                           │
│           ▼                                                               │
│  ┌─────────────────┐         ┌─────────────────┐                         │
│  │      User       │         │    Category     │                         │
│  ├─────────────────┤         ├─────────────────┤                         │
│  │ id: UUID (PK)   │         │ id: UUID (PK)   │                         │
│  │ email: String   │         │ name: String    │                         │
│  │ role: Enum      │         │ priority: Enum  │                         │
│  │ org_id: UUID(FK)│         │ sla_days: Int   │                         │
│  │ status: Enum    │         └────────┬────────┘                         │
│  │ full_name       │                  │                                   │
│  └────────┬────────┘                  │ 1:N                               │
│           │                           │                                   │
│           │                           ▼                                   │
│           │              ┌─────────────────────────┐                     │
│           │              │         Issue           │                     │
│           │              ├─────────────────────────┤                     │
│           │ 1:N (worker) │ id: UUID (PK)           │                     │
│           └─────────────▶│ category_id: UUID (FK)  │                     │
│                          │ reporter_email: String  │                     │
│                          │ worker_id: UUID (FK)    │◀── Assigned Worker  │
│                          │ location: POINT         │◀── PostGIS Point    │
│                          │ status: Enum            │                     │
│                          │ priority: Enum          │                     │
│                          │ before_image_url        │                     │
│                          │ after_image_url         │                     │
│                          │ created_at, updated_at  │                     │
│                          └───────────┬─────────────┘                     │
│                                      │                                    │
│                                      │ 1:N                                │
│                                      ▼                                    │
│                          ┌─────────────────────────┐                     │
│                          │       AuditLog          │                     │
│                          ├─────────────────────────┤                     │
│                          │ id: UUID (PK)           │                     │
│                          │ entity_id: UUID (FK)    │                     │
│                          │ actor_id: UUID (FK)     │                     │
│                          │ action: String          │                     │
│                          │ old_value: String       │                     │
│                          │ new_value: String       │                     │
│                          │ created_at              │                     │
│                          └─────────────────────────┘                     │
│                                                                           │
│  ┌─────────────────┐                                                      │
│  │       OTP       │                                                      │
│  ├─────────────────┤                                                      │
│  │ id: UUID (PK)   │                                                      │
│  │ email: String   │                                                      │
│  │ code: String    │                                                      │
│  │ expires_at      │                                                      │
│  │ created_at      │                                                      │
│  └─────────────────┘                                                      │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Issue State Machine

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         ISSUE STATUS LIFECYCLE                            │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│                              ┌──────────────┐                             │
│                              │   REPORTED   │                             │
│                              │              │                             │
│                              │ Citizen      │                             │
│                              │ submits      │                             │
│                              └──────┬───────┘                             │
│                                     │                                      │
│                          Admin assigns worker                              │
│                                     │                                      │
│                                     ▼                                      │
│                              ┌──────────────┐                             │
│                              │   ASSIGNED   │                             │
│                              │              │                             │
│                              │ Waiting for  │                             │
│                              │ acceptance   │                             │
│                              └──────┬───────┘                             │
│                                     │                                      │
│                          Worker accepts with ETA                           │
│                                     │                                      │
│                                     ▼                                      │
│                              ┌──────────────┐                             │
│                              │   ACCEPTED   │                             │
│                              │              │                             │
│                              │ Worker       │                             │
│                              │ committed    │                             │
│                              └──────┬───────┘                             │
│                                     │                                      │
│                          Worker starts on-site work                        │
│                                     │                                      │
│                                     ▼                                      │
│                              ┌──────────────┐                             │
│                              │ IN_PROGRESS  │                             │
│                              │              │                             │
│                              │ Active       │                             │
│                              │ repair       │                             │
│                              └──────┬───────┘                             │
│                                     │                                      │
│                          Worker submits "after" photo                      │
│                                     │                                      │
│                                     ▼                                      │
│   ┌──────────────┐           ┌──────────────┐                             │
│   │   REJECTED   │◀──────────│   RESOLVED   │                             │
│   │              │  Admin    │              │                             │
│   │ Needs        │  rejects  │ Pending      │                             │
│   │ re-work      │           │ approval     │                             │
│   └──────┬───────┘           └──────┬───────┘                             │
│          │                          │                                      │
│          │                   Admin approves                                │
│          │                          │                                      │
│          │                          ▼                                      │
│          │                   ┌──────────────┐                             │
│          └──────────────────▶│    CLOSED    │                             │
│            Re-resolve        │              │                             │
│                              │ Successfully │                             │
│                              │ completed    │                             │
│                              └──────────────┘                             │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### 5.3 PostGIS Spatial Operations

```sql
-- Issue Location Storage
CREATE TABLE issue (
    id UUID PRIMARY KEY,
    location GEOMETRY(POINT, 4326),  -- WGS84 coordinate system
    ...
);

-- Spatial Index for Performance
CREATE INDEX idx_issue_location ON issue USING GIST(location);

-- Example Queries Used in System:

-- 1. Find issues within a zone
SELECT i.* FROM issue i, zone z
WHERE ST_Contains(z.boundary, i.location)
AND z.id = :zone_id;

-- 2. Find nearest worker to an issue
SELECT u.*, ST_Distance(i.location, w.last_known_location) as distance
FROM "user" u
WHERE u.role = 'WORKER'
ORDER BY distance ASC
LIMIT 1;

-- 3. Generate heatmap data (lat/lng extraction)
SELECT 
    ST_Y(location) as lat,  -- Latitude
    ST_X(location) as lng,  -- Longitude
    0.5 as intensity
FROM issue
WHERE status != 'CLOSED';
```

---

## 6. API Architecture

### 6.1 RESTful Design Principles

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         API DESIGN STANDARDS                              │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  URL STRUCTURE                                                            │
│  ─────────────                                                            │
│  /api/v1/{resource}                    → Collection                       │
│  /api/v1/{resource}/{id}               → Individual resource              │
│  /api/v1/{resource}/{id}/{sub}         → Sub-resource                     │
│                                                                           │
│  HTTP METHODS                                                             │
│  ────────────                                                             │
│  GET     → Read (idempotent)                                              │
│  POST    → Create / Action                                                │
│  PUT     → Full update                                                    │
│  PATCH   → Partial update                                                 │
│  DELETE  → Remove                                                         │
│                                                                           │
│  RESPONSE CODES                                                           │
│  ──────────────                                                           │
│  200 OK              → Successful read/update                             │
│  201 Created         → Resource created                                   │
│  400 Bad Request     → Validation error                                   │
│  401 Unauthorized    → Missing/invalid token                              │
│  403 Forbidden       → Insufficient permissions                           │
│  404 Not Found       → Resource doesn't exist                             │
│  500 Internal Error  → Server-side failure                                │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### 6.2 API Endpoint Catalog

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    COMPLETE API ENDPOINT REFERENCE                        │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  AUTHENTICATION (/api/v1/auth)                                            │
│  ─────────────────────────────                                            │
│  POST /otp-request          Public    Request OTP via email               │
│  POST /login                Public    Verify OTP, receive JWT             │
│                                                                           │
│  ISSUES (/api/v1/issues)                                                  │
│  ───────────────────────                                                  │
│  POST /report               Citizen   Submit new issue (multipart)        │
│  GET  /my-reports           Citizen   List own reports                    │
│                                                                           │
│  ADMIN (/api/v1/admin)                                                    │
│  ─────────────────────                                                    │
│  GET  /issues               Admin     List all issues (filterable)        │
│  GET  /workers              Admin     List active workers                 │
│  GET  /categories           Public    List issue categories               │
│  POST /bulk-assign          Admin     Assign issues to worker             │
│  POST /approve              Admin     Approve resolution                  │
│  POST /reject               Admin     Reject with reason                  │
│                                                                           │
│  WORKER (/api/v1/worker)                                                  │
│  ───────────────────────                                                  │
│  GET  /tasks                Worker    Get assigned tasks                  │
│  POST /tasks/{id}/accept    Worker    Accept with ETA                     │
│  POST /tasks/{id}/start     Worker    Mark in-progress                    │
│  POST /tasks/{id}/resolve   Worker    Submit resolution (multipart)       │
│                                                                           │
│  ANALYTICS (/api/v1/analytics)                                            │
│  ─────────────────────────────                                            │
│  GET  /stats                Public    Dashboard statistics                │
│  GET  /heatmap              Public    Geospatial density data             │
│  GET  /issues-public        Public    Issue list for map markers          │
│  GET  /audit/{issue_id}     Auth      Issue audit trail                   │
│                                                                           │
│  MEDIA (/api/v1/media)                                                    │
│  ─────────────────────                                                    │
│  GET  /{issue_id}/before    Public    Before image                        │
│  GET  /{issue_id}/after     Public    After image (if exists)             │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### 6.3 Request/Response Examples

#### Authentication Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  POST /api/v1/auth/otp-request                                   │
├─────────────────────────────────────────────────────────────────┤
│  Request:                                                        │
│  {                                                               │
│    "email": "citizen@example.com"                                │
│  }                                                               │
│                                                                  │
│  Response (200):                                                 │
│  {                                                               │
│    "message": "OTP sent successfully"                            │
│  }                                                               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  POST /api/v1/auth/login                                         │
├─────────────────────────────────────────────────────────────────┤
│  Request:                                                        │
│  {                                                               │
│    "email": "citizen@example.com",                               │
│    "otp": "123456"                                               │
│  }                                                               │
│                                                                  │
│  Response (200):                                                 │
│  {                                                               │
│    "access_token": "eyJhbGciOiJIUzI1NiIs...",                   │
│    "token_type": "bearer"                                        │
│  }                                                               │
│                                                                  │
│  JWT Payload:                                                    │
│  {                                                               │
│    "sub": "citizen@example.com",                                 │
│    "role": "CITIZEN",                                            │
│    "user_id": "uuid-here",                                       │
│    "exp": 1738540800                                             │
│  }                                                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Security Architecture

### 7.1 Authentication & Authorization Model

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    SECURITY ARCHITECTURE                                  │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  AUTHENTICATION LAYER                                                     │
│  ────────────────────                                                     │
│                                                                           │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                   │
│  │    OTP      │    │    JWT      │    │   Bearer    │                   │
│  │ Generation  │───▶│   Token     │───▶│   Header    │                   │
│  │ (6-digit)   │    │  (7 days)   │    │   Verify    │                   │
│  └─────────────┘    └─────────────┘    └─────────────┘                   │
│        │                   │                   │                          │
│        ▼                   ▼                   ▼                          │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │  Security Measures:                                          │         │
│  │  • OTP stored hashed in database                             │         │
│  │  • OTP expires after 10 minutes                              │         │
│  │  • JWT signed with HS256 algorithm                           │         │
│  │  • Secret key from environment variable                      │         │
│  │  • Token contains role for authorization                     │         │
│  └─────────────────────────────────────────────────────────────┘         │
│                                                                           │
│  AUTHORIZATION LAYER (Role-Based Access Control)                          │
│  ───────────────────────────────────────────────                          │
│                                                                           │
│  ┌─────────┬─────────────────────────────────────────────────────┐       │
│  │  Role   │  Permissions                                        │       │
│  ├─────────┼─────────────────────────────────────────────────────┤       │
│  │CITIZEN  │ • Create issues                                     │       │
│  │         │ • View own issues                                   │       │
│  │         │ • View public analytics                             │       │
│  ├─────────┼─────────────────────────────────────────────────────┤       │
│  │WORKER   │ • View assigned tasks                               │       │
│  │         │ • Accept/Start/Resolve tasks                        │       │
│  │         │ • View public analytics                             │       │
│  ├─────────┼─────────────────────────────────────────────────────┤       │
│  │ADMIN    │ • View all issues                                   │       │
│  │         │ • Assign workers                                    │       │
│  │         │ • Approve/Reject resolutions                        │       │
│  │         │ • Manage workers                                    │       │
│  ├─────────┼─────────────────────────────────────────────────────┤       │
│  │SYSADMIN │ • All ADMIN permissions                             │       │
│  │         │ • System configuration                              │       │
│  │         │ • Organization management                           │       │
│  │         │ • Global audit access                               │       │
│  └─────────┴─────────────────────────────────────────────────────┘       │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Data Protection

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    DATA PROTECTION MEASURES                               │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  IN TRANSIT                                                               │
│  ──────────                                                               │
│  • HTTPS enforced in production                                           │
│  • TLS 1.2+ for all API communications                                    │
│  • CORS configured for known origins only                                 │
│                                                                           │
│  AT REST                                                                  │
│  ───────                                                                  │
│  • PostgreSQL with encrypted connections                                  │
│  • MinIO with server-side encryption (production)                         │
│  • No plaintext credentials in codebase                                   │
│                                                                           │
│  INPUT VALIDATION                                                         │
│  ────────────────                                                         │
│  • Pydantic schemas validate all API inputs                               │
│  • SQL injection prevented via SQLModel ORM                               │
│  • File upload restricted to image MIME types                             │
│  • Coordinate validation (lat: -90 to 90, lng: -180 to 180)              │
│                                                                           │
│  AUDIT TRAIL                                                              │
│  ───────────                                                              │
│  • Every mutation logged with actor, timestamp, old/new values            │
│  • Immutable audit log (append-only)                                      │
│  • Supports forensic investigation                                        │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Frontend Architecture

### 8.1 Component Hierarchy

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    FRONTEND COMPONENT ARCHITECTURE                        │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  src/                                                                     │
│  ├── main.jsx                 # Application entry point                   │
│  ├── App.jsx                  # Router configuration                      │
│  │                                                                        │
│  ├── pages/                   # Route-level components                    │
│  │   ├── Login.jsx            # Authentication page                       │
│  │   ├── AnalyticsDashboard.jsx                                          │
│  │   │                                                                    │
│  │   ├── citizen/                                                         │
│  │   │   ├── CitizenHome.jsx  # Dashboard with navigation                │
│  │   │   ├── ReportIssue.jsx  # 3-step issue submission                  │
│  │   │   └── MyReports.jsx    # Issue tracking view                      │
│  │   │                                                                    │
│  │   ├── authority/                                                       │
│  │   │   └── AuthorityDashboard.jsx  # Map, Kanban, Workers              │
│  │   │                                                                    │
│  │   ├── worker/                                                          │
│  │   │   └── WorkerHome.jsx   # Task list, map, history                  │
│  │   │                                                                    │
│  │   └── admin/                                                           │
│  │       └── AdminDashboard.jsx  # System overview                       │
│  │                                                                        │
│  ├── components/              # Reusable UI components                    │
│  │   ├── LocateControl.jsx    # GPS location button for maps             │
│  │   ├── SearchField.jsx      # Geocoding search for maps                │
│  │   ├── HeatmapLayer.jsx     # Leaflet heatmap integration              │
│  │   ├── EvidenceGallery.jsx  # Before/after image viewer               │
│  │   └── PrivateRoute.jsx     # Auth-protected route wrapper             │
│  │                                                                        │
│  ├── services/                # API and utility services                  │
│  │   ├── api.js               # Axios instance configuration             │
│  │   ├── auth.js              # JWT storage, logout, role check          │
│  │   └── offline.js           # IndexedDB for offline support            │
│  │                                                                        │
│  └── utils/                                                               │
│      └── utils.js             # cn() classname merger utility            │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### 8.2 State Management

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    STATE MANAGEMENT STRATEGY                              │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  LOCAL STATE (useState)                                                   │
│  ─────────────────────                                                    │
│  Used for:                                                                │
│  • Form inputs                                                            │
│  • UI toggles (modals, tabs)                                              │
│  • Loading states                                                         │
│  • Component-specific data                                                │
│                                                                           │
│  CONTEXT/ZUSTAND (Global State)                                           │
│  ──────────────────────────────                                           │
│  Used for:                                                                │
│  • Authentication state                                                   │
│  • User preferences                                                       │
│  • Theme settings                                                         │
│                                                                           │
│  SERVER STATE (API Calls)                                                 │
│  ────────────────────────                                                 │
│  Pattern:                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │  useEffect(() => {                                           │         │
│  │    setLoading(true);                                         │         │
│  │    api.get('/endpoint')                                      │         │
│  │      .then(res => setData(res.data))                         │         │
│  │      .catch(err => setError(err))                            │         │
│  │      .finally(() => setLoading(false));                      │         │
│  │  }, [dependencies]);                                         │         │
│  └─────────────────────────────────────────────────────────────┘         │
│                                                                           │
│  JWT STORAGE                                                              │
│  ───────────                                                              │
│  • Token stored in localStorage                                           │
│  • Axios interceptor attaches Bearer header                               │
│  • Logout clears storage and redirects                                    │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### 8.3 Map Integration Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    LEAFLET MAP INTEGRATION                                │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  COMPONENT STACK                                                          │
│  ───────────────                                                          │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │  MapContainer                                                │         │
│  │  ├── TileLayer (CartoDB Voyager)                            │         │
│  │  ├── Marker / MarkerCluster                                 │         │
│  │  ├── Popup (Issue details)                                  │         │
│  │  ├── HeatmapLayer (Custom component)                        │         │
│  │  ├── LocateControl (GPS button)                             │         │
│  │  └── SearchField (Geocoding)                                │         │
│  └─────────────────────────────────────────────────────────────┘         │
│                                                                           │
│  TILE PROVIDER                                                            │
│  ─────────────                                                            │
│  URL: https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}  │
│  Subdomains: a, b, c, d                                                   │
│  Attribution: OpenStreetMap + CARTO                                       │
│                                                                           │
│  HEATMAP IMPLEMENTATION                                                   │
│  ─────────────────────                                                    │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │  // HeatmapLayer.jsx                                         │         │
│  │  import L from 'leaflet';                                    │         │
│  │  import 'leaflet.heat';                                      │         │
│  │                                                              │         │
│  │  useEffect(() => {                                           │         │
│  │    const heatData = points.map(p =>                          │         │
│  │      [p.lat, p.lng, p.intensity]                             │         │
│  │    );                                                        │         │
│  │    L.heatLayer(heatData, {                                   │         │
│  │      radius: 25,                                             │         │
│  │      blur: 15,                                               │         │
│  │      maxZoom: 17                                             │         │
│  │    }).addTo(map);                                            │         │
│  │  }, [points, map]);                                          │         │
│  └─────────────────────────────────────────────────────────────┘         │
│                                                                           │
│  GEOLOCATION                                                              │
│  ───────────                                                              │
│  • Uses browser Geolocation API                                           │
│  • Fallback to Hyderabad center: [17.4447, 78.3483]                      │
│  • "Get Current Location" triggers map.locate()                           │
│  • Adds marker with "You are here" popup                                  │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Integration Architecture

### 9.1 External System Integrations

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    INTEGRATION POINTS                                     │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │                     MINIO OBJECT STORAGE                         │     │
│  ├─────────────────────────────────────────────────────────────────┤     │
│  │  Protocol:    S3-Compatible API                                  │     │
│  │  Endpoint:    localhost:9000 (configurable)                      │     │
│  │  Auth:        Access Key + Secret Key                            │     │
│  │  Bucket:      infrastructure-evidence                            │     │
│  │                                                                   │     │
│  │  Operations:                                                      │     │
│  │  • PUT: Upload before/after images                                │     │
│  │  • GET: Retrieve images for display                               │     │
│  │  • DELETE: Remove images on issue deletion                        │     │
│  │                                                                   │     │
│  │  Path Structure:                                                  │     │
│  │  issues/{uuid}/before.jpg                                         │     │
│  │  issues/{uuid}/after.jpg                                          │     │
│  └─────────────────────────────────────────────────────────────────┘     │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │                     SMTP EMAIL SERVICE                           │     │
│  ├─────────────────────────────────────────────────────────────────┤     │
│  │  Protocol:    SMTP with STARTTLS                                 │     │
│  │  Port:        587                                                 │     │
│  │  Provider:    Configurable (Gmail, SendGrid, etc.)               │     │
│  │                                                                   │     │
│  │  DEV MODE:                                                        │     │
│  │  • Skips actual email sending                                     │     │
│  │  • Prints OTP to console                                          │     │
│  │  • Enables rapid testing without email setup                      │     │
│  └─────────────────────────────────────────────────────────────────┘     │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │                     GEOCODING SERVICE                            │     │
│  ├─────────────────────────────────────────────────────────────────┤     │
│  │  Provider:    Nominatim (OpenStreetMap)                          │     │
│  │  Library:     leaflet-control-geocoder                           │     │
│  │  Usage:       Address search on maps                              │     │
│  │  Rate Limit:  1 request/second (OSM policy)                      │     │
│  └─────────────────────────────────────────────────────────────────┘     │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │                     BROWSER GEOLOCATION                          │     │
│  ├─────────────────────────────────────────────────────────────────┤     │
│  │  API:         navigator.geolocation                               │     │
│  │  Usage:       Get user's current position                         │     │
│  │  Fallback:    Default to Hyderabad coordinates                   │     │
│  │  Privacy:     User must grant permission                          │     │
│  └─────────────────────────────────────────────────────────────────┘     │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### 9.2 API Communication Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    FRONTEND-BACKEND COMMUNICATION                         │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│   React Component                                                         │
│        │                                                                  │
│        ▼                                                                  │
│   ┌─────────────────────────────────────────────────────────┐            │
│   │  Axios Instance (services/api.js)                        │            │
│   │  ─────────────────────────────────                       │            │
│   │  baseURL: http://localhost:8088/api/v1                   │            │
│   │                                                          │            │
│   │  Request Interceptor:                                    │            │
│   │  • Attach Authorization: Bearer {token}                  │            │
│   │  • Set Content-Type                                      │            │
│   │                                                          │            │
│   │  Response Interceptor:                                   │            │
│   │  • Handle 401 → Redirect to login                        │            │
│   │  • Transform error responses                             │            │
│   └──────────────────────────┬──────────────────────────────┘            │
│                              │                                            │
│                              ▼                                            │
│   ┌─────────────────────────────────────────────────────────┐            │
│   │  FastAPI Application                                     │            │
│   │  ────────────────────                                    │            │
│   │                                                          │            │
│   │  Middleware Stack:                                       │            │
│   │  1. CORSMiddleware (allow frontend origin)               │            │
│   │  2. Request logging                                      │            │
│   │                                                          │            │
│   │  Dependency Injection:                                   │            │
│   │  • get_db() → SQLModel Session                           │            │
│   │  • get_current_user() → JWT verification                 │            │
│   └─────────────────────────────────────────────────────────┘            │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Deployment Architecture

### 10.1 Development Environment

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    DEVELOPMENT SETUP                                      │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │                     Docker Compose                               │     │
│  │  ┌──────────────────┐    ┌──────────────────┐                   │     │
│  │  │   PostgreSQL     │    │      MinIO       │                   │     │
│  │  │   + PostGIS      │    │                  │                   │     │
│  │  │   Port: 5432     │    │   Port: 9000     │                   │     │
│  │  │                  │    │   Console: 9001  │                   │     │
│  │  └──────────────────┘    └──────────────────┘                   │     │
│  └─────────────────────────────────────────────────────────────────┘     │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │                     Local Processes                               │    │
│  │  ┌──────────────────┐    ┌──────────────────┐                    │    │
│  │  │   Backend        │    │    Frontend      │                    │    │
│  │  │   (Uvicorn)      │    │    (Vite Dev)    │                    │    │
│  │  │   Port: 8088     │    │    Port: 5173    │                    │    │
│  │  │                  │    │    HMR enabled   │                    │    │
│  │  └──────────────────┘    └──────────────────┘                    │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│                                                                           │
│  COMMANDS:                                                                │
│  ─────────                                                                │
│  # Start databases                                                        │
│  docker-compose up -d                                                     │
│                                                                           │
│  # Backend                                                                │
│  cd backend && source ../venv/bin/activate                               │
│  uvicorn app.main:app --port 8088 --reload                               │
│                                                                           │
│  # Frontend                                                               │
│  cd frontend && npm run dev                                               │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### 10.2 Production Architecture (Recommended)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    PRODUCTION DEPLOYMENT                                  │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│                         ┌────────────────┐                                │
│                         │   CloudFlare   │                                │
│                         │   (CDN + WAF)  │                                │
│                         └───────┬────────┘                                │
│                                 │                                         │
│                                 ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │                     Load Balancer (Nginx)                        │     │
│  └───────────────────────────┬─────────────────────────────────────┘     │
│                              │                                            │
│              ┌───────────────┼───────────────┐                           │
│              │               │               │                            │
│              ▼               ▼               ▼                            │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐                │
│  │  API Server 1  │ │  API Server 2  │ │  API Server N  │                │
│  │  (Gunicorn +   │ │  (Gunicorn +   │ │  (Gunicorn +   │                │
│  │   Uvicorn)     │ │   Uvicorn)     │ │   Uvicorn)     │                │
│  └───────┬────────┘ └───────┬────────┘ └───────┬────────┘                │
│          │                  │                  │                          │
│          └──────────────────┼──────────────────┘                          │
│                             │                                             │
│              ┌──────────────┼──────────────┐                             │
│              │              │              │                              │
│              ▼              ▼              ▼                              │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐                │
│  │   PostgreSQL   │ │     MinIO      │ │     Redis      │                │
│  │   (Primary +   │ │   (Cluster)    │ │   (Sessions/   │                │
│  │    Replica)    │ │                │ │    Cache)      │                │
│  └────────────────┘ └────────────────┘ └────────────────┘                │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │                     Static Assets (S3/CDN)                       │     │
│  │  • React build artifacts                                         │     │
│  │  • Served via CloudFlare                                         │     │
│  └─────────────────────────────────────────────────────────────────┘     │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 11. Data Flow Diagrams

### 11.1 Issue Reporting Flow (End-to-End)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    ISSUE REPORTING - COMPLETE FLOW                        │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────┐                                                             │
│  │ Citizen │                                                             │
│  │ Browser │                                                             │
│  └────┬────┘                                                             │
│       │                                                                   │
│       │ 1. Open Report Page                                               │
│       ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │  STEP 1: LOCATION SELECTION                                      │     │
│  │  • Browser requests geolocation permission                       │     │
│  │  • User sees map centered on current location                    │     │
│  │  • User can adjust marker or search address                      │     │
│  │  • Coordinates captured: {lat, lng}                              │     │
│  └────────────────────────────┬────────────────────────────────────┘     │
│                               │                                           │
│                               │ 2. Proceed to Photo                       │
│                               ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │  STEP 2: PHOTO CAPTURE                                           │     │
│  │  • Camera input or file upload                                   │     │
│  │  • Image preview displayed                                       │     │
│  │  • File stored in memory (not uploaded yet)                      │     │
│  └────────────────────────────┬────────────────────────────────────┘     │
│                               │                                           │
│                               │ 3. Proceed to Details                     │
│                               ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │  STEP 3: CATEGORY & DESCRIPTION                                  │     │
│  │  • Select from: Pothole, Drainage, Street Light, Garbage         │     │
│  │  • Optional description text                                     │     │
│  │  • Submit button triggers API call                               │     │
│  └────────────────────────────┬────────────────────────────────────┘     │
│                               │                                           │
│                               │ 4. POST /api/v1/issues/report             │
│                               │    (multipart/form-data)                  │
│                               ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │  BACKEND PROCESSING                                              │     │
│  │                                                                   │     │
│  │  ┌─────────────┐                                                 │     │
│  │  │ Parse Form  │───▶ Extract: category_id, lat, lng, photo,     │     │
│  │  │             │      description, reporter_email                │     │
│  │  └─────────────┘                                                 │     │
│  │         │                                                         │     │
│  │         ▼                                                         │     │
│  │  ┌─────────────┐                                                 │     │
│  │  │ EXIF Extract│───▶ Read GPS from image metadata                │     │
│  │  │             │     (Pillow library)                            │     │
│  │  └─────────────┘                                                 │     │
│  │         │                                                         │     │
│  │         ▼                                                         │     │
│  │  ┌─────────────┐                                                 │     │
│  │  │ MinIO Upload│───▶ PUT issues/{uuid}/before.jpg                │     │
│  │  │             │                                                 │     │
│  │  └─────────────┘                                                 │     │
│  │         │                                                         │     │
│  │         ▼                                                         │     │
│  │  ┌─────────────┐                                                 │     │
│  │  │ Create Issue│───▶ INSERT INTO issue (                         │     │
│  │  │  in DB      │       id, category_id, reporter_email,          │     │
│  │  │             │       location = ST_MakePoint(lng, lat),        │     │
│  │  │             │       status = 'REPORTED', ...                  │     │
│  │  └─────────────┘     )                                           │     │
│  │         │                                                         │     │
│  │         ▼                                                         │     │
│  │  ┌─────────────┐                                                 │     │
│  │  │ Audit Log   │───▶ INSERT INTO audit_log (                     │     │
│  │  │             │       action='ISSUE_CREATED', ...               │     │
│  │  └─────────────┘     )                                           │     │
│  │         │                                                         │     │
│  │         ▼                                                         │     │
│  │  Return: { issue_id, status: "success" }                         │     │
│  └─────────────────────────────────────────────────────────────────┘     │
│                               │                                           │
│                               │ 5. Response                               │
│                               ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │  FRONTEND COMPLETION                                             │     │
│  │  • Show success message                                          │     │
│  │  • Navigate to My Reports page                                   │     │
│  │  • Issue visible with "REPORTED" status                          │     │
│  └─────────────────────────────────────────────────────────────────┘     │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### 11.2 Issue Resolution Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    ISSUE RESOLUTION - COMPLETE FLOW                       │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  AUTHORITY ACTIONS                      WORKER ACTIONS                    │
│  ─────────────────                      ──────────────                    │
│                                                                           │
│  ┌──────────────────┐                                                    │
│  │ View Kanban Board│                                                    │
│  │ (REPORTED column)│                                                    │
│  └────────┬─────────┘                                                    │
│           │                                                               │
│           │ Select issues + Worker                                        │
│           ▼                                                               │
│  ┌──────────────────┐                                                    │
│  │ POST /admin/     │                                                    │
│  │ bulk-assign      │───────────────────────────────────────┐            │
│  └────────┬─────────┘                                       │            │
│           │                                                  │            │
│           │ DB: UPDATE issue SET                             │            │
│           │     worker_id = :id,                             │            │
│           │     status = 'ASSIGNED'                          │            │
│           │                                                  │            │
│           │ Audit: ASSIGNMENT action logged                  ▼            │
│           │                                       ┌──────────────────┐   │
│           │                                       │ Worker sees task │   │
│           │                                       │ in dashboard     │   │
│           │                                       └────────┬─────────┘   │
│           │                                                │              │
│           │                                                │ Accept       │
│           │                                                ▼              │
│           │                                       ┌──────────────────┐   │
│           │                                       │ POST /worker/    │   │
│           │                                       │ tasks/{id}/accept│   │
│           │                                       │ ?eta=30m         │   │
│           │                                       └────────┬─────────┘   │
│           │                                                │              │
│           │                                       DB: status='ACCEPTED'  │
│           │                                                │              │
│           │                                                │ Start Work   │
│           │                                                ▼              │
│           │                                       ┌──────────────────┐   │
│           │                                       │ POST /worker/    │   │
│           │                                       │ tasks/{id}/start │   │
│           │                                       └────────┬─────────┘   │
│           │                                                │              │
│           │                                       DB: status='IN_PROGRESS'│
│           │                                                │              │
│           │                                                │ Complete +   │
│           │                                                │ Photo Upload │
│           │                                                ▼              │
│           │                                       ┌──────────────────┐   │
│           │                                       │ POST /worker/    │   │
│           │                                       │ tasks/{id}/resolve│  │
│           │                                       │ (multipart)      │   │
│           │                                       └────────┬─────────┘   │
│           │                                                │              │
│           │                                       MinIO: Upload after.jpg │
│           │                                       DB: status='RESOLVED'   │
│           │                                                │              │
│           ▼                                                │              │
│  ┌──────────────────┐◀─────────────────────────────────────┘             │
│  │ Issue appears in │                                                     │
│  │ RESOLVED column  │                                                     │
│  └────────┬─────────┘                                                    │
│           │                                                               │
│           │ Review before/after                                           │
│           ▼                                                               │
│  ┌──────────────────┐                                                    │
│  │ Compare Images   │                                                    │
│  │ in Modal         │                                                    │
│  └────────┬─────────┘                                                    │
│           │                                                               │
│           ├───────────────────────────────────┐                          │
│           │ Approve                           │ Reject                   │
│           ▼                                   ▼                          │
│  ┌──────────────────┐               ┌──────────────────┐                 │
│  │ POST /admin/     │               │ POST /admin/     │                 │
│  │ approve          │               │ reject           │                 │
│  └────────┬─────────┘               │ ?reason=...      │                 │
│           │                         └────────┬─────────┘                 │
│           │                                  │                            │
│  DB: status='CLOSED'              DB: status='REJECTED'                  │
│  Audit: APPROVED                  Audit: REJECTED                        │
│           │                                  │                            │
│           ▼                                  ▼                            │
│  ┌──────────────────┐               Worker must re-resolve               │
│  │ Issue Archived   │                                                    │
│  │ (Success!)       │                                                    │
│  └──────────────────┘                                                    │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 12. Non-Functional Requirements

### 12.1 Performance Requirements

| Metric | Target | Measurement |
|--------|--------|-------------|
| API Response Time | < 200ms (p95) | Server-side latency |
| Page Load Time | < 3s (LCP) | Core Web Vitals |
| Map Tile Load | < 1s | Time to interactive |
| Image Upload | < 5s for 5MB | End-to-end |
| Concurrent Users | 1000+ | Simultaneous connections |

### 12.2 Scalability Considerations

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    SCALABILITY STRATEGIES                                 │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  HORIZONTAL SCALING                                                       │
│  ──────────────────                                                       │
│  • Stateless API design enables multiple backend instances               │
│  • Session state via JWT (no server-side sessions)                       │
│  • Database connection pooling with PgBouncer                            │
│                                                                           │
│  DATABASE OPTIMIZATION                                                    │
│  ─────────────────────                                                    │
│  • PostGIS spatial indexes (GiST) for location queries                   │
│  • Composite indexes on (status, created_at) for filtering               │
│  • Read replicas for analytics queries                                   │
│                                                                           │
│  CACHING STRATEGY                                                         │
│  ────────────────                                                         │
│  • Redis for frequently accessed data (categories, stats)               │
│  • CDN for static assets and map tiles                                   │
│  • Browser caching with proper Cache-Control headers                     │
│                                                                           │
│  STORAGE SCALING                                                          │
│  ───────────────                                                          │
│  • MinIO supports distributed mode                                        │
│  • Image compression before storage                                       │
│  • Lifecycle policies for old images                                      │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### 12.3 Availability & Reliability

| Aspect | Strategy |
|--------|----------|
| **Database** | Primary-replica setup with automatic failover |
| **API** | Multiple instances behind load balancer |
| **Storage** | MinIO erasure coding for data durability |
| **Monitoring** | Health check endpoints, alerting on failures |
| **Backup** | Daily database snapshots, MinIO versioning |

### 12.4 Maintainability

| Practice | Implementation |
|----------|----------------|
| **Code Organization** | Modular architecture with clear boundaries |
| **Documentation** | OpenAPI auto-generated from FastAPI |
| **Testing** | Unit tests (pytest), E2E tests (Playwright) |
| **Logging** | Structured logging with request correlation |
| **Configuration** | Environment-based with `.env` files |

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| **OTP** | One-Time Password - 6-digit code for authentication |
| **JWT** | JSON Web Token - Signed token for session management |
| **PostGIS** | PostgreSQL extension for geospatial data |
| **EXIF** | Exchangeable Image File Format - Image metadata |
| **MinIO** | S3-compatible object storage system |
| **SLA** | Service Level Agreement - Expected resolution time |
| **Heatmap** | Density visualization of issue locations |
| **Kanban** | Visual task management board |

---

## Appendix B: API Quick Reference

```
Authentication:
  POST /api/v1/auth/otp-request    → Request OTP
  POST /api/v1/auth/login          → Verify & get token

Citizen:
  POST /api/v1/issues/report       → Submit issue
  GET  /api/v1/issues/my-reports   → View own issues

Admin:
  GET  /api/v1/admin/issues        → List all issues
  GET  /api/v1/admin/workers       → List workers
  POST /api/v1/admin/bulk-assign   → Assign to worker
  POST /api/v1/admin/approve       → Approve resolution
  POST /api/v1/admin/reject        → Reject with reason

Worker:
  GET  /api/v1/worker/tasks        → Get assigned tasks
  POST /api/v1/worker/tasks/{id}/accept   → Accept task
  POST /api/v1/worker/tasks/{id}/resolve  → Submit proof

Analytics:
  GET  /api/v1/analytics/stats     → Dashboard stats
  GET  /api/v1/analytics/heatmap   → Heatmap data
```

---

**Document Control:**
- **Author:** System Architecture Team
- **Reviewers:** Development Team, Product Owner
- **Status:** Final
- **Classification:** Internal Use

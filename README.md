# Urban Infrastructure Reporting System

A full-stack application for reporting and managing city infrastructure issues (potholes, drainage problems, street lights, garbage) in Hyderabad, India. Built for GHMC (Greater Hyderabad Municipal Corporation).

## Features

- **Citizen Portal**: Report infrastructure issues with GPS location and photo evidence
- **Authority Dashboard**: View issues on map, assign to workers, approve resolutions
- **Worker Dashboard**: Accept assigned tasks, submit resolution proof
- **Analytics Dashboard**: Real-time city health metrics, heatmaps, and trends
- **Audit Trail**: Complete transparency with full mutation history

## Tech Stack

### Backend
- **FastAPI** - High-performance Python web framework
- **PostgreSQL + PostGIS** - Spatial database for geolocation data
- **SQLModel** - ORM with Pydantic integration
- **MinIO** - S3-compatible object storage for images
- **JWT** - Secure token-based authentication

### Frontend
- **React 18** + **Vite** - Modern frontend tooling
- **Tailwind CSS** - Utility-first styling
- **Leaflet** - Interactive maps with heatmap support
- **Recharts** - Data visualization
- **Framer Motion** - Smooth animations

## Prerequisites

- **Docker** and **Docker Compose** (for PostgreSQL + PostGIS and MinIO)
- **Python 3.12+**
- **Node.js 18+** and **npm**

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/AryamaVMurthy/Road-Infra_app-demo.git
cd Road-Infra_app-demo
```

### 2. Start Database Services

```bash
docker-compose up -d
```

This starts:
- PostgreSQL with PostGIS on port `5432`
- MinIO object storage on ports `9000` (API) and `9001` (Console)

### 3. Setup Backend

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
cd backend
pip install -r requirements.txt

# Initialize database (creates tables and seed data)
python seed.py

# Start backend server
uvicorn app.main:app --host 0.0.0.0 --port 8088
```

The backend API will be available at `http://localhost:8088`

### 4. Setup Frontend

In a new terminal:

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173`

## Environment Configuration

### Backend (`backend/.env`)

Create a `.env` file in the backend directory (optional - defaults work for local development):

```env
# Database
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=toto
POSTGRES_DB=app

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=infrastructure-evidence

# JWT
SECRET_KEY=your-secret-key-change-in-production

# Development Mode (skips actual email sending, prints OTP to console)
DEV_MODE=True
```

### Frontend (`frontend/.env`)

```env
VITE_API_URL=http://localhost:8088/api/v1
```

## Test Users

In DEV_MODE, OTPs are printed to the backend console instead of being emailed.

| Email | Role | Dashboard |
|-------|------|-----------|
| `admin@ghmc.gov.in` | ADMIN | `/authority` |
| `worker@ghmc.gov.in` | WORKER | `/worker` |
| `resident@hyderabad.in` | CITIZEN | `/citizen` |
| Any new email | CITIZEN | `/citizen` |

### Login Flow
1. Enter email on login page
2. Click "Request Access"
3. Check backend console for OTP: `[DEV MODE] Skipping email send. OTP for email@example.com: 123456`
4. Enter the 6-digit OTP
5. You'll be redirected to your role-based dashboard

## API Endpoints

### Authentication
- `POST /api/v1/auth/otp-request` - Request OTP
- `POST /api/v1/auth/login` - Verify OTP and get JWT

### Issues
- `POST /api/v1/issues/report` - Report new issue (multipart form)
- `GET /api/v1/issues/my-reports?email=` - Get user's reports

### Admin
- `GET /api/v1/admin/issues` - List all issues
- `GET /api/v1/admin/workers` - List all workers
- `POST /api/v1/admin/bulk-assign` - Assign issues to worker
- `POST /api/v1/admin/approve` - Approve resolved issue
- `POST /api/v1/admin/reject` - Reject with reason

### Worker
- `GET /api/v1/worker/tasks` - Get assigned tasks
- `POST /api/v1/worker/tasks/{id}/accept` - Accept task with ETA
- `POST /api/v1/worker/tasks/{id}/resolve` - Submit resolution proof

### Analytics (Public)
- `GET /api/v1/analytics/stats` - Dashboard statistics
- `GET /api/v1/analytics/heatmap` - Issue heatmap data
- `GET /api/v1/analytics/issues-public` - Public issue list

### Media
- `GET /api/v1/media/{issue_id}/before` - Before image
- `GET /api/v1/media/{issue_id}/after` - After image

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API route handlers
│   │   ├── core/            # Config, security, database
│   │   ├── models/          # SQLModel domain models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   └── services/        # Business logic services
│   ├── seed.py              # Database seeder
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/           # Route pages by role
│   │   │   ├── citizen/     # Citizen dashboard pages
│   │   │   ├── authority/   # Admin dashboard pages
│   │   │   ├── worker/      # Worker dashboard pages
│   │   │   └── admin/       # Sysadmin pages
│   │   └── services/        # API client, auth
│   └── package.json
├── docker-compose.yml       # PostgreSQL + MinIO
└── README.md
```

## Issue Lifecycle

```
REPORTED → ASSIGNED → ACCEPTED → IN_PROGRESS → RESOLVED → CLOSED
    ↓         ↓                       ↓            ↓
 (Citizen)  (Admin)     ←←←←←←   (Worker)     (Admin approves)
```

1. **REPORTED**: Citizen submits issue with photo and GPS
2. **ASSIGNED**: Authority assigns to field worker
3. **ACCEPTED**: Worker accepts with ETA
4. **IN_PROGRESS**: Worker starts on-site work
5. **RESOLVED**: Worker submits "after" photo proof
6. **CLOSED**: Authority approves resolution

## Development

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Building for Production

```bash
# Frontend build
cd frontend
npm run build

# The dist/ folder can be served by any static file server
```

## Troubleshooting

### Database Connection Issues
```bash
# Check if PostgreSQL is running
docker-compose ps

# View logs
docker-compose logs db
```

### MinIO Issues
```bash
# Access MinIO Console at http://localhost:9001
# Login: minioadmin / minioadmin

# Create bucket manually if needed
```

### OTP Not Received
- In DEV_MODE, OTPs are printed to the backend console, not emailed
- Check backend terminal output for: `[DEV MODE] Skipping email send. OTP for email: 123456`

## License

MIT License - See LICENSE file for details.

## Contributors

Built for DASS (Design and Analysis of Software Systems) course project.

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import api_router
from app.core.config import settings
from app.core.middleware import SecurityHeadersMiddleware
from app.schemas.common import RootResponse

from app.services.minio_client import init_minio

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

OPENAPI_TAGS = [
    {"name": "auth", "description": "Authentication, OTP login, token refresh, and session inspection."},
    {"name": "categories", "description": "Public issue category lookup used by citizens and admins."},
    {"name": "issues", "description": "Citizen issue reporting and personal report history."},
    {"name": "admin", "description": "Shared administrative routes available to admins or sysadmins."},
    {"name": "admin-analytics", "description": "Authority dashboard analytics and operational summary metrics."},
    {"name": "admin-assignments", "description": "Issue assignment, reassignment, and queue control endpoints."},
    {"name": "admin-issues", "description": "Issue workflow operations such as approval, rejection, and priority updates."},
    {"name": "admin-system", "description": "System-admin authority and issue-type management endpoints."},
    {"name": "admin-workers", "description": "Worker account administration, invitations, and staffing views."},
    {"name": "worker", "description": "Field-worker task acceptance, progress, and resolution APIs."},
    {"name": "media", "description": "Issue evidence file retrieval endpoints."},
    {"name": "analytics", "description": "Public analytics, heatmap, and audit-trail endpoints."},
    {"name": "meta", "description": "Operational metadata and service health landing routes."},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_minio()
    yield


app = FastAPI(
    title="MARG (Monitoring Application for Road Governance) API",
    description=(
        "Role-based civic issue management API for citizens, authorities, workers, and system administrators."
    ),
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
    docs_url="/api/v1/docs" if settings.DEV_MODE else None,
    redoc_url="/api/v1/redoc" if settings.DEV_MODE else None,
    openapi_tags=OPENAPI_TAGS,
)

app.add_middleware(SecurityHeadersMiddleware)

_default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3011",
    "http://127.0.0.1:3011",
]
cors_origins = (
    [str(o) for o in settings.BACKEND_CORS_ORIGINS]
    if settings.BACKEND_CORS_ORIGINS
    else _default_origins
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get(
    "/",
    response_model=RootResponse,
    tags=["meta"],
    summary="Get API landing metadata",
    description="Return the human-readable API landing message used to confirm the service is reachable.",
)
def root():
    return RootResponse(
        message="Welcome to the MARG (Monitoring Application for Road Governance) API"
    )

"""
Main API Router - V1

Organizes all API endpoints by domain:
- auth: Authentication (OTP, login)
- issues: Issue reporting and citizen views
- admin: Admin operations (split into sub-modules)
- worker: Worker task management
- media: File/media serving
- analytics: Public analytics endpoints
"""

from fastapi import APIRouter
from . import auth, issues, worker, media, analytics
from app.api.v1.admin import router as admin_router
from app.api.v1.admin.issues import get_categories

api_router = APIRouter()

# Core routes
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(issues.router, prefix="/issues", tags=["issues"])

# Admin routes (now modular)
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])

# Worker routes
api_router.include_router(worker.router, prefix="/worker", tags=["worker"])

# Media and analytics
api_router.include_router(media.router, prefix="/media", tags=["media"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])

# Public categories endpoint
api_router.get("/categories", tags=["categories"])(get_categories)

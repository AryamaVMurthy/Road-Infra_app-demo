"""
Main API Router - V1

Organizes all API endpoints by domain:
- auth: Authentication (OTP, login)
- categories: Public category lookup
- issues: Issue reporting and citizen views
- admin: Admin operations (split into sub-modules)
- worker: Worker task management
- media: File/media serving
- analytics: Public analytics endpoints
"""

from fastapi import APIRouter
from . import analytics, auth, categories, issues, media, worker
from app.api.v1.admin import router as admin_router

api_router = APIRouter()

# Core routes
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(issues.router, prefix="/issues", tags=["issues"])

# Admin routes (now modular)
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])

# Worker routes
api_router.include_router(worker.router, prefix="/worker", tags=["worker"])

# Media and analytics
api_router.include_router(media.router, prefix="/media", tags=["media"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])

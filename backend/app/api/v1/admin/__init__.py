"""
Admin API Routes Package

This package contains all admin-related API endpoints organized by domain:
- analytics.py - Statistics and reporting endpoints
- assignments.py - Issue assignment and reassignment
- issues.py - Issue management and workflow
- workers.py - Worker management
"""

from fastapi import APIRouter

from .analytics import router as analytics_router
from .assignments import router as assignments_router
from .issues import router as issues_router
from .workers import router as workers_router

# Create main admin router
router = APIRouter()

# Include sub-routers with prefixes
router.include_router(analytics_router, prefix="/analytics", tags=["admin-analytics"])
router.include_router(
    assignments_router, prefix="/assignments", tags=["admin-assignments"]
)
router.include_router(issues_router, prefix="/issues", tags=["admin-issues"])
router.include_router(workers_router, prefix="/workers", tags=["admin-workers"])

__all__ = ["router"]

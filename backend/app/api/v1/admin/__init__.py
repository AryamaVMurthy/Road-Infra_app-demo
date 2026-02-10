"""
Admin API Routes Package

This package contains all admin-related API endpoints organized by domain:
- analytics.py - Statistics and reporting endpoints
- assignments.py - Issue assignment and reassignment
- issues.py - Issue management and workflow
- system.py - SYSADMIN authority and issue-type administration
- workers.py - Worker management
"""

from fastapi import APIRouter

from .analytics import router as analytics_router
from .assignments import router as assignments_router
from .issues import router as issues_router
from .system import router as system_router
from .workers import router as workers_router
from .sysadmin import router as sysadmin_router

# Create main admin router
router = APIRouter()

router.include_router(analytics_router, tags=["admin-analytics"])
router.include_router(assignments_router, tags=["admin-assignments"])
router.include_router(issues_router, tags=["admin-issues"])
router.include_router(system_router, tags=["admin-system"])
router.include_router(workers_router, tags=["admin-workers"])
router.include_router(sysadmin_router, prefix="/sysadmin", tags=["sysadmin"])

__all__ = ["router"]

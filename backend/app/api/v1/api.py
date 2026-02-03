from fastapi import APIRouter
from . import auth, issues, admin, worker, media, analytics
from app.api.v1.admin import get_categories

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(issues.router, prefix="/issues", tags=["issues"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(worker.router, prefix="/worker", tags=["worker"])
api_router.include_router(media.router, prefix="/media", tags=["media"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.get("/categories", tags=["categories"])(get_categories)

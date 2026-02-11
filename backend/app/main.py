from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import api_router
from app.core.config import settings
from app.core.middleware import SecurityHeadersMiddleware

from app.services.minio_client import init_minio

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_minio()
    yield


app = FastAPI(
    title="MARG (Monitoring Application for Road Governance) API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
    docs_url="/api/v1/docs" if settings.DEV_MODE else None,
    redoc_url="/api/v1/redoc" if settings.DEV_MODE else None,
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


@app.get("/")
def root():
    return {
        "message": "Welcome to the MARG (Monitoring Application for Road Governance) API"
    }

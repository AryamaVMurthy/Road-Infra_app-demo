from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import api_router
from app.core.config import settings
from app.core.middleware import SecurityHeadersMiddleware

from app.services.minio_client import init_minio


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_minio()
    yield


app = FastAPI(
    title="MARG (Monitoring Application for Road Governance) API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)


# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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

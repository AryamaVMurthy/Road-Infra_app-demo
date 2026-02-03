from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import api_router
from app.core.config import settings

from app.services.minio_client import init_minio

app = FastAPI(
    title="Urban Infrastructure Issue Reporting API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)


@app.on_event("startup")
def on_startup():
    init_minio()


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
    return {"message": "Welcome to the Urban Infrastructure Issue Reporting API"}

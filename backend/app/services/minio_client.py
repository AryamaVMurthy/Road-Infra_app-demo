import logging

from minio import Minio
from minio.error import S3Error

from app.core.config import settings

logger = logging.getLogger(__name__)

minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE,
)


def init_minio():
    if not minio_client.bucket_exists(settings.MINIO_BUCKET):
        try:
            minio_client.make_bucket(settings.MINIO_BUCKET)
        except S3Error as exc:
            if exc.code == "BucketAlreadyOwnedByYou":
                logger.info(
                    "MinIO bucket already exists and is owned by this deployment",
                    extra={"bucket": settings.MINIO_BUCKET, "s3_code": exc.code},
                )
                return
            raise RuntimeError(
                f"Failed to initialize MinIO bucket '{settings.MINIO_BUCKET}': "
                f"{exc.code or 'unknown_s3_error'}"
            ) from exc

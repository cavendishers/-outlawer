from io import BytesIO

from minio import Minio
from minio.error import S3Error

from app.core.config import get_settings

settings = get_settings()


def get_minio_client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def ensure_bucket_exists() -> None:
    client = get_minio_client()
    found = client.bucket_exists(settings.minio_bucket)
    if not found:
        client.make_bucket(settings.minio_bucket)


def upload_bytes(object_name: str, content: bytes, content_type: str) -> None:
    client = get_minio_client()
    ensure_bucket_exists()
    client.put_object(
        settings.minio_bucket,
        object_name,
        BytesIO(content),
        len(content),
        content_type=content_type,
    )


def download_bytes(object_name: str) -> bytes:
    client = get_minio_client()
    ensure_bucket_exists()
    response = client.get_object(settings.minio_bucket, object_name)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def get_presigned_url(object_name: str) -> str | None:
    try:
        client = get_minio_client()
        ensure_bucket_exists()
        return client.presigned_get_object(settings.minio_bucket, object_name)
    except S3Error:
        return None

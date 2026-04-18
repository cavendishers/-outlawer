from fastapi import APIRouter
from kombu import Connection
from redis import Redis
from sqlalchemy import text

from app.api.deps import DbSession
from app.core.config import get_settings
from app.core.minio import ensure_bucket_exists

router = APIRouter()
settings = get_settings()


def check_database(db: DbSession) -> dict:
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "detail": "query ok"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "detail": str(exc)}


def check_object_storage() -> dict:
    try:
        ensure_bucket_exists()
        return {"status": "healthy", "detail": settings.minio_bucket}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "detail": str(exc)}


def check_redis() -> dict:
    try:
        client = Redis.from_url(settings.redis_url, socket_connect_timeout=3, socket_timeout=3)
        client.ping()
        return {"status": "healthy", "detail": settings.redis_url}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "detail": str(exc)}


def check_broker() -> dict:
    try:
        with Connection(settings.broker_url, connect_timeout=3) as conn:
            conn.connect()
        return {"status": "healthy", "detail": settings.broker_url}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "detail": str(exc)}


@router.get("/health")
def healthcheck(db: DbSession) -> dict:
    services = {
        "database": check_database(db),
        "object_storage": check_object_storage(),
        "redis": check_redis(),
        "broker": check_broker(),
    }
    overall = "healthy" if all(service["status"] == "healthy" for service in services.values()) else "degraded"
    return {"code": 0, "message": "ok", "data": {"status": overall, "services": services}}

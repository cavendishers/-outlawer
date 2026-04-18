import logging

from celery import Celery

from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging()
logger = logging.getLogger("outlawer.worker")

celery_app = Celery(
    "outlawer",
    broker=settings.broker_url,
    backend=settings.redis_url,
    include=["app.tasks.pipeline"],
)
celery_app.conf.task_routes = {
    "app.tasks.pipeline.process_note_task": {"queue": "knowledge"},
}
celery_app.conf.task_track_started = True

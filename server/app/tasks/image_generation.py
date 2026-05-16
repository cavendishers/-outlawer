import logging

from app.core.celery import celery_app
from app.core.database import SessionLocal
from app.domains.image_generation.service import mark_image_generation_failed, process_image_generation

logger = logging.getLogger("outlawer.worker.image_generation")


@celery_app.task(name="app.tasks.image_generation.process_image_generation_task")
def process_image_generation_task(job_id: str) -> None:
    db = SessionLocal()
    try:
        logger.info("process_image_generation_task_started job_id=%s", job_id)
        process_image_generation(db, job_id)
        logger.info("process_image_generation_task_completed job_id=%s", job_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("process_image_generation_task_failed job_id=%s error=%s", job_id, exc)
        mark_image_generation_failed(db, job_id, str(exc))
        raise
    finally:
        db.close()

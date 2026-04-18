import logging

from app.core.celery import celery_app
from app.core.database import SessionLocal
from app.services.pipeline_service import mark_job_failed, process_note

logger = logging.getLogger("outlawer.worker.pipeline")


@celery_app.task(name="app.tasks.pipeline.process_note_task")
def process_note_task(job_id: str) -> None:
    db = SessionLocal()
    try:
        logger.info("process_note_task_started job_id=%s", job_id)
        process_note(db, job_id)
        logger.info("process_note_task_completed job_id=%s", job_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("process_note_task_failed job_id=%s error=%s", job_id, exc)
        mark_job_failed(db, job_id, str(exc))
        raise
    finally:
        db.close()

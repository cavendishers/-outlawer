from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.ai_job import AIJob
from app.models.extraction import ExtractionRun
from app.models.note import Note
from app.models.raw_asset import RawAsset
from app.services.asset_text_service import get_asset_text
from app.domains.extraction.metadata import resolve_extraction_run_metadata
from app.domains.replay.service import (
    list_extraction_runs,
    log_replay_action,
    mark_extraction_run_applied,
    PROJECTION_STATUS_FAILED,
    PROJECTION_STATUS_PENDING_REVIEW,
    PROJECTION_STATUS_APPLIED,
    resolve_applied_run_id,
    RUN_STATUS_COMPLETED,
    RUN_STATUS_READY_FOR_REVIEW,
)
from app.domains.extraction.extractor import build_extraction_payload
from app.services.projection_service import persist_extraction_projection


JOB_STATUS_PENDING = "pending"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_FAILED = "failed"


NOTE_STATUS_PROCESSING = "processing"
NOTE_STATUS_FAILED = "failed"


def process_note(db: Session, job_id: str) -> None:
    job = db.get(AIJob, job_id)
    if not job:
        raise ValueError(f"AI job {job_id} not found")

    note = db.get(Note, job.target_id)
    if not note:
        raise ValueError(f"Note {job.target_id} not found")

    asset = db.get(RawAsset, note.asset_id) if note.asset_id else None
    if not asset:
        raise ValueError("Associated asset not found")

    job.status = JOB_STATUS_RUNNING
    note.status = NOTE_STATUS_PROCESSING
    db.add_all([job, note])
    db.commit()

    text = get_asset_text(asset, db)
    if not text:
        raise ValueError("No text available for processing")

    payload = build_extraction_payload(note.id, asset.id, text)
    db.flush()
    is_reprocess = bool(job.payload_json.get("reprocess"))
    previous_applied_run_id = resolve_applied_run_id(list_extraction_runs(db, user_id=note.user_id, note_id=note.id))
    run_kind = "reprocess" if is_reprocess else "initial"
    run_metadata = resolve_extraction_run_metadata(
        payload,
        text=text,
        parent_run_id=previous_applied_run_id,
        run_kind=run_kind,
    )

    extraction_run = ExtractionRun(
        user_id=note.user_id,
        note_id=note.id,
        source_asset_id=asset.id,
        raw_result_json=payload,
        normalized_result_json=payload,
        status=RUN_STATUS_READY_FOR_REVIEW if is_reprocess and previous_applied_run_id else RUN_STATUS_COMPLETED,
        extractor_name=payload["source"]["extractor_name"],
        extractor_version=payload["source"]["extractor_version"],
        provider_name=str(run_metadata["provider_name"]),
        model_name=str(run_metadata["model_name"]),
        prompt_version=str(run_metadata["prompt_version"]),
        schema_version=str(run_metadata["schema_version"]),
        input_hash=str(run_metadata["input_hash"]),
        parent_run_id=run_metadata["parent_run_id"],
        run_kind=str(run_metadata["run_kind"]),
        projection_status=PROJECTION_STATUS_PENDING_REVIEW if is_reprocess and previous_applied_run_id else PROJECTION_STATUS_APPLIED,
    )
    db.add(extraction_run)
    db.flush()
    if extraction_run.status == RUN_STATUS_READY_FOR_REVIEW:
        note.status = "ready"
        db.add(note)
        projection_result = None
    else:
        projection_result = persist_extraction_projection(
            db,
            note=note,
            asset=asset,
            payload=payload,
            text=text,
        )
        mark_extraction_run_applied(db, user_id=note.user_id, note_id=note.id, run_id=extraction_run.id)
        log_replay_action(
            db,
            user_id=note.user_id,
            note_id=note.id,
            run=extraction_run,
            action_type="auto_apply_extraction_run",
            previous_run_id=previous_applied_run_id,
            projection_version_id=note.active_projection_id,
            previous_projection_version_id=None,
        )

    job.status = JOB_STATUS_COMPLETED
    job.result_json = (
        {
            "note_id": note.id,
            "event_id": projection_result.event_id,
            "extractor_name": projection_result.extractor_name,
            "extractor_version": projection_result.extractor_version,
            "entity_count": projection_result.entity_count,
            "relation_count": projection_result.relation_count,
            "similarity_hint_count": projection_result.similarity_hint_count,
            "run_id": extraction_run.id,
            "requires_review": False,
        }
        if projection_result is not None
        else {
            "note_id": note.id,
            "run_id": extraction_run.id,
            "extractor_name": extraction_run.extractor_name,
            "extractor_version": extraction_run.extractor_version,
            "requires_review": True,
            "review_status": extraction_run.status,
        }
    )
    job.finished_at = datetime.now(UTC)
    db.add(job)
    db.commit()


def mark_job_failed(db: Session, job_id: str, message: str) -> None:
    db.rollback()
    job = db.get(AIJob, job_id)
    note = db.get(Note, job.target_id) if job else None
    run = None
    if note and note.user_id:
        runs = list_extraction_runs(db, user_id=note.user_id, note_id=note.id)
        run = runs[0] if runs else None
    if job:
        job.status = JOB_STATUS_FAILED
        job.error_message = message
        db.add(job)
    if note:
        note.status = NOTE_STATUS_FAILED
        db.add(note)
    if run and run.status == RUN_STATUS_READY_FOR_REVIEW:
        run.projection_status = PROJECTION_STATUS_PENDING_REVIEW
        db.add(run)
    elif run:
        run.projection_status = PROJECTION_STATUS_FAILED
        db.add(run)
    db.commit()

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.replay.diff import compare_extraction_payloads, safe_string, serialize_datetime, summarize_run_payload
from app.models.extraction import ExtractionRun, ProjectionVersion
from app.models.note import Note
from app.models.raw_asset import RawAsset
from app.models.review import ReviewAction
from app.services.projection_service import ProjectionResult, persist_extraction_projection

RUN_STATUS_APPLIED = "applied"
RUN_STATUS_SUPERSEDED = "superseded"
RUN_STATUS_COMPLETED = "completed"
RUN_STATUS_READY_FOR_REVIEW = "ready_for_review"
RUN_STATUS_REJECTED = "rejected"
RUN_STATUS_FAILED = "failed"
MIN_DATETIME = datetime.min.replace(tzinfo=UTC)
REPLAY_ACTION_TYPES = {
    "apply_extraction_run",
    "auto_apply_extraction_run",
    "approve_extraction_run",
    "reject_extraction_run",
}
PROJECTION_STATUS_APPLIED = "applied"
PROJECTION_STATUS_SUPERSEDED = "superseded"
PROJECTION_STATUS_PENDING_REVIEW = "pending_review"
PROJECTION_STATUS_REJECTED = "rejected"
PROJECTION_STATUS_FAILED = "failed"
PROJECTION_STATUS_NOT_APPLIED = "not_applied"
APPLIED_FALLBACK_STATUSES = {RUN_STATUS_APPLIED, RUN_STATUS_SUPERSEDED, RUN_STATUS_COMPLETED}
ACTIVE_LINEAGE_STATUSES = {RUN_STATUS_APPLIED, RUN_STATUS_SUPERSEDED, RUN_STATUS_COMPLETED}


def serialize_extraction_run(run: ExtractionRun, *, applied_run_id: str | None = None) -> dict[str, Any]:
    projection_status = normalized_projection_status(run)
    return {
        "id": run.id,
        "note_id": run.note_id,
        "source_asset_id": run.source_asset_id,
        "status": run.status,
        "is_applied": is_applied_run(run, applied_run_id=applied_run_id),
        "extractor_name": run.extractor_name,
        "extractor_version": run.extractor_version,
        "provider_name": run.provider_name,
        "model_name": run.model_name,
        "prompt_version": run.prompt_version,
        "schema_version": run.schema_version,
        "input_hash": run.input_hash,
        "parent_run_id": run.parent_run_id,
        "run_kind": run.run_kind,
        "projection_status": projection_status,
        "created_at": serialize_datetime(run.created_at),
        "updated_at": serialize_datetime(run.updated_at),
        "summary": summarize_run_payload(run.normalized_result_json or {}),
    }


def list_extraction_runs(db: Session, *, user_id: str, note_id: str) -> list[ExtractionRun]:
    return list(
        db.scalars(
            select(ExtractionRun)
            .where(ExtractionRun.user_id == user_id, ExtractionRun.note_id == note_id)
            .order_by(ExtractionRun.created_at.desc())
        ).all()
    )


def list_note_replay_actions(db: Session, *, user_id: str, note_id: str, limit: int = 20) -> list[ReviewAction]:
    return list(
        db.scalars(
            select(ReviewAction)
            .where(
                ReviewAction.user_id == user_id,
                ReviewAction.target_type == "note",
                ReviewAction.target_id == note_id,
                ReviewAction.action_type.in_(sorted(REPLAY_ACTION_TYPES)),
            )
            .order_by(ReviewAction.created_at.desc())
            .limit(limit)
        ).all()
    )


def get_extraction_run(db: Session, *, user_id: str, note_id: str, run_id: str) -> ExtractionRun | None:
    return db.scalar(
        select(ExtractionRun).where(
            ExtractionRun.user_id == user_id,
            ExtractionRun.note_id == note_id,
            ExtractionRun.id == run_id,
        )
    )


def compare_extraction_runs(
    base_run: ExtractionRun,
    candidate_run: ExtractionRun,
    *,
    applied_run_id: str | None = None,
) -> dict[str, Any]:
    resolved_applied_run_id = applied_run_id or resolve_applied_run_id([base_run, candidate_run])
    diff = compare_extraction_payloads(
        base_run.normalized_result_json or {},
        candidate_run.normalized_result_json or {},
    )
    return {
        "note_id": base_run.note_id,
        "base_run": serialize_extraction_run(base_run, applied_run_id=resolved_applied_run_id),
        "candidate_run": serialize_extraction_run(candidate_run, applied_run_id=resolved_applied_run_id),
        "diff": diff,
    }


def resolve_applied_run_id(runs: list[ExtractionRun]) -> str | None:
    projection_applied_runs = [run for run in runs if normalized_projection_status(run) == PROJECTION_STATUS_APPLIED]
    if projection_applied_runs:
        projection_applied_runs.sort(key=lambda item: item.created_at or MIN_DATETIME, reverse=True)
        return projection_applied_runs[0].id

    applied_runs = [run for run in runs if run.status == RUN_STATUS_APPLIED]
    if applied_runs:
        applied_runs.sort(key=lambda item: item.created_at or MIN_DATETIME, reverse=True)
        return applied_runs[0].id

    successful_runs = [run for run in runs if run.status in APPLIED_FALLBACK_STATUSES]
    if not successful_runs:
        return None
    successful_runs.sort(key=lambda item: item.created_at or MIN_DATETIME, reverse=True)
    return successful_runs[0].id


def is_applied_run(run: ExtractionRun, *, applied_run_id: str | None) -> bool:
    if applied_run_id:
        return run.id == applied_run_id
    return run.status == RUN_STATUS_APPLIED


def mark_extraction_run_applied(db: Session, *, user_id: str, note_id: str, run_id: str) -> None:
    runs = list_extraction_runs(db, user_id=user_id, note_id=note_id)
    for run in runs:
        if run.id == run_id:
            run.status = RUN_STATUS_APPLIED
            run.projection_status = PROJECTION_STATUS_APPLIED
        elif run.status in ACTIVE_LINEAGE_STATUSES:
            run.status = RUN_STATUS_SUPERSEDED
            run.projection_status = PROJECTION_STATUS_SUPERSEDED
        db.add(run)


def apply_extraction_run_projection(
    db: Session,
    *,
    note: Note,
    asset: RawAsset,
    run: ExtractionRun,
    text: str,
    action_type: str = "apply_extraction_run",
    operator_note: str | None = None,
    status_before: str | None = None,
) -> ProjectionResult:
    previous_applied_run_id = resolve_applied_run_id(list_extraction_runs(db, user_id=note.user_id, note_id=note.id))
    previous_projection_id = note.active_projection_id
    payload = run.normalized_result_json or {}
    projection_result = persist_extraction_projection(
        db,
        note=note,
        asset=asset,
        payload=payload,
        text=text,
    )
    mark_extraction_run_applied(db, user_id=note.user_id, note_id=note.id, run_id=run.id)
    projection_version = create_projection_version(
        db,
        note=note,
        asset=asset,
        run=run,
        action_type=action_type,
        previous_projection_id=previous_projection_id,
        projection_result=projection_result,
    )
    note.active_projection_id = projection_version.id
    log_replay_action(
        db,
        user_id=note.user_id,
        note_id=note.id,
        run=run,
        action_type=action_type,
        previous_run_id=previous_applied_run_id,
        projection_version_id=projection_version.id,
        previous_projection_version_id=previous_projection_id,
        operator_note=operator_note,
        status_before=status_before,
    )
    db.flush()
    return projection_result


def approve_reviewable_extraction_run(
    db: Session,
    *,
    note: Note,
    asset: RawAsset,
    run: ExtractionRun,
    text: str,
    operator_note: str | None = None,
) -> ProjectionResult:
    if run.status != RUN_STATUS_READY_FOR_REVIEW:
        raise ValueError("Extraction run is not awaiting review")
    return apply_extraction_run_projection(
        db,
        note=note,
        asset=asset,
        run=run,
        text=text,
        action_type="approve_extraction_run",
        operator_note=operator_note,
        status_before=RUN_STATUS_READY_FOR_REVIEW,
    )


def reject_reviewable_extraction_run(
    db: Session,
    *,
    user_id: str,
    note_id: str,
    run: ExtractionRun,
    operator_note: str | None = None,
) -> ExtractionRun:
    if run.status != RUN_STATUS_READY_FOR_REVIEW:
        raise ValueError("Extraction run is not awaiting review")
    run.status = RUN_STATUS_REJECTED
    run.projection_status = PROJECTION_STATUS_REJECTED
    db.add(run)
    log_replay_action(
        db,
        user_id=user_id,
        note_id=note_id,
        run=run,
        action_type="reject_extraction_run",
        previous_run_id=resolve_applied_run_id(list_extraction_runs(db, user_id=user_id, note_id=note_id)),
        projection_version_id=None,
        previous_projection_version_id=None,
        operator_note=operator_note,
        status_before=RUN_STATUS_READY_FOR_REVIEW,
        status_after=RUN_STATUS_REJECTED,
    )
    db.flush()
    return run


def log_replay_action(
    db: Session,
    *,
    user_id: str,
    note_id: str,
    run: ExtractionRun,
    action_type: str,
    previous_run_id: str | None,
    projection_version_id: str | None,
    previous_projection_version_id: str | None,
    operator_note: str | None = None,
    status_before: str | None = None,
    status_after: str | None = None,
) -> ReviewAction:
    action = ReviewAction(
        user_id=user_id,
        target_type="note",
        target_id=note_id,
        action_type=action_type,
        status_before=status_before if status_before is not None else (RUN_STATUS_APPLIED if previous_run_id else None),
        status_after=status_after or RUN_STATUS_APPLIED,
        payload_json={
            "run_id": run.id,
            "previous_run_id": previous_run_id,
            "projection_version_id": projection_version_id,
            "previous_projection_version_id": previous_projection_version_id,
            "extractor_name": run.extractor_name,
            "extractor_version": run.extractor_version,
            "provider_name": run.provider_name,
            "model_name": run.model_name,
            "prompt_version": run.prompt_version,
            "schema_version": run.schema_version,
            "note": operator_note,
        },
    )
    db.add(action)
    db.flush()
    return action


def serialize_replay_action(action: ReviewAction) -> dict[str, Any]:
    payload = action.payload_json or {}
    return {
        "id": action.id,
        "action_type": action.action_type,
        "created_at": serialize_datetime(action.created_at),
        "status_before": action.status_before,
        "status_after": action.status_after,
        "run_id": safe_string(payload.get("run_id")),
        "previous_run_id": safe_string(payload.get("previous_run_id")) or None,
        "projection_version_id": safe_string(payload.get("projection_version_id")) or None,
        "previous_projection_version_id": safe_string(payload.get("previous_projection_version_id")) or None,
        "extractor_name": safe_string(payload.get("extractor_name")),
        "extractor_version": safe_string(payload.get("extractor_version")),
        "provider_name": safe_string(payload.get("provider_name")) or None,
        "model_name": safe_string(payload.get("model_name")) or None,
        "prompt_version": safe_string(payload.get("prompt_version")) or None,
        "schema_version": safe_string(payload.get("schema_version")) or None,
        "note": safe_string(payload.get("note")) or None,
    }


def normalized_projection_status(run: ExtractionRun) -> str:
    if run.projection_status:
        return run.projection_status
    if run.status == RUN_STATUS_APPLIED:
        return PROJECTION_STATUS_APPLIED
    if run.status == RUN_STATUS_SUPERSEDED:
        return PROJECTION_STATUS_SUPERSEDED
    if run.status == RUN_STATUS_READY_FOR_REVIEW:
        return PROJECTION_STATUS_PENDING_REVIEW
    if run.status == RUN_STATUS_REJECTED:
        return PROJECTION_STATUS_REJECTED
    if run.status == RUN_STATUS_FAILED:
        return PROJECTION_STATUS_FAILED
    return PROJECTION_STATUS_NOT_APPLIED


def create_projection_version(
    db: Session,
    *,
    note: Note,
    asset: RawAsset,
    run: ExtractionRun,
    action_type: str,
    previous_projection_id: str | None,
    projection_result: ProjectionResult,
) -> ProjectionVersion:
    version = ProjectionVersion(
        user_id=note.user_id,
        note_id=note.id,
        extraction_run_id=run.id,
        source_asset_id=asset.id,
        previous_projection_id=previous_projection_id,
        action_type=action_type,
        summary_json={
            "event_id": projection_result.event_id,
            "extractor_name": projection_result.extractor_name,
            "extractor_version": projection_result.extractor_version,
            "entity_count": projection_result.entity_count,
            "relation_count": projection_result.relation_count,
            "similarity_hint_count": projection_result.similarity_hint_count,
        },
    )
    db.add(version)
    db.flush()
    return version

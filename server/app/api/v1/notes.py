from fastapi import APIRouter, Depends, HTTPException, status

from app.api.serializers import serialize_note
from app.api.deps import DbSession, get_current_user
from app.core.pagination import normalize_page_params
from app.core.responses import ok, paginated
from app.models.ai_job import AIJob
from app.models.note import Note
from app.models.raw_asset import RawAsset
from app.schemas.common import CollectionData, Envelope, PaginatedData
from app.schemas.note import (
    ExtractionRunCompareResponse,
    ExtractionRunResponse,
    NoteCreateRequest,
    NoteCreateResponse,
    NoteExtractionRunApplyResponse,
    NoteExtractionRunApproveResponse,
    NoteExtractionRunRejectResponse,
    NoteReplayActionRequest,
    NoteResponse,
    ProjectionResultResponse,
    ReplayActionResponse,
)
from app.domains.retrieval import note_query
from app.services.asset_text_service import get_asset_text
from app.domains.replay.service import (
    RUN_STATUS_REJECTED,
    RUN_STATUS_READY_FOR_REVIEW,
    apply_extraction_run_projection,
    approve_reviewable_extraction_run,
    get_extraction_run,
    list_extraction_runs,
    list_note_replay_actions,
    reject_reviewable_extraction_run,
    resolve_applied_run_id,
    serialize_replay_action,
    serialize_extraction_run,
)
from app.services.job_dispatcher import dispatch_job

router = APIRouter()


@router.post("", response_model=Envelope[NoteCreateResponse])
def create_note(payload: NoteCreateRequest, db: DbSession, user=Depends(get_current_user)) -> dict:
    asset = db.get(RawAsset, payload.asset_id)
    if not asset or asset.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    note = Note(
        user_id=user.id,
        asset_id=asset.id,
        title=payload.title or asset.title,
        status="processing",
    )
    db.add(note)
    db.flush()

    job = AIJob(
        user_id=user.id,
        job_type="knowledge_pipeline",
        target_type="note",
        target_id=note.id,
        status="pending",
        payload_json={"asset_id": asset.id},
    )
    db.add(job)
    db.commit()
    db.refresh(note)
    db.refresh(job)
    dispatch_job(job)

    return ok({"note_id": note.id, "job_id": job.id})


@router.get("", response_model=Envelope[PaginatedData[NoteResponse]])
def list_notes(
    db: DbSession,
    page: int = 1,
    page_size: int = 20,
    user=Depends(get_current_user),
) -> dict:
    params = normalize_page_params(page, page_size)
    notes, total = note_query.list_notes(db, user_id=user.id, params=params)
    return paginated(
        items=notes,
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/{note_id}", response_model=Envelope[NoteResponse])
def get_note(note_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(note_query.get_note_detail(db, user_id=user.id, note_id=note_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")


@router.get("/{note_id}/extraction-runs", response_model=Envelope[CollectionData[ExtractionRunResponse]])
def list_note_extraction_runs(note_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(note_query.list_note_extraction_run_items(db, user_id=user.id, note_id=note_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")


@router.get("/{note_id}/extraction-runs/compare", response_model=Envelope[ExtractionRunCompareResponse])
def compare_note_extraction_runs(
    note_id: str,
    base_run_id: str,
    candidate_run_id: str,
    db: DbSession,
    user=Depends(get_current_user),
) -> dict:
    try:
        return ok(
            note_query.compare_note_extraction_runs(
                db,
                user_id=user.id,
                note_id=note_id,
                base_run_id=base_run_id,
                candidate_run_id=candidate_run_id,
            )
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if detail in {"Note not found", "Extraction run not found"} else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail) from exc


@router.get("/{note_id}/extraction-runs/{run_id}", response_model=Envelope[ExtractionRunResponse])
def get_note_extraction_run(note_id: str, run_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(note_query.get_note_extraction_run_detail(db, user_id=user.id, note_id=note_id, run_id=run_id))
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if detail in {"Note not found", "Extraction run not found"} else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail) from exc


@router.get("/{note_id}/replay-actions", response_model=Envelope[CollectionData[ReplayActionResponse]])
def list_note_replay_action_log(note_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(note_query.list_note_replay_action_items(db, user_id=user.id, note_id=note_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")


@router.post("/{note_id}/extraction-runs/{run_id}/apply", response_model=Envelope[NoteExtractionRunApplyResponse])
def apply_note_extraction_run(
    note_id: str,
    run_id: str,
    db: DbSession,
    payload: NoteReplayActionRequest | None = None,
    user=Depends(get_current_user),
) -> dict:
    note = db.get(Note, note_id)
    if not note or note.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    run = get_extraction_run(db, user_id=user.id, note_id=note.id, run_id=run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extraction run not found")
    if run.status in {RUN_STATUS_READY_FOR_REVIEW, RUN_STATUS_REJECTED}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This extraction run cannot be applied directly")
    asset_id = run.source_asset_id or note.asset_id
    asset = db.get(RawAsset, asset_id) if asset_id else None
    if not asset or asset.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source asset not found")
    text = get_asset_text(asset, db)
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No text available for replay")
    operator_note = None
    if payload is not None:
        operator_note = str(payload.note or "").strip() or None
    projection_result = apply_extraction_run_projection(
        db,
        note=note,
        asset=asset,
        run=run,
        text=text,
        operator_note=operator_note,
    )
    db.commit()
    db.refresh(note)
    refreshed_run = get_extraction_run(db, user_id=user.id, note_id=note.id, run_id=run.id)
    applied_run_id = resolve_applied_run_id(list_extraction_runs(db, user_id=user.id, note_id=note.id))
    return ok(
        {
            "note": serialize_note(note),
            "applied_run": serialize_extraction_run(refreshed_run or run, applied_run_id=applied_run_id),
            "projection_result": {
                "note_id": projection_result.note_id,
                "event_id": projection_result.event_id,
                "projection_version_id": note.active_projection_id,
                "extractor_name": projection_result.extractor_name,
                "extractor_version": projection_result.extractor_version,
                "entity_count": projection_result.entity_count,
                "relation_count": projection_result.relation_count,
                "similarity_hint_count": projection_result.similarity_hint_count,
            },
            "replay_actions": [serialize_replay_action(action) for action in list_note_replay_actions(db, user_id=user.id, note_id=note.id)],
        }
    )


@router.post("/{note_id}/extraction-runs/{run_id}/approve", response_model=Envelope[NoteExtractionRunApproveResponse])
def approve_note_extraction_run(
    note_id: str,
    run_id: str,
    db: DbSession,
    payload: NoteReplayActionRequest | None = None,
    user=Depends(get_current_user),
) -> dict:
    note = db.get(Note, note_id)
    if not note or note.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    run = get_extraction_run(db, user_id=user.id, note_id=note.id, run_id=run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extraction run not found")
    asset_id = run.source_asset_id or note.asset_id
    asset = db.get(RawAsset, asset_id) if asset_id else None
    if not asset or asset.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source asset not found")
    text = get_asset_text(asset, db)
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No text available for replay")
    operator_note = None
    if payload is not None:
        operator_note = str(payload.note or "").strip() or None
    try:
        projection_result = approve_reviewable_extraction_run(
            db,
            note=note,
            asset=asset,
            run=run,
            text=text,
            operator_note=operator_note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    db.refresh(note)
    refreshed_run = get_extraction_run(db, user_id=user.id, note_id=note.id, run_id=run.id)
    applied_run_id = resolve_applied_run_id(list_extraction_runs(db, user_id=user.id, note_id=note.id))
    return ok(
        {
            "note": serialize_note(note),
            "approved_run": serialize_extraction_run(refreshed_run or run, applied_run_id=applied_run_id),
            "projection_result": {
                "note_id": projection_result.note_id,
                "event_id": projection_result.event_id,
                "projection_version_id": note.active_projection_id,
                "extractor_name": projection_result.extractor_name,
                "extractor_version": projection_result.extractor_version,
                "entity_count": projection_result.entity_count,
                "relation_count": projection_result.relation_count,
                "similarity_hint_count": projection_result.similarity_hint_count,
            },
            "replay_actions": [serialize_replay_action(action) for action in list_note_replay_actions(db, user_id=user.id, note_id=note.id)],
        }
    )


@router.post("/{note_id}/extraction-runs/{run_id}/reject", response_model=Envelope[NoteExtractionRunRejectResponse])
def reject_note_extraction_run(
    note_id: str,
    run_id: str,
    db: DbSession,
    payload: NoteReplayActionRequest | None = None,
    user=Depends(get_current_user),
) -> dict:
    note = db.get(Note, note_id)
    if not note or note.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    run = get_extraction_run(db, user_id=user.id, note_id=note.id, run_id=run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extraction run not found")
    operator_note = None
    if payload is not None:
        operator_note = str(payload.note or "").strip() or None
    try:
        rejected_run = reject_reviewable_extraction_run(
            db,
            user_id=user.id,
            note_id=note.id,
            run=run,
            operator_note=operator_note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    applied_run_id = resolve_applied_run_id(list_extraction_runs(db, user_id=user.id, note_id=note.id))
    return ok(
        {
            "note": serialize_note(note),
            "rejected_run": serialize_extraction_run(rejected_run, applied_run_id=applied_run_id),
            "replay_actions": [serialize_replay_action(action) for action in list_note_replay_actions(db, user_id=user.id, note_id=note.id)],
        }
    )


@router.post("/{note_id}/reprocess", response_model=Envelope[NoteCreateResponse])
def reprocess_note(note_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    note = db.get(Note, note_id)
    if not note or note.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    job = AIJob(
        user_id=user.id,
        job_type="knowledge_pipeline",
        target_type="note",
        target_id=note.id,
        status="pending",
        payload_json={"note_id": note.id, "reprocess": True},
    )
    note.status = "processing"
    db.add_all([note, job])
    db.commit()
    db.refresh(job)
    dispatch_job(job)
    return ok({"note_id": note.id, "job_id": job.id})

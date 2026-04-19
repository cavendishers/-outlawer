from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.serializers import serialize_note
from app.api.deps import DbSession, get_current_user
from app.core.pagination import normalize_page_params, paginate_query
from app.core.responses import ok, paginated
from app.models.ai_job import AIJob
from app.models.note import Note
from app.models.raw_asset import RawAsset
from app.services.extraction_run_service import (
    compare_extraction_runs,
    get_extraction_run,
    list_extraction_runs,
    serialize_extraction_run,
)
from app.services.job_dispatcher import dispatch_job

router = APIRouter()


@router.post("")
def create_note(payload: dict, db: DbSession, user=Depends(get_current_user)) -> dict:
    asset_id = payload.get("asset_id")
    asset = db.get(RawAsset, asset_id)
    if not asset or asset.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    note = Note(
        user_id=user.id,
        asset_id=asset.id,
        title=payload.get("title") or asset.title,
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


@router.get("")
def list_notes(
    db: DbSession,
    page: int = 1,
    page_size: int = 20,
    user=Depends(get_current_user),
) -> dict:
    params = normalize_page_params(page, page_size)
    query = select(Note).where(Note.user_id == user.id).order_by(Note.created_at.desc())
    notes, total = paginate_query(db, query, params)
    return paginated(
        items=[serialize_note(note) for note in notes],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/{note_id}")
def get_note(note_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    note = db.get(Note, note_id)
    if not note or note.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return ok(serialize_note(note))


@router.get("/{note_id}/extraction-runs")
def list_note_extraction_runs(note_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    note = db.get(Note, note_id)
    if not note or note.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    runs = list_extraction_runs(db, user_id=user.id, note_id=note.id)
    return ok({"items": [serialize_extraction_run(run) for run in runs], "total": len(runs)})


@router.get("/{note_id}/extraction-runs/compare")
def compare_note_extraction_runs(
    note_id: str,
    base_run_id: str,
    candidate_run_id: str,
    db: DbSession,
    user=Depends(get_current_user),
) -> dict:
    note = db.get(Note, note_id)
    if not note or note.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    base_run = get_extraction_run(db, user_id=user.id, note_id=note.id, run_id=base_run_id)
    candidate_run = get_extraction_run(db, user_id=user.id, note_id=note.id, run_id=candidate_run_id)
    if not base_run or not candidate_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extraction run not found")
    return ok(compare_extraction_runs(base_run, candidate_run))


@router.get("/{note_id}/extraction-runs/{run_id}")
def get_note_extraction_run(note_id: str, run_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    note = db.get(Note, note_id)
    if not note or note.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    run = get_extraction_run(db, user_id=user.id, note_id=note.id, run_id=run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extraction run not found")
    return ok(serialize_extraction_run(run))


@router.post("/{note_id}/reprocess")
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

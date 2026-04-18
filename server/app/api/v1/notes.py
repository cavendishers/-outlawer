from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.serializers import serialize_note
from app.api.deps import DbSession, get_current_user
from app.core.pagination import normalize_page_params, paginate_query
from app.core.responses import ok, paginated
from app.models.ai_job import AIJob
from app.models.note import Note
from app.models.raw_asset import RawAsset
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

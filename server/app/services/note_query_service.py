from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.serializers import serialize_note
from app.core.pagination import PageParams, paginate_query
from app.models.note import Note
from app.domains.replay.service import (
    compare_extraction_runs,
    get_extraction_run,
    list_extraction_runs,
    list_note_replay_actions,
    resolve_applied_run_id,
    serialize_extraction_run,
    serialize_replay_action,
)


def get_owned_note(db: Session, *, user_id: str, note_id: str) -> Note:
    note = db.get(Note, note_id)
    if note is None or note.user_id != user_id:
        raise ValueError("Note not found")
    return note


def list_notes(db: Session, *, user_id: str, params: PageParams) -> tuple[list[dict[str, Any]], int]:
    query = select(Note).where(Note.user_id == user_id).order_by(Note.created_at.desc())
    notes, total = paginate_query(db, query, params)
    return [serialize_note(note) for note in notes], total


def get_note_detail(db: Session, *, user_id: str, note_id: str) -> dict[str, Any]:
    note = get_owned_note(db, user_id=user_id, note_id=note_id)
    return serialize_note(note)


def list_note_extraction_run_items(db: Session, *, user_id: str, note_id: str) -> dict[str, Any]:
    note = get_owned_note(db, user_id=user_id, note_id=note_id)
    runs = list_extraction_runs(db, user_id=user_id, note_id=note.id)
    applied_run_id = resolve_applied_run_id(runs)
    return {
        "items": [serialize_extraction_run(run, applied_run_id=applied_run_id) for run in runs],
        "total": len(runs),
    }


def compare_note_extraction_runs(
    db: Session,
    *,
    user_id: str,
    note_id: str,
    base_run_id: str,
    candidate_run_id: str,
) -> dict[str, Any]:
    note = get_owned_note(db, user_id=user_id, note_id=note_id)
    base_run = get_extraction_run(db, user_id=user_id, note_id=note.id, run_id=base_run_id)
    candidate_run = get_extraction_run(db, user_id=user_id, note_id=note.id, run_id=candidate_run_id)
    if not base_run or not candidate_run:
        raise ValueError("Extraction run not found")
    applied_run_id = resolve_applied_run_id(list_extraction_runs(db, user_id=user_id, note_id=note.id))
    return compare_extraction_runs(base_run, candidate_run, applied_run_id=applied_run_id)


def get_note_extraction_run_detail(db: Session, *, user_id: str, note_id: str, run_id: str) -> dict[str, Any]:
    note = get_owned_note(db, user_id=user_id, note_id=note_id)
    run = get_extraction_run(db, user_id=user_id, note_id=note.id, run_id=run_id)
    if not run:
        raise ValueError("Extraction run not found")
    applied_run_id = resolve_applied_run_id(list_extraction_runs(db, user_id=user_id, note_id=note.id))
    return serialize_extraction_run(run, applied_run_id=applied_run_id)


def list_note_replay_action_items(db: Session, *, user_id: str, note_id: str) -> dict[str, Any]:
    note = get_owned_note(db, user_id=user_id, note_id=note_id)
    actions = list_note_replay_actions(db, user_id=user_id, note_id=note.id)
    return {"items": [serialize_replay_action(action) for action in actions], "total": len(actions)}

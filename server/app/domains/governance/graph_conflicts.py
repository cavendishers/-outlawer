from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.graph_conflict import GraphConflictDisposition
from app.models.review import ReviewAction


ALLOWED_DISPOSITIONS = {"open", "keep", "snooze"}


def set_graph_conflict_disposition(
    db: Session,
    *,
    user_id: str,
    conflict_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    conflict_id = conflict_id.strip()
    if not conflict_id or len(conflict_id) > 255:
        raise ValueError("Invalid graph conflict id")
    disposition = str(payload.get("disposition") or "").strip().lower()
    if disposition not in ALLOWED_DISPOSITIONS:
        raise ValueError("Disposition must be open, keep, or snooze")

    row = db.scalar(
        select(GraphConflictDisposition).where(
            GraphConflictDisposition.user_id == user_id,
            GraphConflictDisposition.conflict_id == conflict_id,
        )
    )
    before = row.disposition if row is not None else "open"
    if row is None:
        row = GraphConflictDisposition(user_id=user_id, conflict_id=conflict_id)

    note = clean_optional_string(payload.get("note"))
    snapshot = {
        key: payload.get(key)
        for key in ("conflict_type", "title", "summary", "node_ids", "edge_label")
        if payload.get(key) is not None
    }
    row.disposition = disposition
    row.note = note
    row.snapshot_json = snapshot
    db.add(row)
    db.flush()
    db.add(
        ReviewAction(
            user_id=user_id,
            target_type="graph_conflict",
            target_id=row.id,
            action_type="set_conflict_disposition",
            status_before=before,
            status_after=disposition,
            payload_json={
                "conflict_id": conflict_id,
                "note": note,
                "snapshot": snapshot,
            },
        )
    )
    db.commit()
    db.refresh(row)
    return serialize_graph_conflict_disposition(row)


def apply_graph_conflict_dispositions(
    db: Session,
    *,
    user_id: str,
    conflicts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    conflict_ids = [item["id"] for item in conflicts]
    if not conflict_ids:
        return []
    rows = db.scalars(
        select(GraphConflictDisposition).where(
            GraphConflictDisposition.user_id == user_id,
            GraphConflictDisposition.conflict_id.in_(conflict_ids),
        )
    ).all()
    by_conflict_id = {row.conflict_id: row for row in rows}
    return [
        {
            **conflict,
            "disposition": by_conflict_id[conflict["id"]].disposition if conflict["id"] in by_conflict_id else "open",
            "disposition_note": by_conflict_id[conflict["id"]].note if conflict["id"] in by_conflict_id else None,
            "is_active": conflict["id"] not in by_conflict_id
            or by_conflict_id[conflict["id"]].disposition == "open",
        }
        for conflict in conflicts
    ]


def serialize_graph_conflict_disposition(row: GraphConflictDisposition) -> dict[str, Any]:
    return {
        "id": row.id,
        "conflict_id": row.conflict_id,
        "disposition": row.disposition,
        "note": row.note,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def clean_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None

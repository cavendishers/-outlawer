from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.serializers import isoformat, serialize_entity, serialize_event
from app.models.entity import Entity, EntityAlias, EventEntity, Relation
from app.models.event import Event, TimelineItem
from app.models.manual_knowledge import ManualKnowledgeEvidence
from app.models.note import Note
from app.models.raw_asset import RawAsset
from app.models.review import ReviewAction
from app.utils.text import normalize_name


def create_manual_entity(db: Session, *, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    entity = _build_entity(db, user_id=user_id, payload=payload)
    evidence = _attach_evidence(db, user_id=user_id, target_type="entity", target_id=entity.id, payload=payload.get("evidence"))
    _log_action(
        db,
        user_id=user_id,
        target_type="entity",
        target_id=entity.id,
        action_type="create_entity",
        payload={"source": "manual", "name": entity.display_name, "evidence_id": evidence.id if evidence else None},
    )
    db.commit()
    db.refresh(entity)
    return {
        "entity": serialize_entity(entity, aliases=[row.alias for row in _entity_aliases(db, entity.id)]),
        "evidence": serialize_manual_evidence(db, evidence) if evidence else None,
        "routes": _entity_routes(entity.id),
    }


def create_manual_event(db: Session, *, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    event = _build_event(db, user_id=user_id, payload=payload)
    evidence = _attach_evidence(db, user_id=user_id, target_type="event", target_id=event.id, payload=payload.get("evidence"))
    _log_action(
        db,
        user_id=user_id,
        target_type="event",
        target_id=event.id,
        action_type="create_event",
        payload={"source": "manual", "title": event.title, "evidence_id": evidence.id if evidence else None},
    )
    db.commit()
    db.refresh(event)
    return {"event": serialize_event(event), "evidence": serialize_manual_evidence(db, evidence) if evidence else None, "routes": _event_routes(event.id)}


def attach_manual_evidence(db: Session, *, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    target_type = _clean_required(payload.get("target_type"), "Target type is required").lower()
    target_id = _clean_required(payload.get("target_id"), "Target id is required")
    _get_owned_target(db, user_id=user_id, target_type=target_type, target_id=target_id)
    row = _attach_evidence(db, user_id=user_id, target_type=target_type, target_id=target_id, payload=payload)
    assert row is not None
    db.commit()
    db.refresh(row)
    return serialize_manual_evidence(db, row)


def create_graph_manual_node(db: Session, *, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    node_type = _clean_required(payload.get("node_type"), "Node type is required").lower()
    anchor_type = _clean_required(payload.get("anchor_type"), "Anchor type is required").lower()
    anchor_id = _clean_required(payload.get("anchor_id"), "Anchor id is required")
    if node_type not in {"entity", "event"} or anchor_type not in {"entity", "event"}:
        raise ValueError("Node and anchor types must be entity or event")
    _get_owned_target(db, user_id=user_id, target_type=anchor_type, target_id=anchor_id)

    if node_type == "entity":
        node = _build_entity(
            db,
            user_id=user_id,
            payload={
                "canonical_name": payload.get("name"),
                "display_name": payload.get("name"),
                "entity_type": payload.get("subtype") or "person",
                "description": payload.get("description"),
            },
        )
        label = node.display_name
    else:
        node = _build_event(
            db,
            user_id=user_id,
            payload={
                "title": payload.get("name"),
                "description": payload.get("description"),
                "summary": payload.get("description"),
                "event_type": payload.get("subtype"),
                "start_time": payload.get("event_time"),
                "timeline_sort_time": payload.get("event_time"),
                "time_precision": "exact" if payload.get("event_time") else "unknown",
            },
        )
        label = node.title

    connection_type: str
    if {node_type, anchor_type} == {"entity", "event"}:
        event_id = node.id if node_type == "event" else anchor_id
        entity_id = node.id if node_type == "entity" else anchor_id
        relation_type = _clean_optional(payload.get("relation_type")) or "participates_in"
        row = EventEntity(
            event_id=event_id,
            entity_id=entity_id,
            role=_clean_optional(payload.get("role")),
            relation_type=relation_type,
            display_order=_next_participant_order(db, event_id),
            confidence_score=1.0,
        )
        db.add(row)
        db.flush()
        connection_type = "participant"
        connection_id = row.id
    else:
        relation = Relation(
            user_id=user_id,
            source_type=anchor_type,
            source_id=anchor_id,
            relation_type=_clean_optional(payload.get("relation_type")) or "related_to",
            target_type=node_type,
            target_id=node.id,
            evidence_count=1,
            confidence_score=1.0,
            meta_json={"source": "manual_authoring"},
        )
        db.add(relation)
        db.flush()
        connection_type = "relation"
        connection_id = relation.id

    evidence = _attach_evidence(db, user_id=user_id, target_type=node_type, target_id=node.id, payload=payload.get("evidence"))
    _log_action(
        db,
        user_id=user_id,
        target_type=node_type,
        target_id=node.id,
        action_type=f"create_{node_type}",
        payload={"source": "graph", "anchor_type": anchor_type, "anchor_id": anchor_id},
    )
    _log_action(
        db,
        user_id=user_id,
        target_type=connection_type,
        target_id=connection_id,
        action_type="create_manual_connection",
        payload={
            "anchor_type": anchor_type,
            "anchor_id": anchor_id,
            "node_type": node_type,
            "node_id": node.id,
            "relation_type": payload.get("relation_type") or "participates_in",
        },
    )
    db.commit()
    return {
        "node_type": node_type,
        "node_id": node.id,
        "label": label,
        "connection_type": connection_type,
        "connection_id": connection_id,
        "evidence": serialize_manual_evidence(db, evidence) if evidence else None,
        "graph_href": f"/graph?{node_type}_id={node.id}&active_node_id={node.id}",
    }


def _build_entity(db: Session, *, user_id: str, payload: dict[str, Any]) -> Entity:
    canonical_name = _clean_required(payload.get("canonical_name"), "Canonical name is required")
    normalized_name = normalize_name(canonical_name)
    if db.scalar(select(Entity.id).where(Entity.user_id == user_id, Entity.normalized_name == normalized_name)):
        raise ValueError("An entity with the same normalized name already exists")
    display_name = _clean_optional(payload.get("display_name")) or canonical_name
    entity = Entity(
        user_id=user_id,
        entity_type=_clean_optional(payload.get("entity_type")) or "person",
        canonical_name=canonical_name,
        display_name=display_name,
        description=_clean_optional(payload.get("description")),
        alias_json=[],
        normalized_name=normalized_name,
        status="active",
        confidence_score=1.0,
        first_seen_at=payload.get("first_seen_at"),
        last_seen_at=payload.get("last_seen_at"),
    )
    db.add(entity)
    db.flush()
    seen: set[str] = set()
    for raw_alias in payload.get("aliases") or []:
        alias = _clean_optional(raw_alias)
        normalized = normalize_name(alias or "")
        if not alias or not normalized or normalized == normalized_name or normalized in seen:
            continue
        seen.add(normalized)
        db.add(EntityAlias(entity_id=entity.id, alias=alias, normalized_alias=normalized, alias_type="manual"))
    return entity


def _build_event(db: Session, *, user_id: str, payload: dict[str, Any]) -> Event:
    title = _clean_required(payload.get("title"), "Title is required")
    evidence = payload.get("evidence") or {}
    start_time = payload.get("start_time")
    sort_time = payload.get("timeline_sort_time") or start_time
    time_text = _clean_optional(payload.get("time_text"))
    if not time_text and isinstance(start_time, datetime):
        time_text = start_time.date().isoformat()
    event = Event(
        user_id=user_id,
        title=title,
        summary=_clean_optional(payload.get("summary")) or _summary_from_description(payload.get("description")),
        description=_clean_optional(payload.get("description")),
        event_type=_clean_optional(payload.get("event_type")),
        status="active",
        source_note_id=evidence.get("note_id"),
        start_time=start_time,
        end_time=payload.get("end_time"),
        time_precision=_clean_optional(payload.get("time_precision")) or "unknown",
        time_text=time_text,
        timeline_sort_time=sort_time,
        location_text=_clean_optional(payload.get("location_text")),
        confidence_score=1.0,
    )
    db.add(event)
    db.flush()
    db.add(
        TimelineItem(
            user_id=user_id,
            event_id=event.id,
            note_id=event.source_note_id,
            title=event.title,
            summary=event.summary,
            display_time=event.time_text,
            sort_time=event.timeline_sort_time,
            time_precision=event.time_precision,
            importance_score=1.0,
        )
    )
    return event


def _attach_evidence(
    db: Session,
    *,
    user_id: str,
    target_type: str,
    target_id: str,
    payload: dict[str, Any] | None,
) -> ManualKnowledgeEvidence | None:
    if not payload:
        return None
    note_id = payload.get("note_id")
    asset_id = payload.get("raw_asset_id")
    if bool(note_id) == bool(asset_id):
        raise ValueError("Exactly one evidence source is required")
    if note_id:
        note = db.get(Note, note_id)
        if note is None or note.user_id != user_id:
            raise ValueError("Evidence note not found")
    else:
        asset = db.get(RawAsset, asset_id)
        if asset is None or asset.user_id != user_id:
            raise ValueError("Evidence asset not found")
    row = ManualKnowledgeEvidence(
        user_id=user_id,
        target_type=target_type,
        target_id=target_id,
        note_id=note_id,
        raw_asset_id=asset_id,
        excerpt=_clean_optional(payload.get("excerpt")),
        curator_note=_clean_optional(payload.get("curator_note")),
        provenance_type="manual",
    )
    db.add(row)
    db.flush()
    _log_action(
        db,
        user_id=user_id,
        target_type=target_type,
        target_id=target_id,
        action_type="attach_manual_evidence",
        payload={"evidence_id": row.id, "note_id": note_id, "raw_asset_id": asset_id},
    )
    return row


def serialize_manual_evidence(db: Session, row: ManualKnowledgeEvidence) -> dict[str, Any]:
    source = db.get(Note, row.note_id) if row.note_id else db.get(RawAsset, row.raw_asset_id)
    return {
        "id": row.id,
        "target_type": row.target_type,
        "target_id": row.target_id,
        "note_id": row.note_id,
        "raw_asset_id": row.raw_asset_id,
        "source_title": source.title if source else "已删除来源",
        "excerpt": row.excerpt,
        "curator_note": row.curator_note,
        "provenance_type": row.provenance_type,
        "created_at": isoformat(row.created_at),
    }


def _get_owned_target(db: Session, *, user_id: str, target_type: str, target_id: str) -> Entity | Event:
    model = Entity if target_type == "entity" else Event if target_type == "event" else None
    if model is None:
        raise ValueError("Manual evidence target must be entity or event")
    target = db.get(model, target_id)
    if target is None or target.user_id != user_id:
        raise ValueError("Knowledge target not found")
    return target


def _entity_aliases(db: Session, entity_id: str) -> list[EntityAlias]:
    return list(db.scalars(select(EntityAlias).where(EntityAlias.entity_id == entity_id).order_by(EntityAlias.created_at)).all())


def _next_participant_order(db: Session, event_id: str) -> int:
    maximum = db.scalar(select(func.max(EventEntity.display_order)).where(EventEntity.event_id == event_id))
    return int(maximum if maximum is not None else -1) + 1


def _log_action(
    db: Session,
    *,
    user_id: str,
    target_type: str,
    target_id: str,
    action_type: str,
    payload: dict[str, Any],
) -> None:
    db.add(
        ReviewAction(
            user_id=user_id,
            target_type=target_type,
            target_id=target_id,
            action_type=action_type,
            status_before=None,
            status_after="active",
            payload_json=payload,
        )
    )


def _entity_routes(entity_id: str) -> dict[str, str]:
    return {
        "detail": f"/story/entity/{entity_id}",
        "curation": f"/curation/entities/{entity_id}",
        "graph": f"/graph?entity_id={entity_id}&active_node_id={entity_id}",
    }


def _event_routes(event_id: str) -> dict[str, str]:
    return {
        "detail": f"/events/{event_id}",
        "curation": f"/curation/events/{event_id}",
        "graph": f"/graph?event_id={event_id}&active_node_id={event_id}",
        "timeline": "/timeline",
    }


def _clean_required(value: Any, message: str) -> str:
    cleaned = str(value).strip() if value is not None else ""
    if not cleaned:
        raise ValueError(message)
    return cleaned


def _clean_optional(value: Any) -> str | None:
    cleaned = str(value).strip() if value is not None else ""
    return cleaned or None


def _summary_from_description(value: Any) -> str | None:
    description = _clean_optional(value)
    return description[:160] if description else None

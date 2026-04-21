from __future__ import annotations

from datetime import UTC, datetime
from math import ceil
from typing import Any

from sqlalchemy import Select, func, or_, select, update
from sqlalchemy.orm import Session

from app.api.serializers import isoformat, serialize_entity, serialize_event, serialize_note
from app.models.embedding import Embedding
from app.models.entity import Entity, EntityAlias, EventEntity, NoteEntity, NoteEvent, Relation
from app.models.event import Event, TimelineItem
from app.models.extraction import ExtractionEvidence, MergeCandidate
from app.models.note import Note
from app.models.review import EntityMergeHistory, EventMergeHistory, ReviewAction
from app.models.style_view import StyleView
from app.services.entity_alias_service import list_entity_alias_rows, list_entity_alias_values, upsert_entity_alias_value
from app.domains.retrieval.event_query import list_event_participants
from app.services.graph_service import get_related_events_for_event, get_timeline_fragments_for_entity
def list_merge_candidates(
    db: Session,
    *,
    user_id: str,
    object_type: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    query: Select = select(MergeCandidate).where(MergeCandidate.user_id == user_id)
    if object_type:
        query = query.where(MergeCandidate.object_type == object_type)
    if status:
        query = query.where(MergeCandidate.status == status)

    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    total = int(db.scalar(count_query) or 0)
    items = db.scalars(
        query.order_by(MergeCandidate.score.desc(), MergeCandidate.created_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    ).all()

    return {
        "items": [serialize_merge_candidate_list_item(db, candidate) for candidate in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": ceil(total / page_size) if page_size else 0,
    }


def get_merge_candidate_detail(db: Session, *, user_id: str, candidate_id: str) -> dict[str, Any]:
    candidate = get_candidate_for_user(db, user_id=user_id, candidate_id=candidate_id)
    source_summary = build_object_summary(db, candidate.object_type, candidate.source_id, user_id=user_id)
    candidate_summary = build_object_summary(db, candidate.object_type, candidate.candidate_id, user_id=user_id)

    return {
        "id": candidate.id,
        "object_type": candidate.object_type,
        "status": candidate.status,
        "score": float(candidate.score),
        "reason": candidate.reason_json,
        "reviewed_at": isoformat(candidate.reviewed_at),
        "review_note": candidate.review_note,
        "source": source_summary,
        "candidate": candidate_summary,
        "can_accept": candidate.status == "pending" and source_summary is not None and candidate_summary is not None,
        "can_reject": candidate.status == "pending",
    }


def get_entity_review_context(db: Session, *, user_id: str, entity_id: str) -> dict[str, Any]:
    entity = db.get(Entity, entity_id)
    if not entity or entity.user_id != user_id:
        raise ValueError("Entity not found")

    related_event_links = db.scalars(select(EventEntity).where(EventEntity.entity_id == entity.id)).all()
    related_note_links = db.scalars(select(NoteEntity).where(NoteEntity.entity_id == entity.id)).all()
    aliases = db.scalars(select(EntityAlias).where(EntityAlias.entity_id == entity.id).order_by(EntityAlias.created_at.asc())).all()
    candidates = db.scalars(
        select(MergeCandidate)
        .where(
            MergeCandidate.user_id == user_id,
            MergeCandidate.object_type == "entity",
            or_(MergeCandidate.source_id == entity.id, MergeCandidate.candidate_id == entity.id),
        )
        .order_by(MergeCandidate.score.desc(), MergeCandidate.created_at.desc())
    ).all()

    return {
        "entity": serialize_entity(entity, aliases=list_entity_alias_values(db, entity)),
        "aliases": [
            {
                "id": alias.id,
                "alias": alias.alias,
                "normalized_alias": alias.normalized_alias,
                "alias_type": alias.alias_type,
                "created_at": isoformat(alias.created_at),
            }
            for alias in aliases
        ],
        "stats": {
            "related_event_count": len({link.event_id for link in related_event_links}),
            "related_note_count": len({link.note_id for link in related_note_links}),
            "alias_count": len(aliases),
            "candidate_count": len(candidates),
        },
        "timeline_fragments": get_timeline_fragments_for_entity(db, user_id, entity.id),
        "candidates": [serialize_merge_candidate_list_item(db, candidate) for candidate in candidates],
    }


def get_event_review_context(db: Session, *, user_id: str, event_id: str) -> dict[str, Any]:
    event = db.get(Event, event_id)
    if not event or event.user_id != user_id:
        raise ValueError("Event not found")

    participant_links = db.scalars(select(EventEntity).where(EventEntity.event_id == event.id)).all()
    note_links = db.scalars(select(NoteEvent).where(NoteEvent.event_id == event.id)).all()
    candidates = db.scalars(
        select(MergeCandidate)
        .where(
            MergeCandidate.user_id == user_id,
            MergeCandidate.object_type == "event",
            or_(MergeCandidate.source_id == event.id, MergeCandidate.candidate_id == event.id),
        )
        .order_by(MergeCandidate.score.desc(), MergeCandidate.created_at.desc())
    ).all()

    source_note = db.get(Note, event.source_note_id) if event.source_note_id else None
    participants = list_event_participants(db, event.id)

    return {
        "event": {
            **serialize_event(event),
            "source_note_title": source_note.title if source_note else None,
            "participants": participants,
            "related_events": get_related_events_for_event(db, user_id, event),
        },
        "stats": {
            "participant_count": len(participant_links),
            "linked_note_count": len({link.note_id for link in note_links}),
            "candidate_count": len(candidates),
        },
        "candidates": [serialize_merge_candidate_list_item(db, candidate) for candidate in candidates],
    }


def reject_merge_candidate(
    db: Session,
    *,
    user_id: str,
    candidate_id: str,
    reason: str,
    note: str | None = None,
) -> dict[str, Any]:
    candidate = get_candidate_for_user(db, user_id=user_id, candidate_id=candidate_id)
    previous_status = candidate.status
    candidate.status = "rejected"
    candidate.reviewed_at = datetime.now(UTC)
    candidate.review_note = note or reason
    db.add(candidate)
    log_review_action(
        db,
        user_id=user_id,
        target_type="merge_candidate",
        target_id=candidate.id,
        action_type="reject",
        status_before=previous_status,
        status_after=candidate.status,
        payload_json={"reason": reason, "note": note, "object_type": candidate.object_type},
    )
    db.commit()
    db.refresh(candidate)
    return {"candidate_id": candidate.id, "status": candidate.status}


def confirm_entity_alias(
    db: Session,
    *,
    user_id: str,
    entity_id: str,
    alias: str,
    note: str | None = None,
) -> dict[str, Any]:
    entity = db.get(Entity, entity_id)
    if not entity or entity.user_id != user_id:
        raise ValueError("Entity not found")

    ensure_entity_alias(db, entity, alias, alias_type="manual")
    log_review_action(
        db,
        user_id=user_id,
        target_type="entity",
        target_id=entity.id,
        action_type="confirm_alias",
        status_before=entity.status,
        status_after=entity.status,
        payload_json={"alias": alias, "note": note},
    )
    db.commit()
    db.refresh(entity)
    return {"entity_id": entity.id, "aliases": list_entity_alias_values(db, entity)}


def accept_merge_candidate(
    db: Session,
    *,
    user_id: str,
    candidate_id: str,
    resolution: str = "merge",
    survivor_id: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    candidate = get_candidate_for_user(db, user_id=user_id, candidate_id=candidate_id)
    previous_status = candidate.status
    if previous_status != "pending":
        raise ValueError("Candidate is not pending")

    if candidate.object_type == "entity":
        result = accept_entity_candidate(
            db,
            user_id=user_id,
            candidate=candidate,
            resolution=resolution,
            survivor_id=survivor_id,
            note=note,
        )
    elif candidate.object_type == "event":
        if resolution != "merge":
            raise ValueError("Event candidates only support merge resolution")
        result = accept_event_candidate(
            db,
            user_id=user_id,
            candidate=candidate,
            survivor_id=survivor_id,
            note=note,
        )
    else:
        raise ValueError("Unsupported merge candidate type")

    candidate.status = "accepted"
    candidate.reviewed_at = datetime.now(UTC)
    candidate.review_note = note
    db.add(candidate)
    log_review_action(
        db,
        user_id=user_id,
        target_type="merge_candidate",
        target_id=candidate.id,
        action_type=f"accept_{resolution}",
        status_before=previous_status,
        status_after=candidate.status,
        payload_json={"resolution": resolution, "survivor_id": survivor_id, "object_type": candidate.object_type},
    )
    db.commit()
    return result


def accept_entity_candidate(
    db: Session,
    *,
    user_id: str,
    candidate: MergeCandidate,
    resolution: str,
    survivor_id: str | None,
    note: str | None,
) -> dict[str, Any]:
    source = db.get(Entity, candidate.source_id)
    other = db.get(Entity, candidate.candidate_id)
    if not source or not other or source.user_id != user_id or other.user_id != user_id:
        raise ValueError("Entity candidate targets not found")
    if resolution not in {"merge", "alias_only"}:
        raise ValueError("Unsupported entity candidate resolution")
    if survivor_id and survivor_id not in {source.id, other.id}:
        raise ValueError("Survivor must be one of the candidate targets")

    survivor = source if not survivor_id or survivor_id == source.id else other
    merged = other if survivor.id == source.id else source

    if resolution == "alias_only":
        add_aliases_from_entity(db, survivor, merged, alias_type="confirmed")
        log_review_action(
            db,
            user_id=user_id,
            target_type="entity",
            target_id=survivor.id,
            action_type="alias_only",
            status_before=survivor.status,
            status_after=survivor.status,
            payload_json={"candidate_id": candidate.id, "other_entity_id": merged.id, "note": note},
        )
        return {
            "candidate_id": candidate.id,
            "status": "accepted",
            "resolution": resolution,
            "survivor_id": survivor.id,
            "merged_id": None,
        }

    merge_entities(db, user_id=user_id, survivor=survivor, merged=merged, note=note)
    return {
        "candidate_id": candidate.id,
        "status": "accepted",
        "resolution": resolution,
        "survivor_id": survivor.id,
        "merged_id": merged.id,
    }


def accept_event_candidate(
    db: Session,
    *,
    user_id: str,
    candidate: MergeCandidate,
    survivor_id: str | None,
    note: str | None,
) -> dict[str, Any]:
    source = db.get(Event, candidate.source_id)
    other = db.get(Event, candidate.candidate_id)
    if not source or not other or source.user_id != user_id or other.user_id != user_id:
        raise ValueError("Event candidate targets not found")
    if survivor_id and survivor_id not in {source.id, other.id}:
        raise ValueError("Survivor must be one of the candidate targets")

    survivor = source if not survivor_id or survivor_id == source.id else other
    merged = other if survivor.id == source.id else source
    merge_events(db, user_id=user_id, survivor=survivor, merged=merged, note=note)
    return {
        "candidate_id": candidate.id,
        "status": "accepted",
        "resolution": "merge",
        "survivor_id": survivor.id,
        "merged_id": merged.id,
    }


def merge_entities(db: Session, *, user_id: str, survivor: Entity, merged: Entity, note: str | None = None) -> None:
    add_aliases_from_entity(db, survivor, merged, alias_type="merged")
    survivor.description = survivor.description or merged.description
    survivor.confidence_score = max_nullable(survivor.confidence_score, merged.confidence_score)
    survivor.first_seen_at = min_nullable_datetime(survivor.first_seen_at, merged.first_seen_at)
    survivor.last_seen_at = max_nullable_datetime(survivor.last_seen_at, merged.last_seen_at)
    db.add(survivor)

    db.execute(update(NoteEntity).where(NoteEntity.entity_id == merged.id).values(entity_id=survivor.id))
    db.execute(update(EventEntity).where(EventEntity.entity_id == merged.id).values(entity_id=survivor.id))
    db.execute(
        update(ExtractionEvidence)
        .where(ExtractionEvidence.target_type == "entity", ExtractionEvidence.target_id == merged.id)
        .values(target_id=survivor.id)
    )
    db.execute(update(Relation).where(Relation.source_type == "entity", Relation.source_id == merged.id).values(source_id=survivor.id))
    db.execute(update(Relation).where(Relation.target_type == "entity", Relation.target_id == merged.id).values(target_id=survivor.id))
    db.execute(
        update(StyleView)
        .where(StyleView.target_type == "entity", StyleView.target_id == merged.id)
        .values(target_id=survivor.id)
    )

    dedupe_embedding_owner(db, owner_type="entity", survivor_id=survivor.id, merged_id=merged.id)
    db.execute(update(EntityAlias).where(EntityAlias.entity_id == merged.id).values(entity_id=survivor.id))
    rewrite_merge_candidates(db, user_id=user_id, object_type="entity", survivor_id=survivor.id, merged_id=merged.id)

    dedupe_note_entities(db, survivor.id)
    dedupe_event_entities_for_entity(db, survivor.id)
    dedupe_entity_aliases(db, survivor)
    dedupe_relations(db, user_id=user_id, affected_ids={survivor.id, merged.id})

    db.add(
        EntityMergeHistory(
            user_id=user_id,
            survivor_entity_id=survivor.id,
            merged_entity_id=merged.id,
            merge_reason=note,
            payload_json={
                "survivor_display_name": survivor.display_name,
                "merged_display_name": merged.display_name,
                "merged_aliases": list_entity_alias_values(db, merged),
            },
        )
    )
    log_review_action(
        db,
        user_id=user_id,
        target_type="entity",
        target_id=survivor.id,
        action_type="merge",
        status_before=merged.status,
        status_after=survivor.status,
        payload_json={"survivor_id": survivor.id, "merged_id": merged.id, "note": note},
    )
    db.delete(merged)


def merge_events(db: Session, *, user_id: str, survivor: Event, merged: Event, note: str | None = None) -> None:
    survivor.summary = choose_richer_text(survivor.summary, merged.summary)
    survivor.description = choose_richer_text(survivor.description, merged.description)
    survivor.location_text = survivor.location_text or merged.location_text
    survivor.time_text = survivor.time_text or merged.time_text
    survivor.start_time = survivor.start_time or merged.start_time
    survivor.end_time = survivor.end_time or merged.end_time
    survivor.timeline_sort_time = survivor.timeline_sort_time or merged.timeline_sort_time
    survivor.source_note_id = survivor.source_note_id or merged.source_note_id
    survivor.confidence_score = max_nullable(survivor.confidence_score, merged.confidence_score)
    db.add(survivor)

    db.execute(update(NoteEvent).where(NoteEvent.event_id == merged.id).values(event_id=survivor.id))
    db.execute(update(EventEntity).where(EventEntity.event_id == merged.id).values(event_id=survivor.id))
    db.execute(update(TimelineItem).where(TimelineItem.event_id == merged.id).values(event_id=survivor.id))
    db.execute(
        update(ExtractionEvidence)
        .where(ExtractionEvidence.target_type == "event", ExtractionEvidence.target_id == merged.id)
        .values(target_id=survivor.id)
    )
    db.execute(update(Relation).where(Relation.source_type == "event", Relation.source_id == merged.id).values(source_id=survivor.id))
    db.execute(update(Relation).where(Relation.target_type == "event", Relation.target_id == merged.id).values(target_id=survivor.id))
    db.execute(
        update(StyleView)
        .where(StyleView.target_type == "event", StyleView.target_id == merged.id)
        .values(target_id=survivor.id)
    )

    dedupe_embedding_owner(db, owner_type="event", survivor_id=survivor.id, merged_id=merged.id)
    rewrite_merge_candidates(db, user_id=user_id, object_type="event", survivor_id=survivor.id, merged_id=merged.id)

    dedupe_note_events(db, survivor.id)
    dedupe_event_entities_for_event(db, survivor.id)
    dedupe_timeline_items(db, survivor.id)
    dedupe_style_views(db, target_type="event", target_id=survivor.id)
    dedupe_relations(db, user_id=user_id, affected_ids={survivor.id, merged.id})

    db.add(
        EventMergeHistory(
            user_id=user_id,
            survivor_event_id=survivor.id,
            merged_event_id=merged.id,
            merge_reason=note,
            payload_json={
                "survivor_title": survivor.title,
                "merged_title": merged.title,
                "merged_time_text": merged.time_text,
            },
        )
    )
    log_review_action(
        db,
        user_id=user_id,
        target_type="event",
        target_id=survivor.id,
        action_type="merge",
        status_before=merged.status,
        status_after=survivor.status,
        payload_json={"survivor_id": survivor.id, "merged_id": merged.id, "note": note},
    )
    db.delete(merged)


def get_candidate_for_user(db: Session, *, user_id: str, candidate_id: str) -> MergeCandidate:
    candidate = db.get(MergeCandidate, candidate_id)
    if not candidate or candidate.user_id != user_id:
        raise ValueError("Merge candidate not found")
    return candidate


def serialize_merge_candidate_list_item(db: Session, candidate: MergeCandidate) -> dict[str, Any]:
    return {
        "id": candidate.id,
        "object_type": candidate.object_type,
        "status": candidate.status,
        "score": float(candidate.score),
        "reason": candidate.reason_json,
        "reviewed_at": isoformat(candidate.reviewed_at),
        "review_note": candidate.review_note,
        "source": build_object_summary(db, candidate.object_type, candidate.source_id, user_id=candidate.user_id),
        "candidate": build_object_summary(db, candidate.object_type, candidate.candidate_id, user_id=candidate.user_id),
    }


def build_object_summary(db: Session, object_type: str, object_id: str, *, user_id: str) -> dict[str, Any] | None:
    if object_type == "entity":
        entity = db.get(Entity, object_id)
        if not entity or entity.user_id != user_id:
            return None
        note_count = int(db.scalar(select(func.count()).select_from(NoteEntity).where(NoteEntity.entity_id == entity.id)) or 0)
        event_count = int(db.scalar(select(func.count()).select_from(EventEntity).where(EventEntity.entity_id == entity.id)) or 0)
        return {
            "id": entity.id,
            "label": entity.display_name,
            "href": f"/review/entities/{entity.id}",
            "stats": {"related_note_count": note_count, "related_event_count": event_count},
            "data": serialize_entity(entity, aliases=list_entity_alias_values(db, entity)),
        }
    if object_type == "event":
        event = db.get(Event, object_id)
        if not event or event.user_id != user_id:
            return None
        participant_count = int(db.scalar(select(func.count()).select_from(EventEntity).where(EventEntity.event_id == event.id)) or 0)
        note_count = int(db.scalar(select(func.count()).select_from(NoteEvent).where(NoteEvent.event_id == event.id)) or 0)
        return {
            "id": event.id,
            "label": event.title,
            "href": f"/review/events/{event.id}",
            "stats": {"participant_count": participant_count, "linked_note_count": note_count},
            "data": serialize_event(event),
        }
    if object_type == "note":
        note = db.get(Note, object_id)
        if not note or note.user_id != user_id:
            return None
        return {
            "id": note.id,
            "label": note.title,
            "href": f"/notes/{note.id}",
            "stats": {},
            "data": serialize_note(note),
        }
    return None


def ensure_entity_alias(db: Session, entity: Entity, alias: str, *, alias_type: str) -> None:
    upsert_entity_alias_value(db, entity=entity, alias=alias, alias_type=alias_type)


def add_aliases_from_entity(db: Session, survivor: Entity, merged: Entity, *, alias_type: str) -> None:
    alias_values = [merged.display_name, merged.canonical_name, *list_entity_alias_values(db, merged)]
    for value in alias_values:
        ensure_entity_alias(db, survivor, value, alias_type=alias_type)


def log_review_action(
    db: Session,
    *,
    user_id: str,
    target_type: str,
    target_id: str,
    action_type: str,
    status_before: str | None,
    status_after: str | None,
    payload_json: dict[str, Any],
) -> None:
    db.add(
        ReviewAction(
            user_id=user_id,
            target_type=target_type,
            target_id=target_id,
            action_type=action_type,
            status_before=status_before,
            status_after=status_after,
            payload_json=payload_json,
        )
    )


def dedupe_embedding_owner(db: Session, *, owner_type: str, survivor_id: str, merged_id: str) -> None:
    survivor_embeddings = db.scalars(
        select(Embedding).where(Embedding.owner_type == owner_type, Embedding.owner_id == survivor_id)
    ).all()
    merged_embeddings = db.scalars(
        select(Embedding).where(Embedding.owner_type == owner_type, Embedding.owner_id == merged_id)
    ).all()
    survivor_by_model = {embedding.model_name: embedding for embedding in survivor_embeddings}
    for embedding in merged_embeddings:
        if embedding.model_name in survivor_by_model:
            db.delete(embedding)
            continue
        embedding.owner_id = survivor_id
        db.add(embedding)


def rewrite_merge_candidates(db: Session, *, user_id: str, object_type: str, survivor_id: str, merged_id: str) -> None:
    candidates = db.scalars(
        select(MergeCandidate).where(MergeCandidate.user_id == user_id, MergeCandidate.object_type == object_type)
    ).all()
    for candidate in candidates:
        changed = False
        if candidate.source_id == merged_id:
            candidate.source_id = survivor_id
            changed = True
        if candidate.candidate_id == merged_id:
            candidate.candidate_id = survivor_id
            changed = True
        if candidate.source_id == candidate.candidate_id and candidate.status == "pending":
            candidate.status = "superseded"
            candidate.reviewed_at = datetime.now(UTC)
        if changed:
            db.add(candidate)


def dedupe_note_entities(db: Session, entity_id: str) -> None:
    rows = db.scalars(select(NoteEntity).where(NoteEntity.entity_id == entity_id).order_by(NoteEntity.created_at.asc())).all()
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (row.note_id, row.entity_id)
        if key in seen:
            db.delete(row)
            continue
        seen.add(key)


def dedupe_note_events(db: Session, event_id: str) -> None:
    rows = db.scalars(select(NoteEvent).where(NoteEvent.event_id == event_id).order_by(NoteEvent.created_at.asc())).all()
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (row.note_id, row.event_id)
        if key in seen:
            db.delete(row)
            continue
        seen.add(key)


def dedupe_event_entities_for_entity(db: Session, entity_id: str) -> None:
    rows = db.scalars(select(EventEntity).where(EventEntity.entity_id == entity_id).order_by(EventEntity.created_at.asc())).all()
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (row.event_id, row.entity_id)
        if key in seen:
            db.delete(row)
            continue
        seen.add(key)


def dedupe_event_entities_for_event(db: Session, event_id: str) -> None:
    rows = db.scalars(select(EventEntity).where(EventEntity.event_id == event_id).order_by(EventEntity.created_at.asc())).all()
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (row.event_id, row.entity_id)
        if key in seen:
            db.delete(row)
            continue
        seen.add(key)


def dedupe_entity_aliases(db: Session, entity: Entity) -> None:
    rows = list_entity_alias_rows(db, entity.id)
    seen: set[str] = set()
    for row in rows:
        if row.normalized_alias in seen:
            db.delete(row)
            continue
        seen.add(row.normalized_alias)


def dedupe_timeline_items(db: Session, event_id: str) -> None:
    rows = db.scalars(select(TimelineItem).where(TimelineItem.event_id == event_id).order_by(TimelineItem.created_at.asc())).all()
    seen_event = False
    for row in rows:
        if seen_event:
            db.delete(row)
            continue
        seen_event = True


def dedupe_style_views(db: Session, *, target_type: str, target_id: str) -> None:
    rows = db.scalars(
        select(StyleView)
        .where(StyleView.target_type == target_type, StyleView.target_id == target_id)
        .order_by(StyleView.created_at.asc())
    ).all()
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        key = (row.target_type, row.target_id, row.style_type)
        if key in seen:
            db.delete(row)
            continue
        seen.add(key)


def dedupe_relations(db: Session, *, user_id: str, affected_ids: set[str]) -> None:
    rows = db.scalars(
        select(Relation)
        .where(
            Relation.user_id == user_id,
            or_(Relation.source_id.in_(affected_ids), Relation.target_id.in_(affected_ids)),
        )
        .order_by(Relation.created_at.asc())
    ).all()
    seen: dict[tuple[str, str, str, str, str], Relation] = {}
    for row in rows:
        key = (row.source_type, row.source_id, row.relation_type, row.target_type, row.target_id)
        if key not in seen:
            seen[key] = row
            continue
        keeper = seen[key]
        keeper.evidence_count = (keeper.evidence_count or 0) + (row.evidence_count or 0)
        keeper.confidence_score = max_nullable(keeper.confidence_score, row.confidence_score)
        db.add(keeper)
        db.delete(row)


def choose_richer_text(left: str | None, right: str | None) -> str | None:
    if not left:
        return right
    if not right:
        return left
    return left if len(left) >= len(right) else right


def max_nullable(left: float | None, right: float | None) -> float | None:
    if left is None:
        return right
    if right is None:
        return left
    return max(left, right)


def min_nullable_datetime(left: datetime | None, right: datetime | None) -> datetime | None:
    if left is None:
        return right
    if right is None:
        return left
    return min(left, right)


def max_nullable_datetime(left: datetime | None, right: datetime | None) -> datetime | None:
    if left is None:
        return right
    if right is None:
        return left
    return max(left, right)

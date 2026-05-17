from dataclasses import dataclass
from datetime import UTC, datetime
from math import sqrt

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.embedding import Embedding
from app.models.entity import Entity, EventEntity, NoteEntity, NoteEvent, Relation
from app.models.event import Event, TimelineItem
from app.models.extraction import ExtractionEvidence, MergeCandidate
from app.models.note import Note, NoteChunk
from app.models.raw_asset import RawAsset
from app.models.style_view import StyleView
from app.domains.knowledge.aliases import upsert_entity_alias_value
from app.domains.knowledge.embeddings import upsert_embedding
from app.utils.text import text_to_vector


@dataclass(frozen=True)
class ProjectionResult:
    note_id: str
    event_id: str
    extractor_name: str
    extractor_version: str
    entity_count: int
    relation_count: int
    similarity_hint_count: int


def cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = sqrt(sum(value * value for value in left)) or 1.0
    right_norm = sqrt(sum(value * value for value in right)) or 1.0
    return float(dot / (left_norm * right_norm))


def replace_merge_candidates(
    db: Session,
    *,
    user_id: str,
    object_type: str,
    source_id: str,
    source_vector: list[float],
    threshold: float,
    reason: str,
) -> None:
    existing_candidates = db.scalars(
        select(MergeCandidate).where(
            MergeCandidate.user_id == user_id,
            MergeCandidate.object_type == object_type,
            MergeCandidate.source_id == source_id,
        )
    ).all()
    for candidate in existing_candidates:
        db.delete(candidate)

    candidate_embeddings = db.scalars(
        select(Embedding).where(
            Embedding.owner_type == object_type,
            Embedding.owner_id != source_id,
        )
    ).all()
    best_by_owner_id: dict[str, tuple[float, Embedding]] = {}
    for embedding in candidate_embeddings:
        score = cosine_similarity(source_vector, embedding.vector)
        if score >= threshold:
            current = best_by_owner_id.get(embedding.owner_id)
            if current is None or score > current[0]:
                best_by_owner_id[embedding.owner_id] = (score, embedding)

    scored = list(best_by_owner_id.values())
    scored.sort(key=lambda item: item[0], reverse=True)
    for score, embedding in scored[:5]:
        db.add(
            MergeCandidate(
                user_id=user_id,
                object_type=object_type,
                source_id=source_id,
                candidate_id=embedding.owner_id,
                score=round(score, 4),
                reason_json={"strategy": "embedding_similarity", "reason": reason},
                status="pending",
            )
        )


def delete_rows(db: Session, model: type, *conditions: object) -> None:
    rows = db.scalars(select(model).where(and_(*conditions))).all()
    for row in rows:
        db.delete(row)


def clear_note_projection(db: Session, note_id: str) -> None:
    delete_rows(db, NoteEntity, NoteEntity.note_id == note_id)
    delete_rows(db, NoteEvent, NoteEvent.note_id == note_id)
    delete_rows(db, ExtractionEvidence, ExtractionEvidence.source_note_id == note_id)
    delete_rows(db, TimelineItem, TimelineItem.note_id == note_id)
    delete_rows(db, Relation, Relation.source_type == "note", Relation.source_id == note_id)
    delete_rows(db, StyleView, StyleView.target_type == "note", StyleView.target_id == note_id)
    delete_rows(db, Embedding, Embedding.owner_type == "note", Embedding.owner_id == note_id)


def clear_event_projection(db: Session, event_id: str) -> None:
    delete_rows(db, EventEntity, EventEntity.event_id == event_id)
    delete_rows(db, TimelineItem, TimelineItem.event_id == event_id)
    delete_rows(db, Relation, Relation.target_type == "event", Relation.target_id == event_id)
    delete_rows(db, StyleView, StyleView.target_type == "event", StyleView.target_id == event_id)
    delete_rows(db, Embedding, Embedding.owner_type == "event", Embedding.owner_id == event_id)


def clear_entity_projection(db: Session, entity_id: str) -> None:
    delete_rows(db, StyleView, StyleView.target_type == "entity", StyleView.target_id == entity_id)
    delete_rows(db, Embedding, Embedding.owner_type == "entity", Embedding.owner_id == entity_id)


def upsert_entity_from_payload(db: Session, user_id: str, payload: dict) -> Entity:
    normalized_name = payload["resolution_hint"]["normalized_name"]
    entity = db.scalar(
        select(Entity).where(
            and_(
                Entity.user_id == user_id,
                Entity.entity_type == payload["entity_type"],
                Entity.normalized_name == normalized_name,
            )
        )
    )
    if entity:
        entity.last_seen_at = datetime.now(UTC)
        db.add(entity)
        return entity

    entity = Entity(
        user_id=user_id,
        entity_type=payload["entity_type"],
        canonical_name=payload["canonical_name"],
        display_name=payload["name"],
        description=payload.get("description"),
        alias_json=[],
        normalized_name=normalized_name,
        confidence_score=payload.get("confidence"),
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )
    db.add(entity)
    db.flush()
    return entity


def upsert_event_from_payload(db: Session, user_id: str, note_id: str, payload: dict) -> Event:
    timeline_sort_time = datetime.fromisoformat(payload["time"]["timeline_sort_time"])
    start_time = datetime.fromisoformat(payload["time"]["start_time"]) if payload["time"]["start_time"] else None
    event = db.scalar(
        select(Event).where(
            and_(
                Event.user_id == user_id,
                Event.title == payload["title"],
                Event.timeline_sort_time == timeline_sort_time,
            )
        )
    )
    if event:
        event.summary = payload["summary"]
        event.description = payload["description"]
        event.source_note_id = note_id
        event.location_text = payload.get("locations", [{}])[0].get("name") if payload.get("locations") else event.location_text
        db.add(event)
        return event

    event = Event(
        user_id=user_id,
        title=payload["title"],
        summary=payload["summary"],
        description=payload["description"],
        event_type=payload.get("event_type"),
        source_note_id=note_id,
        start_time=start_time,
        end_time=datetime.fromisoformat(payload["time"]["end_time"]) if payload["time"]["end_time"] else None,
        time_precision=payload["time"]["time_precision"],
        time_text=payload["time"]["time_text"],
        timeline_sort_time=timeline_sort_time,
        location_text=payload.get("locations", [{}])[0].get("name") if payload.get("locations") else None,
        confidence_score=payload.get("confidence"),
    )
    db.add(event)
    db.flush()
    return event


def resolve_relation_object_id(reference: dict, object_id_map: dict[str, dict[str, str]], note_id: str) -> str | None:
    object_type = reference.get("type")
    if object_type == "note":
        return reference.get("id") or note_id
    if object_type not in object_id_map:
        return None
    if reference.get("id") and reference["id"] in object_id_map[object_type]:
        return object_id_map[object_type][reference["id"]]
    if reference.get("temp_id") and reference["temp_id"] in object_id_map[object_type]:
        return object_id_map[object_type][reference["temp_id"]]
    return None


def apply_similarity_hints(
    db: Session,
    *,
    user_id: str,
    note_id: str,
    event_id: str,
    temp_entity_map: dict[str, str],
    similarity_hints: list[dict],
) -> None:
    for hint in similarity_hints:
        target_type = hint.get("target_type")
        target_id = hint.get("target_id")
        if target_type not in {"note", "event", "entity"} or not target_id:
            continue

        if target_type == "note":
            source_id = note_id
        elif target_type == "event":
            source_id = event_id
        else:
            source_id = temp_entity_map.get(hint.get("source_temp_id", "")) or next(iter(temp_entity_map.values()), None)

        if not source_id or source_id == target_id:
            continue

        db.add(
            MergeCandidate(
                user_id=user_id,
                object_type=target_type,
                source_id=source_id,
                candidate_id=target_id,
                score=round(float(hint.get("confidence", 0.5)), 4),
                reason_json={
                    "strategy": "llm_similarity_hint",
                    "reason": hint.get("reason", "Potential related item suggested by LLM."),
                },
                status="pending",
            )
        )


def persist_extraction_projection(
    db: Session,
    *,
    note: Note,
    asset: RawAsset,
    payload: dict,
    text: str,
) -> ProjectionResult:
    note.title = payload["summary"]["title"]
    note.summary = payload["summary"]["short_summary"]
    note.canonical_text = payload["summary"]["canonical_text"]
    note.category = payload["summary"]["category"]
    note.status = "ready"
    note.primary_time = datetime.fromisoformat(payload["events"][0]["time"]["timeline_sort_time"])
    note.processed_at = datetime.now(UTC)
    db.add(note)

    for chunk in list(note.chunks):
        db.delete(chunk)
    note_chunk = NoteChunk(
        note_id=note.id,
        chunk_index=0,
        content=text,
        token_count=len(text),
    )
    db.add(note_chunk)
    clear_note_projection(db, note.id)
    db.flush()

    temp_entity_map: dict[str, str] = {}
    for entity_payload in payload["entities"]:
        entity = upsert_entity_from_payload(db, note.user_id, entity_payload)
        clear_entity_projection(db, entity.id)
        db.flush()
        for alias in entity_payload.get("aliases", []):
            upsert_entity_alias_value(db, entity=entity, alias=alias, alias_type="extracted")
        temp_entity_map[entity_payload["temp_id"]] = entity.id
        db.add(
            NoteEntity(
                note_id=note.id,
                entity_id=entity.id,
                mention_text=entity_payload["evidence"][0]["text"] if entity_payload["evidence"] else None,
                confidence_score=entity_payload.get("confidence"),
            )
        )
        db.add(
            ExtractionEvidence(
                user_id=note.user_id,
                source_note_id=note.id,
                source_asset_id=asset.id,
                target_type="entity",
                target_id=entity.id,
                field_name="canonical_name",
                evidence_text=entity_payload["evidence"][0]["text"] if entity_payload["evidence"] else entity.display_name,
                evidence_offset_start=entity_payload["evidence"][0]["start"] if entity_payload["evidence"] else None,
                evidence_offset_end=entity_payload["evidence"][0]["end"] if entity_payload["evidence"] else None,
                extractor_name=payload["source"]["extractor_name"],
                extractor_version=payload["source"]["extractor_version"],
                confidence_score=entity_payload.get("confidence"),
            )
        )
        entity_vector = text_to_vector(entity.display_name)
        upsert_embedding(db, owner_type="entity", owner_id=entity.id, vector=entity_vector, model_name="heuristic-v1")
        replace_merge_candidates(
            db,
            user_id=note.user_id,
            object_type="entity",
            source_id=entity.id,
            source_vector=entity_vector,
            threshold=0.95,
            reason="Potential duplicate entity based on embedding similarity.",
        )

    event_payload = payload["events"][0]
    event = upsert_event_from_payload(db, note.user_id, note.id, event_payload)
    clear_event_projection(db, event.id)
    db.flush()
    db.add(
        NoteEvent(
            note_id=note.id,
            event_id=event.id,
            mention_text=event_payload["evidence"][0]["text"] if event_payload["evidence"] else event.title,
            confidence_score=event_payload.get("confidence"),
        )
    )
    db.add(
        ExtractionEvidence(
            user_id=note.user_id,
            source_note_id=note.id,
            source_asset_id=asset.id,
            target_type="event",
            target_id=event.id,
            field_name="title",
            evidence_text=event_payload["evidence"][0]["text"] if event_payload["evidence"] else event.title,
            evidence_offset_start=event_payload["evidence"][0]["start"] if event_payload["evidence"] else None,
            evidence_offset_end=event_payload["evidence"][0]["end"] if event_payload["evidence"] else None,
            extractor_name=payload["source"]["extractor_name"],
            extractor_version=payload["source"]["extractor_version"],
            confidence_score=event_payload.get("confidence"),
        )
    )

    for index, participant in enumerate(event_payload["participants"]):
        entity_id = temp_entity_map.get(participant["entity_temp_id"])
        if not entity_id:
            continue
        entity = db.get(Entity, entity_id)
        if entity:
            apply_entity_seen_time_from_event(entity, event)
            db.add(entity)
        db.add(
            EventEntity(
                event_id=event.id,
                entity_id=entity_id,
                role=participant.get("role"),
                relation_type=participant["relation_type"],
                display_order=index,
                confidence_score=event_payload.get("confidence"),
            )
        )

    object_id_map = {
        "note": {note.id: note.id},
        "event": {event_payload["temp_id"]: event.id},
        "entity": temp_entity_map,
    }

    for relation_payload in payload["relations"]:
        source_ref = relation_payload["source_ref"]
        target_ref = relation_payload["target_ref"]
        relation_type = relation_payload["relation_type"]
        if relation_type == "participates_in" and {source_ref["type"], target_ref["type"]} == {"entity", "event"}:
            continue
        source_id = resolve_relation_object_id(source_ref, object_id_map, note.id)
        target_id = resolve_relation_object_id(target_ref, object_id_map, note.id)
        if source_id and target_id:
            db.add(
                Relation(
                    user_id=note.user_id,
                    source_type=source_ref["type"],
                    source_id=source_id,
                    relation_type=relation_type,
                    target_type=target_ref["type"],
                    target_id=target_id,
                    evidence_count=max(1, len(relation_payload.get("evidence", []))),
                    confidence_score=relation_payload.get("confidence"),
                    meta_json={"source": "llm_relation"},
                )
            )
            if relation_payload.get("evidence"):
                evidence = relation_payload["evidence"][0]
                db.add(
                    ExtractionEvidence(
                        user_id=note.user_id,
                        source_note_id=note.id,
                        source_asset_id=asset.id,
                        target_type="relation",
                        target_id=source_id,
                        field_name=relation_type,
                        evidence_text=evidence.get("text") or relation_type,
                        evidence_offset_start=evidence.get("start"),
                        evidence_offset_end=evidence.get("end"),
                        extractor_name=payload["source"]["extractor_name"],
                        extractor_version=payload["source"]["extractor_version"],
                        confidence_score=relation_payload.get("confidence"),
                    )
                )

    timeline_payload = payload["timeline"][0]
    db.add(
        TimelineItem(
            user_id=note.user_id,
            event_id=event.id,
            note_id=note.id,
            title=timeline_payload["title"],
            summary=timeline_payload["summary"],
            display_time=timeline_payload["display_time"],
            sort_time=datetime.fromisoformat(timeline_payload["sort_time"]),
            time_precision=timeline_payload["time_precision"],
            importance_score=timeline_payload["importance_score"],
        )
    )

    upsert_embedding(db, owner_type="note", owner_id=note.id, vector=payload["embedding"], model_name="heuristic-v1")
    event_vector = text_to_vector(event.title)
    upsert_embedding(db, owner_type="event", owner_id=event.id, vector=event_vector, model_name="heuristic-v1")
    replace_merge_candidates(
        db,
        user_id=note.user_id,
        object_type="note",
        source_id=note.id,
        source_vector=payload["embedding"],
        threshold=0.9,
        reason="Potential duplicate note based on embedding similarity.",
    )
    replace_merge_candidates(
        db,
        user_id=note.user_id,
        object_type="event",
        source_id=event.id,
        source_vector=event_vector,
        threshold=0.95,
        reason="Potential duplicate event based on embedding similarity.",
    )
    apply_similarity_hints(
        db,
        user_id=note.user_id,
        note_id=note.id,
        event_id=event.id,
        temp_entity_map=temp_entity_map,
        similarity_hints=payload.get("similarity_hints", []),
    )

    persist_style_views(
        db,
        user_id=note.user_id,
        note_id=note.id,
        event=event,
        temp_entity_map=temp_entity_map,
        style_payload=payload["style_payload"],
    )

    return ProjectionResult(
        note_id=note.id,
        event_id=event.id,
        extractor_name=payload["source"]["extractor_name"],
        extractor_version=payload["source"]["extractor_version"],
        entity_count=len(payload["entities"]),
        relation_count=len(payload["relations"]),
        similarity_hint_count=len(payload.get("similarity_hints", [])),
    )


def apply_entity_seen_time_from_event(entity: Entity, event: Event) -> None:
    event_time = event.timeline_sort_time or event.start_time
    if event_time is None:
        return
    if entity.first_seen_at is None or event_time < entity.first_seen_at:
        entity.first_seen_at = event_time
    if entity.last_seen_at is None or event_time > entity.last_seen_at:
        entity.last_seen_at = event_time


def persist_style_views(
    db: Session,
    *,
    user_id: str,
    note_id: str,
    event: Event,
    temp_entity_map: dict[str, str],
    style_payload: dict,
) -> None:
    story_body = build_story_body(style_payload)
    db.add(
        StyleView(
            user_id=user_id,
            target_type="note",
            target_id=note_id,
            style_type="chunibyo",
            title=style_payload["title"],
            content=story_body,
        )
    )
    db.add(
        StyleView(
            user_id=user_id,
            target_type="event",
            target_id=event.id,
            style_type="chunibyo",
            title=f"事件档案：{event.title}",
            content=story_body,
        )
    )

    for entity_payload in style_payload.get("character_cards", []):
        entity_id = temp_entity_map.get(entity_payload["entity_temp_id"])
        if entity_id:
            db.add(
                StyleView(
                    user_id=user_id,
                    target_type="entity",
                    target_id=entity_id,
                    style_type="chunibyo",
                    title=f"{entity_payload['display_name']} / {entity_payload['epithet']}",
                    content=entity_payload["aura"],
                )
            )


def build_story_body(style_payload: dict) -> str:
    return "\n".join(
        part["body"] for part in style_payload.get("event_narrative", []) if part.get("body")
    )

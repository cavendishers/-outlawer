from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.entity import Entity, EventEntity
from app.models.event import Event, TimelineItem
from app.models.extraction import MergeCandidate
from app.models.note import Note
from app.utils.text import normalize_name


def build_related_event_suggestions(
    current_event: dict[str, Any],
    candidate_events: list[dict[str, Any]],
    merge_score_map: dict[str, float],
) -> list[dict[str, Any]]:
    current_participants = {
        participant["id"]: participant["display_name"]
        for participant in current_event.get("participants", [])
        if participant.get("id")
    }
    current_location = normalize_name(current_event.get("location_text") or "")
    current_sort_time = parse_iso_datetime(current_event.get("sort_time"))

    related_events: list[dict[str, Any]] = []
    for candidate in candidate_events:
        candidate_participants = {
            participant["id"]: participant["display_name"]
            for participant in candidate.get("participants", [])
            if participant.get("id")
        }
        shared_participants = [
            current_participants[participant_id]
            for participant_id in current_participants
            if participant_id in candidate_participants
        ]
        candidate_sort_time = parse_iso_datetime(candidate.get("sort_time"))
        candidate_location = normalize_name(candidate.get("location_text") or "")

        connection_reasons: list[str] = []
        score = 0.0

        if shared_participants:
            connection_reasons.append("共享人物")
            score += min(0.48, 0.18 * len(shared_participants))

        day_distance = compute_day_distance(current_sort_time, candidate_sort_time)
        if day_distance == 0:
            connection_reasons.append("同日记录")
            score += 0.2
        elif day_distance is not None and day_distance <= 3:
            connection_reasons.append("时间接近")
            score += max(0.08, 0.18 - (day_distance * 0.03))

        if current_location and candidate_location and current_location == candidate_location:
            connection_reasons.append("同地点")
            score += 0.14

        merge_score = merge_score_map.get(candidate["id"])
        if merge_score:
            connection_reasons.append("语义相近")
            score += min(0.28, merge_score * 0.28)

        if not connection_reasons:
            continue

        related_events.append(
            {
                "id": candidate["id"],
                "title": candidate["title"],
                "summary": candidate.get("summary"),
                "time_text": candidate.get("time_text"),
                "event_type": candidate.get("event_type"),
                "connection_score": round(min(score, 0.99), 2),
                "connection_reasons": connection_reasons,
                "shared_participants": shared_participants[:3],
                "distance_days": day_distance,
                "source_note_title": candidate.get("source_note_title"),
            }
        )

    related_events.sort(
        key=lambda item: (
            item["connection_score"],
            item["time_text"] or "",
            item["title"],
        ),
        reverse=True,
    )
    return related_events[:6]


def build_entity_timeline_fragments(event_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sorted_rows = sorted(
        event_rows,
        key=lambda item: (
            item.get("sort_time") or "",
            item.get("title") or "",
        ),
    )
    total = len(sorted_rows)
    fragments: list[dict[str, Any]] = []
    for index, item in enumerate(sorted_rows):
        if total == 1:
            chapter_label = "唯一锚点"
        elif index == 0:
            chapter_label = "初现"
        elif index == total - 1:
            chapter_label = "最近回响"
        else:
            chapter_label = f"轨迹 {index + 1:02d}"

        fragments.append(
            {
                "event_id": item["id"],
                "title": item["title"],
                "summary": item.get("summary"),
                "time_text": item.get("time_text"),
                "event_type": item.get("event_type"),
                "location_text": item.get("location_text"),
                "role": item.get("role"),
                "relation_type": item.get("relation_type"),
                "chapter_label": chapter_label,
                "source_note_title": item.get("source_note_title"),
                "position": index + 1,
                "total": total,
            }
        )
    return fragments


def build_graph_overview_network(
    event_rows: list[dict[str, Any]],
    entity_rows: list[dict[str, Any]],
    event_entity_links: list[dict[str, Any]],
    event_event_links: list[dict[str, Any]],
    timeline_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    nodes = [
        {
            "id": event["id"],
            "node_type": "event",
            "label": event["title"],
            "subtitle": event.get("time_text") or event.get("event_type") or "事件节点",
            "href": f"/events/{event['id']}",
            "importance": event.get("importance", 0.7),
            "meta": [item for item in [event.get("event_type"), event.get("time_text"), event.get("location_text")] if item],
        }
        for event in event_rows
    ]
    nodes.extend(
        {
            "id": entity["id"],
            "node_type": "entity",
            "label": entity["display_name"],
            "subtitle": entity.get("entity_type") or "角色节点",
            "href": f"/story/entity/{entity['id']}",
            "importance": entity.get("importance", 0.6),
            "meta": [item for item in [entity.get("entity_type"), entity.get("description")] if item],
        }
        for entity in entity_rows
    )

    edges = []
    seen_edge_keys: set[tuple[str, str, str]] = set()
    for link in event_entity_links:
        edge_key = (link["event_id"], link["entity_id"], "participates_in")
        if edge_key in seen_edge_keys:
            continue
        seen_edge_keys.add(edge_key)
        edges.append(
            {
                "source_id": link["event_id"],
                "target_id": link["entity_id"],
                "edge_type": "participates_in",
                "label": link.get("role") or link.get("relation_type") or "参与",
                "weight": round(float(link.get("weight", 0.6)), 2),
            }
        )

    for link in event_event_links:
        source_id, target_id = sorted([link["source_id"], link["target_id"]])
        edge_key = (source_id, target_id, "relates_to")
        if edge_key in seen_edge_keys:
            continue
        seen_edge_keys.add(edge_key)
        edges.append(
            {
                "source_id": source_id,
                "target_id": target_id,
                "edge_type": "relates_to",
                "label": " / ".join(link.get("reasons", [])[:3]) or "关联",
                "weight": round(float(link.get("weight", 0.5)), 2),
            }
        )

    return {
        "stats": {
            "event_count": len(event_rows),
            "entity_count": len(entity_rows),
            "timeline_count": len(timeline_rows),
            "edge_count": len(edges),
        },
        "nodes": nodes,
        "edges": edges,
        "timeline_focus": timeline_rows[:10],
    }


def get_related_events_for_event(db: Session, user_id: str, event: Event) -> list[dict[str, Any]]:
    candidate_events = db.scalars(
        select(Event).where(Event.user_id == user_id, Event.id != event.id).order_by(Event.timeline_sort_time.desc())
    ).all()
    if not candidate_events:
        return []

    event_ids = [event.id, *[candidate.id for candidate in candidate_events]]
    links = db.scalars(select(EventEntity).where(EventEntity.event_id.in_(event_ids))).all()
    entity_ids = {link.entity_id for link in links}
    entities = {
        entity.id: entity.display_name
        for entity in db.scalars(select(Entity).where(Entity.id.in_(entity_ids))).all()
    }
    notes = {
        note.id: note.title
        for note in db.scalars(select(Note).where(Note.id.in_([candidate.source_note_id for candidate in candidate_events if candidate.source_note_id]))).all()
    }

    participant_map: dict[str, list[dict[str, str]]] = {event_id: [] for event_id in event_ids}
    for link in links:
        display_name = entities.get(link.entity_id)
        if not display_name:
            continue
        participant_map.setdefault(link.event_id, []).append({"id": link.entity_id, "display_name": display_name})

    merge_candidates = db.scalars(
        select(MergeCandidate).where(
            MergeCandidate.user_id == user_id,
            MergeCandidate.object_type == "event",
            or_(
                (MergeCandidate.source_id == event.id),
                (MergeCandidate.candidate_id == event.id),
            ),
        )
    ).all()
    merge_score_map: dict[str, float] = {}
    for candidate in merge_candidates:
        other_id = candidate.candidate_id if candidate.source_id == event.id else candidate.source_id
        merge_score_map[other_id] = max(float(candidate.score), merge_score_map.get(other_id, 0.0))

    current_event_snapshot = {
        "id": event.id,
        "participants": participant_map.get(event.id, []),
        "location_text": event.location_text,
        "sort_time": event.timeline_sort_time.isoformat() if event.timeline_sort_time else None,
    }
    candidate_snapshots = [
        {
            "id": candidate.id,
            "title": candidate.title,
            "summary": candidate.summary,
            "time_text": candidate.time_text,
            "event_type": candidate.event_type,
            "location_text": candidate.location_text,
            "sort_time": candidate.timeline_sort_time.isoformat() if candidate.timeline_sort_time else None,
            "participants": participant_map.get(candidate.id, []),
            "source_note_title": notes.get(candidate.source_note_id),
        }
        for candidate in candidate_events
    ]
    return build_related_event_suggestions(current_event_snapshot, candidate_snapshots, merge_score_map)


def get_timeline_fragments_for_entity(db: Session, user_id: str, entity_id: str) -> list[dict[str, Any]]:
    links = db.scalars(select(EventEntity).where(EventEntity.entity_id == entity_id).order_by(EventEntity.display_order.asc())).all()
    if not links:
        return []

    event_ids = [link.event_id for link in links]
    events = {
        event.id: event
        for event in db.scalars(select(Event).where(Event.user_id == user_id, Event.id.in_(event_ids))).all()
    }
    notes = {
        note.id: note.title
        for note in db.scalars(select(Note).where(Note.id.in_([event.source_note_id for event in events.values() if event.source_note_id]))).all()
    }

    rows: list[dict[str, Any]] = []
    seen_event_ids: set[str] = set()
    for link in links:
        event = events.get(link.event_id)
        if not event or event.id in seen_event_ids:
            continue
        seen_event_ids.add(event.id)
        rows.append(
            {
                "id": event.id,
                "title": event.title,
                "summary": event.summary,
                "time_text": event.time_text,
                "event_type": event.event_type,
                "location_text": event.location_text,
                "sort_time": event.timeline_sort_time.isoformat() if event.timeline_sort_time else None,
                "role": link.role,
                "relation_type": link.relation_type,
                "source_note_title": notes.get(event.source_note_id),
            }
        )

    return build_entity_timeline_fragments(rows)


def get_graph_overview(db: Session, user_id: str) -> dict[str, Any]:
    timeline_items = db.scalars(
        select(TimelineItem).where(TimelineItem.user_id == user_id).order_by(TimelineItem.sort_time.desc())
    ).all()
    timeline_rows = [
        {
            "id": item.id,
            "event_id": item.event_id,
            "note_id": item.note_id,
            "title": item.title,
            "summary": item.summary,
            "display_time": item.display_time,
            "sort_time": item.sort_time.isoformat() if item.sort_time else None,
            "time_precision": item.time_precision,
        }
        for item in timeline_items[:14]
    ]

    recent_event_ids = []
    for item in timeline_rows:
        if item["event_id"] and item["event_id"] not in recent_event_ids:
            recent_event_ids.append(item["event_id"])
    if not recent_event_ids:
        recent_event_ids = [
            event.id
            for event in db.scalars(
                select(Event).where(Event.user_id == user_id).order_by(Event.timeline_sort_time.desc()).limit(8)
            ).all()
        ]

    if not recent_event_ids:
        return build_graph_overview_network([], [], [], [], timeline_rows)

    events = db.scalars(select(Event).where(Event.user_id == user_id, Event.id.in_(recent_event_ids))).all()
    event_map = {event.id: event for event in events}
    ordered_events = [event_map[event_id] for event_id in recent_event_ids if event_id in event_map][:8]
    ordered_event_ids = [event.id for event in ordered_events]

    note_title_map = {
        note.id: note.title
        for note in db.scalars(
            select(Note).where(Note.id.in_([event.source_note_id for event in ordered_events if event.source_note_id]))
        ).all()
    }
    event_rows = [
        {
            "id": event.id,
            "title": event.title,
            "event_type": event.event_type,
            "time_text": event.time_text,
            "location_text": event.location_text,
            "source_note_title": note_title_map.get(event.source_note_id),
            "importance": float(event.confidence_score or 0.7),
        }
        for event in ordered_events
    ]

    event_links = db.scalars(select(EventEntity).where(EventEntity.event_id.in_(ordered_event_ids))).all()
    entity_frequency: dict[str, int] = {}
    for link in event_links:
        entity_frequency[link.entity_id] = entity_frequency.get(link.entity_id, 0) + 1

    ordered_entity_ids = [
        entity_id
        for entity_id, _ in sorted(
            entity_frequency.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ][:10]
    entity_map = {
        entity.id: entity
        for entity in db.scalars(select(Entity).where(Entity.id.in_(ordered_entity_ids))).all()
    }
    entity_rows = [
        {
            "id": entity_id,
            "display_name": entity_map[entity_id].display_name,
            "entity_type": entity_map[entity_id].entity_type,
            "description": entity_map[entity_id].description,
            "importance": min(1.0, 0.42 + (entity_frequency.get(entity_id, 1) * 0.14)),
        }
        for entity_id in ordered_entity_ids
        if entity_id in entity_map
    ]

    event_entity_links = [
        {
            "event_id": link.event_id,
            "entity_id": link.entity_id,
            "role": link.role,
            "relation_type": link.relation_type,
            "weight": float(link.confidence_score or 0.7),
        }
        for link in event_links
        if link.event_id in ordered_event_ids and link.entity_id in entity_map
    ]

    merge_candidates = db.scalars(
        select(MergeCandidate).where(
            MergeCandidate.user_id == user_id,
            MergeCandidate.object_type == "event",
            MergeCandidate.source_id.in_(ordered_event_ids),
            MergeCandidate.candidate_id.in_(ordered_event_ids),
        )
    ).all()
    merge_score_map: dict[tuple[str, str], float] = {}
    for candidate in merge_candidates:
        pair_key = tuple(sorted([candidate.source_id, candidate.candidate_id]))
        merge_score_map[pair_key] = max(float(candidate.score), merge_score_map.get(pair_key, 0.0))

    participant_map: dict[str, list[dict[str, str]]] = {event_id: [] for event_id in ordered_event_ids}
    for link in event_links:
        entity = entity_map.get(link.entity_id)
        if not entity or link.event_id not in participant_map:
            continue
        participant_map[link.event_id].append({"id": entity.id, "display_name": entity.display_name})

    event_event_links = []
    for index, event in enumerate(ordered_events):
        current_snapshot = {
            "id": event.id,
            "participants": participant_map.get(event.id, []),
            "location_text": event.location_text,
            "sort_time": event.timeline_sort_time.isoformat() if event.timeline_sort_time else None,
        }
        candidate_snapshots = []
        for candidate in ordered_events[index + 1:]:
            candidate_snapshots.append(
                {
                    "id": candidate.id,
                    "title": candidate.title,
                    "summary": candidate.summary,
                    "time_text": candidate.time_text,
                    "event_type": candidate.event_type,
                    "location_text": candidate.location_text,
                    "sort_time": candidate.timeline_sort_time.isoformat() if candidate.timeline_sort_time else None,
                    "participants": participant_map.get(candidate.id, []),
                    "source_note_title": note_title_map.get(candidate.source_note_id),
                }
            )
        suggestions = build_related_event_suggestions(
            current_snapshot,
            candidate_snapshots,
            {
                candidate_id: score
                for (left_id, candidate_id), score in merge_score_map.items()
                if left_id == event.id
            }
            | {
                left_id: score
                for (left_id, right_id), score in merge_score_map.items()
                if right_id == event.id
            },
        )
        for suggestion in suggestions:
            if suggestion["id"] not in ordered_event_ids:
                continue
            event_event_links.append(
                {
                    "source_id": event.id,
                    "target_id": suggestion["id"],
                    "reasons": suggestion["connection_reasons"],
                    "weight": suggestion["connection_score"],
                }
            )

    return build_graph_overview_network(
        event_rows,
        entity_rows,
        event_entity_links,
        event_event_links,
        timeline_rows,
    )


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def compute_day_distance(left: datetime | None, right: datetime | None) -> int | None:
    if not left or not right:
        return None
    return abs((right.date() - left.date()).days)

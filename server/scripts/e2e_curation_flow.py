import argparse
from datetime import UTC, datetime
from uuid import uuid4

import httpx
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.entity import Entity, EventEntity, Relation
from app.models.event import Event, TimelineItem
from app.models.note import Note
from app.models.user import User
from app.utils.text import normalize_name


def assert_ok(response: httpx.Response) -> dict:
    response.raise_for_status()
    payload = response.json()
    assert payload["code"] == 0, payload
    return payload["data"]


def seed_curation_fixture(username: str) -> dict[str, str]:
    suffix = uuid4().hex[:8]
    original_time = datetime(2026, 4, 18, 9, 30, tzinfo=UTC)

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username))
        assert user is not None, f"User {username} not found"

        note = Note(
            user_id=user.id,
            title=f"Curation Seed Note {suffix}",
            summary="事件校对 e2e 种子卷宗。",
            canonical_text="2026-04-18 张三记录了需要校对的图谱事件。",
            category="knowledge",
            status="ready",
            primary_time=original_time,
            processed_at=original_time,
        )
        db.add(note)
        db.flush()

        entity_a = Entity(
            user_id=user.id,
            entity_type="person",
            canonical_name=f"校对张三-{suffix}",
            display_name=f"校对张三-{suffix}",
            description="原始参与者",
            alias_json=[],
            normalized_name=normalize_name(f"校对张三-{suffix}"),
            status="active",
            confidence_score=0.9,
            first_seen_at=original_time,
            last_seen_at=original_time,
        )
        entity_b = Entity(
            user_id=user.id,
            entity_type="person",
            canonical_name=f"校对李四-{suffix}",
            display_name=f"校对李四-{suffix}",
            description="后续手动加入的参与者",
            alias_json=[],
            normalized_name=normalize_name(f"校对李四-{suffix}"),
            status="active",
            confidence_score=0.88,
            first_seen_at=original_time,
            last_seen_at=original_time,
        )
        db.add_all([entity_a, entity_b])
        db.flush()

        event = Event(
            user_id=user.id,
            title=f"待校对事件 {suffix}",
            summary="校对前摘要。",
            description="校对前描述。",
            event_type="meeting",
            status="active",
            source_note_id=note.id,
            start_time=original_time,
            time_precision="day",
            time_text="2026-04-18",
            timeline_sort_time=original_time,
            location_text="旧会议室",
            confidence_score=0.77,
        )
        related_event = Event(
            user_id=user.id,
            title=f"后续关联事件 {suffix}",
            summary="用于新增图谱关系的事件。",
            description="关联事件描述。",
            event_type="followup",
            status="active",
            source_note_id=note.id,
            start_time=datetime(2026, 4, 21, 10, 0, tzinfo=UTC),
            time_precision="day",
            time_text="2026-04-21",
            timeline_sort_time=datetime(2026, 4, 21, 10, 0, tzinfo=UTC),
            location_text="新会议室",
            confidence_score=0.75,
        )
        db.add_all([event, related_event])
        db.flush()

        db.add_all(
            [
                EventEntity(
                    event_id=event.id,
                    entity_id=entity_a.id,
                    role="记录者",
                    relation_type="participates_in",
                    display_order=0,
                    confidence_score=0.9,
                ),
                Relation(
                    user_id=user.id,
                    source_type="entity",
                    source_id=entity_a.id,
                    relation_type="participates_in",
                    target_type="event",
                    target_id=event.id,
                    evidence_count=1,
                    confidence_score=0.9,
                    meta_json={"source": "seed"},
                ),
                Relation(
                    user_id=user.id,
                    source_type="note",
                    source_id=note.id,
                    relation_type="source_of",
                    target_type="event",
                    target_id=event.id,
                    evidence_count=1,
                    confidence_score=1.0,
                    meta_json={"source": "seed"},
                ),
                TimelineItem(
                    user_id=user.id,
                    event_id=event.id,
                    note_id=note.id,
                    title=event.title,
                    summary=event.summary,
                    display_time=event.time_text,
                    sort_time=event.timeline_sort_time,
                    time_precision=event.time_precision,
                    importance_score=0.8,
                ),
            ]
        )
        db.commit()

        return {
            "user_id": user.id,
            "note_id": note.id,
            "entity_a_id": entity_a.id,
            "entity_b_id": entity_b.id,
            "event_id": event.id,
            "related_event_id": related_event.id,
            "updated_title": f"校对后的事件 {suffix}",
        }


def verify_database_state(ids: dict[str, str], relation_id: str) -> None:
    with SessionLocal() as db:
        event = db.get(Event, ids["event_id"])
        assert event is not None
        assert event.title == ids["updated_title"]
        assert event.location_text == "校对会议室B"
        assert event.time_text == "2026-04-20 09:15"

        timeline_item = db.scalar(select(TimelineItem).where(TimelineItem.event_id == event.id))
        assert timeline_item is not None
        assert timeline_item.title == ids["updated_title"]
        assert timeline_item.display_time == "2026-04-20 09:15"
        assert timeline_item.sort_time is not None
        assert timeline_item.sort_time.date().isoformat() == "2026-04-20"

        removed_participant = db.scalar(
            select(EventEntity).where(EventEntity.event_id == event.id, EventEntity.entity_id == ids["entity_b_id"])
        )
        assert removed_participant is None

        removed_relation = db.get(Relation, relation_id)
        assert removed_relation is None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="admin123456")
    args = parser.parse_args()

    client = httpx.Client(timeout=20.0, trust_env=False)
    health = assert_ok(client.get(f"{args.base_url}/health"))
    assert health["status"] == "healthy"

    login = assert_ok(client.post(f"{args.base_url}/auth/login", json={"username": args.username, "password": args.password}))
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    ids = seed_curation_fixture(args.username)

    context = assert_ok(client.get(f"{args.base_url}/curation/events/{ids['event_id']}", headers=headers))
    assert context["event"]["id"] == ids["event_id"]
    assert context["stats"]["participant_count"] == 1
    assert any(relation["relation_type"] == "source_of" for relation in context["relations"])

    updated = assert_ok(
        client.patch(
            f"{args.base_url}/curation/events/{ids['event_id']}",
            headers=headers,
            json={
                "title": ids["updated_title"],
                "summary": "校对后的摘要。",
                "description": "校对后的完整描述。",
                "event_type": "curated_meeting",
                "status": "verified",
                "time_precision": "time",
                "time_text": "2026-04-20 09:15",
                "location_text": "校对会议室B",
                "start_time": "2026-04-20T09:15:00+00:00",
                "timeline_sort_time": "2026-04-20T09:15:00+00:00",
            },
        )
    )
    assert updated["title"] == ids["updated_title"]
    assert updated["location_text"] == "校对会议室B"

    participant = assert_ok(
        client.post(
            f"{args.base_url}/curation/events/{ids['event_id']}/participants",
            headers=headers,
            json={"entity_id": ids["entity_b_id"], "role": "负责人", "relation_type": "facilitates"},
        )
    )
    assert participant["entity_id"] == ids["entity_b_id"]
    assert participant["relation_type"] == "facilitates"

    relation = assert_ok(
        client.post(
            f"{args.base_url}/curation/events/{ids['event_id']}/relations",
            headers=headers,
            json={
                "direction": "outgoing",
                "related_type": "event",
                "related_id": ids["related_event_id"],
                "relation_type": "occurs_before",
            },
        )
    )
    assert relation["relation_type"] == "occurs_before"
    assert relation["peer"]["id"] == ids["related_event_id"]

    updated_relation = assert_ok(
        client.patch(
            f"{args.base_url}/curation/events/{ids['event_id']}/relations/{relation['id']}",
            headers=headers,
            json={
                "direction": "incoming",
                "related_type": "note",
                "related_id": ids["note_id"],
                "relation_type": "documents",
            },
        )
    )
    assert updated_relation["id"] == relation["id"]
    assert updated_relation["direction"] == "incoming"
    assert updated_relation["relation_type"] == "documents"
    assert updated_relation["peer"]["id"] == ids["note_id"]

    refreshed = assert_ok(client.get(f"{args.base_url}/curation/events/{ids['event_id']}", headers=headers))
    assert any(item["id"] == ids["entity_b_id"] for item in refreshed["participants"])
    assert any(item["id"] == relation["id"] and item["relation_type"] == "documents" for item in refreshed["relations"])

    removed_relation = assert_ok(
        client.delete(f"{args.base_url}/curation/events/{ids['event_id']}/relations/{relation['id']}", headers=headers)
    )
    assert removed_relation["status"] == "removed"

    removed_participant = assert_ok(
        client.delete(f"{args.base_url}/curation/events/{ids['event_id']}/participants/{ids['entity_b_id']}", headers=headers)
    )
    assert removed_participant["status"] == "removed"

    final_context = assert_ok(client.get(f"{args.base_url}/curation/events/{ids['event_id']}", headers=headers))
    assert not any(item["id"] == ids["entity_b_id"] for item in final_context["participants"])
    assert not any(item["id"] == relation["id"] for item in final_context["relations"])

    verify_database_state(ids, relation["id"])
    print("Curation flow e2e passed")


if __name__ == "__main__":
    main()

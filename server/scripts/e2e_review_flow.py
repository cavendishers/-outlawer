import argparse
from datetime import UTC, datetime
from uuid import uuid4

import httpx
from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.models.entity import Entity, EntityAlias, EventEntity, NoteEntity, NoteEvent, Relation
from app.models.event import Event, TimelineItem
from app.models.extraction import MergeCandidate
from app.models.note import Note
from app.models.review import ReviewAction
from app.models.user import User
from app.utils.text import normalize_name


def assert_ok(response: httpx.Response) -> dict:
    response.raise_for_status()
    payload = response.json()
    assert payload["code"] == 0, payload
    return payload["data"]


def collect_merge_candidate_ids(
    client: httpx.Client,
    *,
    base_url: str,
    headers: dict[str, str],
    object_type: str,
    status: str,
    page_size: int = 100,
) -> set[str]:
    page = 1
    candidate_ids: set[str] = set()

    while True:
        payload = assert_ok(
            client.get(
                f"{base_url}/review/merge-candidates",
                headers=headers,
                params={
                    "status": status,
                    "object_type": object_type,
                    "page": page,
                    "page_size": page_size,
                },
            )
        )
        candidate_ids.update(item["id"] for item in payload["items"])
        if page >= payload["total_pages"] or not payload["items"]:
            return candidate_ids
        page += 1


def seed_review_fixture(username: str) -> dict[str, str]:
    suffix = uuid4().hex[:8]
    now = datetime(2026, 4, 18, 10, 30, tzinfo=UTC)

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username))
        assert user is not None, f"User {username} not found"

        note_a = Note(
            user_id=user.id,
            title=f"Review Seed Alpha {suffix}",
            summary="张三在项目启动会上确认图谱导入流程。",
            canonical_text="2026-04-18 张三在会议室A确认图谱导入流程。",
            category="knowledge",
            status="ready",
            primary_time=now,
            processed_at=now,
        )
        note_b = Note(
            user_id=user.id,
            title=f"Review Seed Beta {suffix}",
            summary="张三别名节点记录了同一场项目启动会。",
            canonical_text="2026-04-18 张三别名节点记录了同一场项目启动会。",
            category="knowledge",
            status="ready",
            primary_time=now,
            processed_at=now,
        )
        db.add_all([note_a, note_b])
        db.flush()

        entity_a = Entity(
            user_id=user.id,
            entity_type="person",
            canonical_name=f"张三-{suffix}",
            display_name=f"张三-{suffix}",
            description="审核流测试人物源节点",
            alias_json=[],
            normalized_name=normalize_name(f"张三-{suffix}"),
            status="active",
            confidence_score=0.92,
            first_seen_at=now,
            last_seen_at=now,
        )
        entity_b = Entity(
            user_id=user.id,
            entity_type="person",
            canonical_name=f"张三同名-{suffix}",
            display_name=f"张三同名-{suffix}",
            description="审核流测试人物候选节点",
            alias_json=[f"老张-{suffix}"],
            normalized_name=normalize_name(f"张三同名-{suffix}"),
            status="active",
            confidence_score=0.88,
            first_seen_at=now,
            last_seen_at=now,
        )
        db.add_all([entity_a, entity_b])
        db.flush()

        event_a = Event(
            user_id=user.id,
            title=f"项目启动会合并源 {suffix}",
            summary="源事件：张三确认图谱导入流程。",
            description="源事件完整描述",
            event_type="meeting",
            status="active",
            source_note_id=note_a.id,
            start_time=now,
            time_precision="day",
            time_text="2026-04-18",
            timeline_sort_time=now,
            location_text="会议室A",
            confidence_score=0.9,
        )
        event_b = Event(
            user_id=user.id,
            title=f"项目启动会候选 {suffix}",
            summary="候选事件：同一场启动会的重复记录。",
            description="候选事件完整描述，比源事件更长，用于测试 richer text 选择。",
            event_type="meeting",
            status="active",
            source_note_id=note_b.id,
            start_time=now,
            time_precision="day",
            time_text="2026-04-18",
            timeline_sort_time=now,
            location_text="会议室A",
            confidence_score=0.93,
        )
        reject_event_a = Event(
            user_id=user.id,
            title=f"预算会议 {suffix}",
            summary="一条不应合并的预算会议。",
            description="预算会议",
            event_type="meeting",
            status="active",
            source_note_id=note_a.id,
            start_time=now,
            time_precision="day",
            time_text="2026-04-18",
            timeline_sort_time=now,
            location_text="会议室B",
            confidence_score=0.71,
        )
        reject_event_b = Event(
            user_id=user.id,
            title=f"技术复盘 {suffix}",
            summary="另一条不应合并的技术复盘。",
            description="技术复盘",
            event_type="meeting",
            status="active",
            source_note_id=note_b.id,
            start_time=now,
            time_precision="day",
            time_text="2026-04-18",
            timeline_sort_time=now,
            location_text="会议室C",
            confidence_score=0.69,
        )
        db.add_all([event_a, event_b, reject_event_a, reject_event_b])
        db.flush()

        db.add_all(
            [
                NoteEntity(
                    note_id=note_a.id,
                    entity_id=entity_a.id,
                    mention_text=entity_a.display_name,
                    confidence_score=0.9,
                ),
                NoteEntity(
                    note_id=note_b.id,
                    entity_id=entity_b.id,
                    mention_text=entity_b.display_name,
                    confidence_score=0.88,
                ),
                NoteEvent(note_id=note_a.id, event_id=event_a.id, mention_text=event_a.title, confidence_score=0.9),
                NoteEvent(note_id=note_b.id, event_id=event_b.id, mention_text=event_b.title, confidence_score=0.9),
                EventEntity(
                    event_id=event_a.id,
                    entity_id=entity_a.id,
                    role="参与者",
                    relation_type="participates_in",
                    display_order=1,
                    confidence_score=0.9,
                ),
                EventEntity(
                    event_id=event_b.id,
                    entity_id=entity_b.id,
                    role="参与者",
                    relation_type="participates_in",
                    display_order=1,
                    confidence_score=0.88,
                ),
                TimelineItem(
                    user_id=user.id,
                    event_id=event_a.id,
                    note_id=note_a.id,
                    title=event_a.title,
                    summary=event_a.summary,
                    display_time="2026-04-18",
                    sort_time=now,
                    time_precision="day",
                    importance_score=0.8,
                ),
                TimelineItem(
                    user_id=user.id,
                    event_id=event_b.id,
                    note_id=note_b.id,
                    title=event_b.title,
                    summary=event_b.summary,
                    display_time="2026-04-18",
                    sort_time=now,
                    time_precision="day",
                    importance_score=0.8,
                ),
                Relation(
                    user_id=user.id,
                    source_type="entity",
                    source_id=entity_a.id,
                    relation_type="participates_in",
                    target_type="event",
                    target_id=event_a.id,
                    evidence_count=1,
                    confidence_score=0.9,
                ),
                Relation(
                    user_id=user.id,
                    source_type="entity",
                    source_id=entity_b.id,
                    relation_type="participates_in",
                    target_type="event",
                    target_id=event_b.id,
                    evidence_count=1,
                    confidence_score=0.88,
                ),
            ]
        )

        entity_candidate = MergeCandidate(
            user_id=user.id,
            object_type="entity",
            source_id=entity_a.id,
            candidate_id=entity_b.id,
            score=0.94,
            reason_json={"signals": ["normalized_name", "shared_context"], "shared_fields": ["person"]},
            status="pending",
        )
        event_candidate = MergeCandidate(
            user_id=user.id,
            object_type="event",
            source_id=event_a.id,
            candidate_id=event_b.id,
            score=0.91,
            reason_json={"signals": ["same_day", "same_location"], "shared_participants": [entity_a.display_name]},
            status="pending",
        )
        reject_candidate = MergeCandidate(
            user_id=user.id,
            object_type="event",
            source_id=reject_event_a.id,
            candidate_id=reject_event_b.id,
            score=0.52,
            reason_json={"signals": ["same_day"], "location": "不同会议室"},
            status="pending",
        )
        db.add_all([entity_candidate, event_candidate, reject_candidate])
        db.commit()

        return {
            "user_id": user.id,
            "entity_a_id": entity_a.id,
            "entity_b_id": entity_b.id,
            "event_a_id": event_a.id,
            "event_b_id": event_b.id,
            "entity_candidate_id": entity_candidate.id,
            "event_candidate_id": event_candidate.id,
            "reject_candidate_id": reject_candidate.id,
            "manual_alias": f"三哥-{suffix}",
        }


def verify_database_state(ids: dict[str, str]) -> None:
    with SessionLocal() as db:
        survivor = db.get(Entity, ids["entity_a_id"])
        merged_entity = db.get(Entity, ids["entity_b_id"])
        survivor_event = db.get(Event, ids["event_a_id"])
        merged_event = db.get(Event, ids["event_b_id"])
        entity_candidate = db.get(MergeCandidate, ids["entity_candidate_id"])
        event_candidate = db.get(MergeCandidate, ids["event_candidate_id"])
        reject_candidate = db.get(MergeCandidate, ids["reject_candidate_id"])

        assert survivor is not None
        assert merged_entity is None
        assert survivor_event is not None
        assert merged_event is None
        assert entity_candidate is not None and entity_candidate.status == "accepted"
        assert event_candidate is not None and event_candidate.status == "accepted"
        assert reject_candidate is not None and reject_candidate.status == "rejected"

        rewritten_note_refs = db.scalar(select(func.count()).select_from(NoteEntity).where(NoteEntity.entity_id == ids["entity_b_id"]))
        rewritten_event_refs = db.scalar(select(func.count()).select_from(EventEntity).where(EventEntity.entity_id == ids["entity_b_id"]))
        event_b_refs = db.scalar(select(func.count()).select_from(NoteEvent).where(NoteEvent.event_id == ids["event_b_id"]))
        alias = db.scalar(
            select(EntityAlias).where(
                EntityAlias.entity_id == ids["entity_a_id"],
                EntityAlias.normalized_alias == normalize_name(ids["manual_alias"]),
            )
        )
        action_count = db.scalar(
            select(func.count()).select_from(ReviewAction).where(ReviewAction.user_id == ids["user_id"])
        )

        assert rewritten_note_refs == 0
        assert rewritten_event_refs == 0
        assert event_b_refs == 0
        assert alias is not None
        assert action_count is not None and action_count >= 5


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

    ids = seed_review_fixture(args.username)

    entity_queue_ids = collect_merge_candidate_ids(
        client,
        base_url=args.base_url,
        headers=headers,
        object_type="entity",
        status="pending",
    )
    event_queue_ids = collect_merge_candidate_ids(
        client,
        base_url=args.base_url,
        headers=headers,
        object_type="event",
        status="pending",
    )
    assert ids["entity_candidate_id"] in entity_queue_ids
    assert ids["event_candidate_id"] in event_queue_ids
    assert ids["reject_candidate_id"] in event_queue_ids

    detail = assert_ok(client.get(f"{args.base_url}/review/merge-candidates/{ids['entity_candidate_id']}", headers=headers))
    assert detail["can_accept"] is True
    assert detail["source"]["id"] == ids["entity_a_id"]

    entity_context = assert_ok(client.get(f"{args.base_url}/review/entities/{ids['entity_a_id']}/context", headers=headers))
    assert any(item["id"] == ids["entity_candidate_id"] for item in entity_context["candidates"])

    alias_result = assert_ok(
        client.post(
            f"{args.base_url}/review/entities/{ids['entity_a_id']}/aliases",
            headers=headers,
            json={"alias": ids["manual_alias"], "note": "e2e alias confirmation"},
        )
    )
    assert alias_result["entity_id"] == ids["entity_a_id"]

    entity_accept = assert_ok(
        client.post(
            f"{args.base_url}/review/merge-candidates/{ids['entity_candidate_id']}/accept",
            headers=headers,
            json={"resolution": "merge", "survivor_id": ids["entity_a_id"], "note": "e2e entity merge"},
        )
    )
    assert entity_accept["status"] == "accepted"
    assert entity_accept["survivor_id"] == ids["entity_a_id"]

    event_accept = assert_ok(
        client.post(
            f"{args.base_url}/review/merge-candidates/{ids['event_candidate_id']}/accept",
            headers=headers,
            json={"resolution": "merge", "survivor_id": ids["event_a_id"], "note": "e2e event merge"},
        )
    )
    assert event_accept["status"] == "accepted"
    assert event_accept["survivor_id"] == ids["event_a_id"]

    reject = assert_ok(
        client.post(
            f"{args.base_url}/review/merge-candidates/{ids['reject_candidate_id']}/reject",
            headers=headers,
            json={"reason": "not_the_same_event", "note": "e2e rejection"},
        )
    )
    assert reject["status"] == "rejected"

    event_context = assert_ok(client.get(f"{args.base_url}/review/events/{ids['event_a_id']}/context", headers=headers))
    assert event_context["event"]["id"] == ids["event_a_id"]
    assert event_context["stats"]["participant_count"] >= 1

    verify_database_state(ids)
    print("Review flow e2e passed")


if __name__ == "__main__":
    main()

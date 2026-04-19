import argparse
from datetime import UTC, datetime
from uuid import uuid4

import httpx
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.entity import Entity, EntityAlias, EventEntity, Relation
from app.models.event import Event
from app.models.note import Note
from app.models.user import User
from app.utils.text import normalize_name


def assert_ok(response: httpx.Response) -> dict:
    response.raise_for_status()
    payload = response.json()
    assert payload["code"] == 0, payload
    return payload["data"]


def seed_entity_curation_fixture(username: str) -> dict[str, str]:
    suffix = uuid4().hex[:8]
    original_time = datetime(2026, 4, 18, 9, 30, tzinfo=UTC)

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username))
        assert user is not None, f"User {username} not found"

        note = Note(
            user_id=user.id,
            title=f"Entity Curation Seed Note {suffix}",
            summary="实体校对 e2e 种子卷宗。",
            canonical_text="2026-04-18 张三参与项目启动会议。",
            category="knowledge",
            status="ready",
            primary_time=original_time,
            processed_at=original_time,
        )
        db.add(note)
        db.flush()

        entity = Entity(
            user_id=user.id,
            entity_type="person",
            canonical_name=f"原始张三-{suffix}",
            display_name=f"原始张三-{suffix}",
            description="待人工校对的人物节点。",
            alias_json=[],
            normalized_name=normalize_name(f"原始张三-{suffix}"),
            status="active",
            confidence_score=0.82,
            first_seen_at=original_time,
            last_seen_at=original_time,
        )
        peer_entity = Entity(
            user_id=user.id,
            entity_type="person",
            canonical_name=f"同伴李四-{suffix}",
            display_name=f"同伴李四-{suffix}",
            description="用于人物关系治理验证的关联实体。",
            alias_json=[],
            normalized_name=normalize_name(f"同伴李四-{suffix}"),
            status="active",
            confidence_score=0.76,
            first_seen_at=original_time,
            last_seen_at=original_time,
        )
        db.add_all([entity, peer_entity])
        db.flush()

        event = Event(
            user_id=user.id,
            title=f"实体校对关联事件 {suffix}",
            summary="用于检查时间线和关联事件上下文。",
            description="人物已经挂接到一个事件，方便在校对页里查看上下文。",
            event_type="meeting",
            status="active",
            source_note_id=note.id,
            start_time=original_time,
            time_precision="day",
            time_text="2026-04-18",
            timeline_sort_time=original_time,
            location_text="会议室 A",
            confidence_score=0.8,
        )
        db.add(event)
        db.flush()

        db.add(
            EventEntity(
                event_id=event.id,
                entity_id=entity.id,
                role="参与者",
                relation_type="participates_in",
                display_order=0,
                confidence_score=0.87,
            )
        )
        db.commit()

        return {
            "user_id": user.id,
            "note_id": note.id,
            "entity_id": entity.id,
            "peer_entity_id": peer_entity.id,
            "event_id": event.id,
            "updated_display_name": f"校对张三-{suffix}",
            "updated_canonical_name": f"张三-{suffix}",
            "manual_alias": f"阿三-{suffix}",
        }


def verify_database_state(ids: dict[str, str], alias_id: str, relation_id: str) -> None:
    with SessionLocal() as db:
        entity = db.get(Entity, ids["entity_id"])
        assert entity is not None
        assert entity.display_name == ids["updated_display_name"]
        assert entity.canonical_name == ids["updated_canonical_name"]
        assert entity.normalized_name == normalize_name(ids["updated_canonical_name"])
        assert entity.status == "verified"
        assert entity.description == "人工修正后的人物说明。"
        assert entity.last_seen_at is not None
        assert entity.last_seen_at.date().isoformat() == "2026-04-21"
        assert ids["manual_alias"] not in (entity.alias_json or [])

        alias = db.get(EntityAlias, alias_id)
        assert alias is None

        relation = db.get(Relation, relation_id)
        assert relation is None


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

    ids = seed_entity_curation_fixture(args.username)

    context = assert_ok(client.get(f"{args.base_url}/curation/entities/{ids['entity_id']}", headers=headers))
    assert context["entity"]["id"] == ids["entity_id"]
    assert context["stats"]["related_event_count"] == 1
    assert len(context["timeline_fragments"]) == 1
    assert context["stats"]["relation_count"] == 0

    updated = assert_ok(
        client.patch(
            f"{args.base_url}/curation/entities/{ids['entity_id']}",
            headers=headers,
            json={
                "entity_type": "person",
                "canonical_name": ids["updated_canonical_name"],
                "display_name": ids["updated_display_name"],
                "description": "人工修正后的人物说明。",
                "status": "verified",
                "first_seen_at": "2026-04-18T09:30:00+00:00",
                "last_seen_at": "2026-04-21T13:20:00+00:00",
            },
        )
    )
    assert updated["display_name"] == ids["updated_display_name"]
    assert updated["canonical_name"] == ids["updated_canonical_name"]
    assert updated["status"] == "verified"

    alias = assert_ok(
        client.post(
            f"{args.base_url}/curation/entities/{ids['entity_id']}/aliases",
            headers=headers,
            json={"alias": ids["manual_alias"], "alias_type": "manual"},
        )
    )
    assert alias["alias"] == ids["manual_alias"]
    assert alias["alias_type"] == "manual"

    refreshed = assert_ok(client.get(f"{args.base_url}/curation/entities/{ids['entity_id']}", headers=headers))
    assert any(item["id"] == alias["id"] for item in refreshed["aliases"])
    assert refreshed["entity"]["display_name"] == ids["updated_display_name"]

    relation = assert_ok(
        client.post(
            f"{args.base_url}/curation/entities/{ids['entity_id']}/relations",
            headers=headers,
            json={
                "direction": "outgoing",
                "related_type": "entity",
                "related_id": ids["peer_entity_id"],
                "relation_type": "supports",
            },
        )
    )
    assert relation["relation_type"] == "supports"
    assert relation["peer"]["id"] == ids["peer_entity_id"]

    updated_relation = assert_ok(
        client.patch(
            f"{args.base_url}/curation/entities/{ids['entity_id']}/relations/{relation['id']}",
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

    relation_context = assert_ok(client.get(f"{args.base_url}/curation/entities/{ids['entity_id']}", headers=headers))
    assert relation_context["stats"]["relation_count"] == 1
    assert any(item["id"] == relation["id"] and item["relation_type"] == "documents" for item in relation_context["relations"])

    removed = assert_ok(
        client.delete(
            f"{args.base_url}/curation/entities/{ids['entity_id']}/aliases/{alias['id']}",
            headers=headers,
        )
    )
    assert removed["status"] == "removed"

    final_context = assert_ok(client.get(f"{args.base_url}/curation/entities/{ids['entity_id']}", headers=headers))
    assert not any(item["id"] == alias["id"] for item in final_context["aliases"])
    assert final_context["stats"]["related_event_count"] == 1
    assert final_context["stats"]["relation_count"] == 1

    removed_relation = assert_ok(
        client.delete(
            f"{args.base_url}/curation/entities/{ids['entity_id']}/relations/{relation['id']}",
            headers=headers,
        )
    )
    assert removed_relation["status"] == "removed"

    final_graph = assert_ok(client.get(f"{args.base_url}/curation/entities/{ids['entity_id']}", headers=headers))
    assert final_graph["stats"]["relation_count"] == 0

    verify_database_state(ids, alias["id"], relation["id"])
    print("Entity curation flow e2e passed")


if __name__ == "__main__":
    main()

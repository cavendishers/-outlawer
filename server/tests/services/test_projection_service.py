from datetime import UTC, datetime

from app.domains.projection.service import apply_entity_seen_time_from_event, build_story_body, resolve_relation_object_id
from app.models.entity import Entity
from app.models.event import Event


def test_resolve_relation_object_id_prefers_note_id_and_temp_map() -> None:
    object_id_map = {
        "event": {"evt_1": "event-db-1"},
        "entity": {"ent_1": "entity-db-1"},
    }

    assert resolve_relation_object_id({"type": "note"}, object_id_map, "note-db-1") == "note-db-1"
    assert (
        resolve_relation_object_id({"type": "event", "temp_id": "evt_1"}, object_id_map, "note-db-1")
        == "event-db-1"
    )
    assert (
        resolve_relation_object_id({"type": "entity", "temp_id": "ent_1"}, object_id_map, "note-db-1")
        == "entity-db-1"
    )
    assert resolve_relation_object_id({"type": "entity", "temp_id": "missing"}, object_id_map, "note-db-1") is None


def test_build_story_body_joins_only_non_empty_event_narrative_sections() -> None:
    body = build_story_body(
        {
            "event_narrative": [
                {"body": "第一幕"},
                {"headline": "忽略这个，没有正文"},
                {"body": "第二幕"},
            ]
        }
    )

    assert body == "第一幕\n第二幕"


def test_apply_entity_seen_time_from_event_uses_event_time_bounds() -> None:
    entity = Entity(
        id="entity-1",
        user_id="user-1",
        entity_type="person",
        canonical_name="李晓",
        display_name="李晓",
        description=None,
        alias_json=[],
        normalized_name="李晓",
        status="active",
        first_seen_at=datetime(2026, 5, 17, tzinfo=UTC),
        last_seen_at=datetime(2026, 5, 17, tzinfo=UTC),
    )
    event = Event(
        id="event-1",
        user_id="user-1",
        title="雀神角逐",
        status="active",
        time_precision="day",
        timeline_sort_time=datetime(2026, 5, 16, 18, tzinfo=UTC),
    )

    apply_entity_seen_time_from_event(entity, event)

    assert entity.first_seen_at == datetime(2026, 5, 16, 18, tzinfo=UTC)
    assert entity.last_seen_at == datetime(2026, 5, 17, tzinfo=UTC)

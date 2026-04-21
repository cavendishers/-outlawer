from app.domains.projection.service import build_story_body, resolve_relation_object_id


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

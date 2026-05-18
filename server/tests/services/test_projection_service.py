from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.domains.projection.service import (
    apply_entity_seen_time_from_event,
    build_story_body,
    regenerate_note_style_view_from_payload,
    resolve_relation_object_id,
)
from app.models.entity import Entity
from app.models.event import Event
from app.models.style_view import StyleView
from app.models.user import User


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


def test_regenerate_note_style_view_upserts_existing_story() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[User.__table__, StyleView.__table__])
    Session = sessionmaker(bind=engine)

    with Session() as db:
        db.add(User(id="user-1", username="admin", password_hash="hash", display_name="Admin"))
        existing = StyleView(
            id="story-1",
            user_id="user-1",
            target_type="note",
            target_id="note-1",
            style_type="chunibyo",
            title="旧标题",
            content="旧正文",
        )
        db.add(existing)
        db.commit()

        story = regenerate_note_style_view_from_payload(
            db,
            user_id="user-1",
            note_id="note-1",
            style_payload={
                "title": "命运卷宗：启动会",
                "event_narrative": [{"body": "第一幕"}, {"body": "第二幕"}],
            },
        )
        db.commit()

        rows = db.query(StyleView).all()

    assert story.id == "story-1"
    assert len(rows) == 1
    assert rows[0].title == "命运卷宗：启动会"
    assert rows[0].content == "第一幕\n第二幕"


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


def test_apply_entity_seen_time_from_event_handles_naive_database_values() -> None:
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
        first_seen_at=datetime(2026, 5, 17),
        last_seen_at=datetime(2026, 5, 17),
    )
    event = Event(
        id="event-1",
        user_id="user-1",
        title="雀神角逐",
        status="active",
        time_precision="day",
        timeline_sort_time=datetime(2026, 5, 18, tzinfo=UTC),
    )

    apply_entity_seen_time_from_event(entity, event)

    assert entity.first_seen_at == datetime(2026, 5, 17)
    assert entity.last_seen_at == datetime(2026, 5, 18, tzinfo=UTC)

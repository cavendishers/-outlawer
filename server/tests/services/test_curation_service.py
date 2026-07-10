from datetime import UTC, datetime

from sqlalchemy import select, create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.database import Base
from app.domains.governance.curation import (
    remove_event_relation,
    update_event_relation,
    upsert_event_participant,
    upsert_event_relation,
)
from app.models.entity import Entity, EntityAlias, EventEntity, NoteEntity, Relation
from app.models.event import Event
from app.models.review import ReviewAction
from app.models.style_view import StyleView
from app.models.user import User


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            Entity.__table__,
            EntityAlias.__table__,
            Event.__table__,
            EventEntity.__table__,
            NoteEntity.__table__,
            Relation.__table__,
            StyleView.__table__,
            ReviewAction.__table__,
        ],
    )
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()


def seed_event(db):
    user = User(id="user-1", username="admin", password_hash="hash", display_name="Admin", status="active")
    event = Event(
        id="event-1",
        user_id=user.id,
        title="良渚咖啡聚会",
        summary="补录参与人物。",
        description="围绕知识库导入和图谱校对展开讨论。",
        event_type="meeting",
        status="active",
        start_time=datetime(2026, 5, 16, tzinfo=UTC),
        time_precision="day",
        time_text="2026-05-16",
        timeline_sort_time=datetime(2026, 5, 16, tzinfo=UTC),
        location_text="良渚",
    )
    db.add_all([user, event])
    db.commit()
    return user, event


def test_upsert_event_participant_creates_profile_defaults_and_story_view() -> None:
    db = make_db()
    user, event = seed_event(db)

    result = upsert_event_participant(
        db,
        user_id=user.id,
        event_id=event.id,
        entity_id=None,
        entity_name="法老林",
        entity_type="person",
        role="同行者",
        relation_type="participates_in",
    )

    entity = db.get(Entity, result["entity_id"])
    assert entity is not None
    assert entity.display_name == "法老林"
    assert entity.description == "手动加入《良渚咖啡聚会》的同行者。"
    assert entity.first_seen_at is not None
    assert entity.last_seen_at is not None
    assert entity.first_seen_at.date() == event.timeline_sort_time.date()
    assert entity.last_seen_at.date() == event.timeline_sort_time.date()

    link = db.scalar(select(EventEntity).where(EventEntity.event_id == event.id, EventEntity.entity_id == entity.id))
    assert link is not None
    assert link.role == "同行者"

    story = db.scalar(
        select(StyleView).where(
            StyleView.target_type == "entity",
            StyleView.target_id == entity.id,
            StyleView.style_type == "chunibyo",
        )
    )
    assert story is not None
    assert story.title == "法老林 / 同行者"
    assert "手动纳入《良渚咖啡聚会》" in story.content


def test_upsert_event_participant_preserves_existing_profile_text() -> None:
    db = make_db()
    user, event = seed_event(db)
    entity = Entity(
        id="entity-1",
        user_id=user.id,
        entity_type="person",
        canonical_name="李晓",
        display_name="李晓",
        description="已有的人物档案。",
        alias_json=[],
        normalized_name="李晓",
        status="active",
        confidence_score=0.9,
    )
    db.add(entity)
    db.commit()

    result = upsert_event_participant(
        db,
        user_id=user.id,
        event_id=event.id,
        entity_id=entity.id,
        role="发起者",
        relation_type="participates_in",
    )

    updated = db.get(Entity, result["entity_id"])
    assert updated is not None
    assert updated.description == "已有的人物档案。"
    assert updated.first_seen_at is not None
    assert updated.first_seen_at.date() == event.timeline_sort_time.date()

    story = db.scalar(select(StyleView).where(StyleView.target_type == "entity", StyleView.target_id == entity.id))
    assert story is not None
    assert story.title == "李晓 / 发起者"


def test_upsert_event_participant_backfills_empty_existing_profile() -> None:
    db = make_db()
    user, event = seed_event(db)
    entity = Entity(
        id="entity-empty-profile",
        user_id=user.id,
        entity_type="person",
        canonical_name="赵六",
        display_name="赵六",
        description=None,
        alias_json=[],
        normalized_name="赵六",
        status="active",
        confidence_score=0.9,
    )
    db.add(entity)
    db.commit()

    result = upsert_event_participant(
        db,
        user_id=user.id,
        event_id=event.id,
        entity_id=entity.id,
        role="记录者",
        relation_type="participates_in",
    )

    updated = db.get(Entity, result["entity_id"])
    assert updated is not None
    assert updated.description == "手动加入《良渚咖啡聚会》的记录者。"


def test_upsert_event_participant_uses_human_default_role_text() -> None:
    db = make_db()
    user, event = seed_event(db)

    result = upsert_event_participant(
        db,
        user_id=user.id,
        event_id=event.id,
        entity_id=None,
        entity_name="红烧鱼",
        entity_type="person",
        role=None,
        relation_type=None,
    )

    entity = db.get(Entity, result["entity_id"])
    assert entity is not None
    assert entity.description == "手动加入《良渚咖啡聚会》的参与者。"

    story = db.scalar(select(StyleView).where(StyleView.target_type == "entity", StyleView.target_id == entity.id))
    assert story is not None
    assert story.title == "红烧鱼 / 参与者"


def test_relation_curation_audit_keeps_before_and_after_snapshots() -> None:
    db = make_db()
    user, event = seed_event(db)
    entity = Entity(
        id="entity-relation-peer",
        user_id=user.id,
        entity_type="person",
        canonical_name="关系对象",
        display_name="关系对象",
        alias_json=[],
        normalized_name="关系对象",
        status="active",
    )
    db.add(entity)
    db.commit()

    created = upsert_event_relation(
        db,
        user_id=user.id,
        event_id=event.id,
        direction="outgoing",
        related_type="entity",
        related_id=entity.id,
        relation_type="supports",
    )
    relation_id = created["id"]
    updated = update_event_relation(
        db,
        user_id=user.id,
        event_id=event.id,
        relation_id=relation_id,
        payload={"relation_type": "blocks"},
    )
    assert updated["relation_type"] == "blocks"
    remove_event_relation(db, user_id=user.id, event_id=event.id, relation_id=relation_id)

    actions = db.scalars(
        select(ReviewAction)
        .where(ReviewAction.target_type == "relation", ReviewAction.target_id == relation_id)
        .order_by(ReviewAction.created_at.asc())
    ).all()

    assert [action.action_type for action in actions] == ["add_relation", "update_relation", "remove_relation"]
    assert actions[0].payload_json["before"] is None
    assert actions[0].payload_json["after"]["relation_type"] == "supports"
    assert actions[1].payload_json["before"]["relation_type"] == "supports"
    assert actions[1].payload_json["after"]["relation_type"] == "blocks"
    assert actions[2].payload_json["before"]["relation_type"] == "blocks"
    assert actions[2].payload_json["after"] is None

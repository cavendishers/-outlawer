from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.database import Base
from app.domains.character_cards.service import (
    build_avatar_prompt,
    build_role_image_prompt,
    build_sillytavern_spec,
    create_card_from_entity,
    normalize_export_spec,
)
from app.models.character_card import CharacterCard
from app.models.entity import Entity, EntityAlias, EventEntity
from app.models.event import Event
from app.models.note import Note
from app.models.raw_asset import RawAsset
from app.models.style_view import StyleView
from app.models.user import User


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            RawAsset.__table__,
            Note.__table__,
            Entity.__table__,
            EntityAlias.__table__,
            Event.__table__,
            EventEntity.__table__,
            StyleView.__table__,
            CharacterCard.__table__,
        ],
    )
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()


def seed_entity_graph(db):
    user = User(id="user-1", username="admin", password_hash="hash", display_name="Admin", status="active")
    asset = RawAsset(
        id="asset-1",
        user_id=user.id,
        asset_type="text",
        source_type="manual",
        title="卷宗",
        status="uploaded",
        original_text="张三参加项目启动会。",
    )
    note = Note(id="note-1", user_id=user.id, asset_id=asset.id, title="项目卷宗", status="ready")
    entity = Entity(
        id="entity-1",
        user_id=user.id,
        entity_type="person",
        canonical_name="张三",
        display_name="张三",
        description="项目发起人，负责推动知识库建设。",
        alias_json=[],
        normalized_name="张三",
        status="active",
    )
    event = Event(
        id="event-1",
        user_id=user.id,
        source_note_id=note.id,
        title="项目启动会",
        summary="张三确认知识库建设方向。",
        description="围绕图谱、导入和时间线展开讨论。",
        event_type="meeting",
        status="active",
        start_time=datetime(2026, 5, 1, tzinfo=UTC),
        time_precision="day",
        time_text="2026-05-01",
        timeline_sort_time=datetime(2026, 5, 1, tzinfo=UTC),
        location_text="会议室A",
    )
    link = EventEntity(event_id=event.id, entity_id=entity.id, role="发起人", relation_type="participates_in")
    story = StyleView(
        id="story-1",
        user_id=user.id,
        target_type="entity",
        target_id=entity.id,
        style_type="chunibyo",
        title="命运卷宗：张三",
        content="张三在静默会议室中推开知识之门。",
        version="v1",
    )
    db.add_all([user, asset, note, entity, event, link, story])
    db.commit()
    return user, entity


def test_create_card_from_entity_builds_sillytavern_v2_spec() -> None:
    db = make_db()
    user, entity = seed_entity_graph(db)

    card = create_card_from_entity(
        db,
        user_id=user.id,
        entity_id=entity.id,
        mode="faithful",
        include_story_view=True,
        include_character_book=True,
        language="zh-CN",
    )

    assert card.title == "张三 人物卡"
    assert card.card_version == "chara_card_v2"
    assert card.spec_json["spec"] == "chara_card_v2"
    assert card.spec_json["data"]["name"] == "张三"
    assert "项目启动会" in card.spec_json["data"]["description"]
    assert card.spec_json["data"]["character_book"]["entries"]
    assert card.spec_json["data"]["extensions"]["outlawer"]["source_entity_id"] == entity.id
    assert card.source_snapshot_json["story_view"]["title"] == "命运卷宗：张三"


def test_build_sillytavern_spec_can_omit_character_book() -> None:
    snapshot = {
        "identity": {
            "id": "entity-2",
            "entity_type": "person",
            "canonical_name": "李四",
            "display_name": "李四",
            "description": None,
            "aliases": [],
        },
        "related_events": [],
        "timeline_fragments": [],
        "story_view": None,
        "source_event_ids": [],
        "source_note_titles": [],
    }

    spec = build_sillytavern_spec(snapshot, mode="creative", include_character_book=False, language="zh-CN")

    assert spec["data"]["name"] == "李四"
    assert spec["data"]["character_book"]["entries"] == []
    assert "创作" in spec["data"]["description"]


def test_normalize_export_spec_wraps_plain_data() -> None:
    spec = normalize_export_spec({"name": "王五", "description": "测试"})

    assert spec["spec"] == "chara_card_v2"
    assert spec["spec_version"] == "2.0"
    assert spec["data"]["name"] == "王五"


def test_build_avatar_prompt_uses_card_fields() -> None:
    card = CharacterCard(
        id="card-1",
        user_id="user-1",
        source_entity_id="entity-1",
        status="draft",
        title="张三 人物卡",
        card_format="sillytavern",
        card_version="chara_card_v2",
        mode="faithful",
        spec_json={
            "spec": "chara_card_v2",
            "spec_version": "2.0",
            "data": {
                "name": "张三",
                "description": "项目发起人，负责推动知识库建设。",
                "personality": "重视时间线和证据。",
                "scenario": "用户正在询问项目启动会。",
            },
        },
        source_snapshot_json={},
    )

    prompt = build_avatar_prompt(card)

    assert "张三" in prompt
    assert "项目发起人" in prompt
    assert "no text" in prompt


def test_build_role_image_prompt_requests_complete_tavern_card() -> None:
    card = CharacterCard(
        id="card-1",
        user_id="user-1",
        source_entity_id="entity-1",
        status="draft",
        title="艾琳 人物卡",
        card_format="sillytavern",
        card_version="chara_card_v2",
        mode="creative",
        spec_json={
            "spec": "chara_card_v2",
            "spec_version": "2.0",
            "data": {
                "name": "艾琳",
                "description": "图书馆管理员，冷静、理性，守着旧城图书馆的秘密。",
                "personality": "克制、观察力强、偶尔毒舌。",
                "scenario": "你第一次来到一座深夜仍亮着灯的旧图书馆。",
                "first_mes": "这么晚还来找书？",
                "tags": ["图书馆", "女性", "原创角色"],
            },
        },
        source_snapshot_json={},
    )

    prompt = build_role_image_prompt(card)

    assert "艾琳" in prompt
    assert "SillyTavern" in prompt
    assert "card face only" in prompt
    assert "no editor UI" in prompt
    assert "角色简介" in prompt

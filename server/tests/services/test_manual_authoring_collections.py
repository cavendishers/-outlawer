from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.domains.collections.service import (
    add_collection_item,
    build_collection_timeline,
    bulk_remove_collection_items,
    compile_collection_story,
    create_collection,
    export_collection,
    get_collection_detail,
    list_collection_candidates,
    reorder_collection_items,
)
from app.domains.knowledge.manual_authoring import create_graph_manual_node, create_manual_entity, list_manual_evidence
from app.domains.retrieval.graph_workspace import get_graph_workspace
from app.core.pagination import PageParams
from app.models.collection import KnowledgeCollection, KnowledgeCollectionItem
from app.models.entity import Entity, EntityAlias, EventEntity, Relation
from app.models.event import Event, TimelineItem
from app.models.graph_viewpoint import GraphViewpoint
from app.models.manual_knowledge import ManualKnowledgeEvidence
from app.models.note import Note
from app.models.raw_asset import RawAsset
from app.models.review import ReviewAction
from app.models.user import User


TABLES = [
    User.__table__,
    RawAsset.__table__,
    Note.__table__,
    Entity.__table__,
    EntityAlias.__table__,
    Event.__table__,
    TimelineItem.__table__,
    EventEntity.__table__,
    Relation.__table__,
    GraphViewpoint.__table__,
    ManualKnowledgeEvidence.__table__,
    KnowledgeCollection.__table__,
    KnowledgeCollectionItem.__table__,
    ReviewAction.__table__,
]


def make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=TABLES)
    return sessionmaker(bind=engine)()


def seed_user_and_note(db) -> None:
    db.add(User(id="user-manual", username="manual", password_hash="hash", display_name="Manual"))
    db.add(RawAsset(id="asset-source", user_id="user-manual", asset_type="text", title="原始访谈", status="uploaded"))
    db.add(Note(id="note-source", user_id="user-manual", asset_id="asset-source", title="访谈笔记", status="active"))
    db.commit()


def test_manual_entity_creation_preserves_source_and_writes_evidence_audit() -> None:
    with make_session() as db:
        seed_user_and_note(db)
        result = create_manual_entity(
            db,
            user_id="user-manual",
            payload={
                "canonical_name": "张三",
                "display_name": "张三",
                "entity_type": "person",
                "aliases": ["老张"],
                "evidence": {"note_id": "note-source", "excerpt": "张三主持了会议"},
            },
        )

        evidence = db.scalar(select(ManualKnowledgeEvidence))
        actions = list(db.scalars(select(ReviewAction).order_by(ReviewAction.created_at)).all())
        source = db.get(Note, "note-source")

    assert result["entity"]["display_name"] == "张三"
    assert result["entity"]["aliases"] == ["老张"]
    assert evidence is not None and evidence.note_id == "note-source"
    assert source is not None and source.title == "访谈笔记"
    assert {action.action_type for action in actions} == {"attach_manual_evidence", "create_entity"}


def test_graph_create_and_connect_adds_event_timeline_and_participant_in_one_flow() -> None:
    with make_session() as db:
        seed_user_and_note(db)
        entity = Entity(
            id="entity-anchor",
            user_id="user-manual",
            entity_type="person",
            canonical_name="李四",
            display_name="李四",
            alias_json=[],
            normalized_name="李四",
            status="active",
        )
        db.add(entity)
        db.commit()

        result = create_graph_manual_node(
            db,
            user_id="user-manual",
            payload={
                "node_type": "event",
                "name": "专题讨论会",
                "subtype": "meeting",
                "anchor_type": "entity",
                "anchor_id": entity.id,
                "relation_type": "hosts",
                "role": "主持人",
                "event_time": datetime(2026, 7, 11, 10, tzinfo=UTC),
            },
        )
        participant = db.scalar(select(EventEntity).where(EventEntity.event_id == result["node_id"]))
        timeline = db.scalar(select(TimelineItem).where(TimelineItem.event_id == result["node_id"]))

    assert result["connection_type"] == "participant"
    assert participant is not None and participant.entity_id == "entity-anchor"
    assert participant.relation_type == "hosts"
    assert timeline is not None and timeline.title == "专题讨论会"


def test_collection_compiles_timeline_story_and_exports_markdown_and_json() -> None:
    with make_session() as db:
        seed_user_and_note(db)
        event = Event(
            id="event-topic",
            user_id="user-manual",
            title="关键会议",
            summary="确认了下一步安排",
            status="active",
            time_precision="day",
            time_text="2026-07-11",
            timeline_sort_time=datetime(2026, 7, 11, tzinfo=UTC),
        )
        db.add(event)
        db.commit()
        collection = create_collection(
            db,
            user_id="user-manual",
            payload={"title": "项目案件", "description": "追踪项目事实", "collection_type": "case"},
        )
        add_collection_item(
            db,
            user_id="user-manual",
            collection_id=collection["id"],
            payload={"item_type": "note", "item_id": "note-source", "curator_note": "背景材料"},
        )
        add_collection_item(
            db,
            user_id="user-manual",
            collection_id=collection["id"],
            payload={"item_type": "event", "item_id": event.id, "curator_note": "关键节点"},
        )
        story = compile_collection_story(db, user_id="user-manual", collection_id=collection["id"])
        timeline = build_collection_timeline(db, user_id="user-manual", collection_id=collection["id"])
        detail = get_collection_detail(db, user_id="user-manual", collection_id=collection["id"])
        markdown = export_collection(db, user_id="user-manual", collection_id=collection["id"], export_format="markdown")
        json_export = export_collection(db, user_id="user-manual", collection_id=collection["id"], export_format="json")

    assert detail["item_count"] == 2
    assert timeline["items"][0]["title"] == "关键会议"
    assert "## 时间线" in (story["body"] or "")
    assert "# 项目案件" in markdown["content"]
    assert '"collection"' in json_export["content"]


def test_collection_candidates_stats_order_bulk_remove_and_evidence_readback() -> None:
    with make_session() as db:
        seed_user_and_note(db)
        created = create_manual_entity(
            db,
            user_id="user-manual",
            payload={
                "canonical_name": "候选人物",
                "entity_type": "person",
                "evidence": {"note_id": "note-source", "excerpt": "候选人物出现在访谈中"},
            },
        )
        entity_id = created["entity"]["id"]
        collection = create_collection(db, user_id="user-manual", payload={"title": "候选专题"})
        note_item = add_collection_item(
            db,
            user_id="user-manual",
            collection_id=collection["id"],
            payload={"item_type": "note", "item_id": "note-source"},
        )

        candidates, total = list_collection_candidates(
            db,
            user_id="user-manual",
            collection_id=collection["id"],
            query="候选",
            item_type="entity",
            params=PageParams(page=1, page_size=20),
        )
        entity_item = add_collection_item(
            db,
            user_id="user-manual",
            collection_id=collection["id"],
            payload={"item_type": "entity", "item_id": entity_id},
        )
        detail = get_collection_detail(db, user_id="user-manual", collection_id=collection["id"])
        evidence = list_manual_evidence(db, user_id="user-manual", target_type="entity", target_id=entity_id)
        reordered = reorder_collection_items(
            db,
            user_id="user-manual",
            collection_id=collection["id"],
            item_ids=[entity_item["id"], note_item["id"]],
        )
        removed = bulk_remove_collection_items(
            db,
            user_id="user-manual",
            collection_id=collection["id"],
            item_ids=[note_item["id"]],
        )

    assert total == 1 and candidates[0]["item_id"] == entity_id
    assert detail["stats"]["by_type"] == {"note": 1, "entity": 1}
    assert detail["stats"]["evidence_coverage"] == 1
    assert next(item for item in detail["items"] if item["item_type"] == "entity")["has_evidence"] is True
    assert evidence["total"] == 1 and evidence["items"][0]["source_title"] == "访谈笔记"
    assert reordered["item_ids"][0] == entity_item["id"]
    assert removed["removed_ids"] == [note_item["id"]]


def test_collection_graph_scope_contains_only_selected_knowledge_nodes() -> None:
    with make_session() as db:
        seed_user_and_note(db)
        entity = Entity(
            id="entity-collection-graph",
            user_id="user-manual",
            entity_type="person",
            canonical_name="专题人物",
            display_name="专题人物",
            alias_json=[],
            normalized_name="专题人物",
            status="active",
        )
        event = Event(id="event-collection-graph", user_id="user-manual", title="专题事件", status="active", time_precision="day")
        db.add_all([entity, event])
        db.flush()
        db.add(EventEntity(event_id=event.id, entity_id=entity.id, relation_type="participates_in", display_order=0))
        db.commit()
        collection = create_collection(db, user_id="user-manual", payload={"title": "图谱专题"})
        add_collection_item(db, user_id="user-manual", collection_id=collection["id"], payload={"item_type": "event", "item_id": event.id})
        add_collection_item(db, user_id="user-manual", collection_id=collection["id"], payload={"item_type": "entity", "item_id": entity.id})

        workspace = get_graph_workspace(db, user_id="user-manual", collection_id=collection["id"])

    assert workspace["scope"] == "collection"
    assert {node["id"] for node in workspace["nodes"]} == {event.id, entity.id}
    assert workspace["edges"][0]["edge_type"] == "participates_in"

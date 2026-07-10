from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.domains.retrieval.graph_query import (
    build_entity_timeline_fragments,
    build_graph_overview_network,
    build_related_event_suggestions,
)
from app.domains.retrieval.graph_workspace import (
    apply_workspace_filters,
    attach_canonical_relation_edges,
    build_workspace_conflicts,
    graph_action_diff_summary,
    normalize_graph_filters,
)
from app.domains.governance.graph_conflicts import (
    apply_graph_conflict_dispositions,
    set_graph_conflict_disposition,
)
from app.domains.retrieval.graph_paths import find_graph_path
from app.domains.retrieval.graph_viewpoints import (
    create_graph_viewpoint,
    delete_graph_viewpoint,
    update_graph_viewpoint,
)
from app.models.entity import Entity, EventEntity, Relation
from app.models.event import Event
from app.models.graph_conflict import GraphConflictDisposition
from app.models.graph_viewpoint import GraphViewpoint
from app.models.review import ReviewAction
from app.models.user import User


def test_build_related_event_suggestions_prioritizes_shared_people_and_similarity() -> None:
    current_event = {
        "id": "evt-1",
        "participants": [
            {"id": "person-1", "display_name": "张三"},
            {"id": "person-2", "display_name": "李四"},
        ],
        "location_text": "会议室A",
        "sort_time": "2026-04-18T00:00:00+00:00",
    }
    candidates = [
        {
            "id": "evt-2",
            "title": "图谱拆分补充会",
            "summary": "补充讨论图谱拆分。",
            "time_text": "2026-04-19",
            "event_type": "meeting",
            "location_text": "会议室A",
            "sort_time": "2026-04-19T00:00:00+00:00",
            "participants": [
                {"id": "person-1", "display_name": "张三"},
                {"id": "person-3", "display_name": "王五"},
            ],
            "source_note_title": "补充记录",
        },
        {
            "id": "evt-3",
            "title": "完全无关事件",
            "summary": "另一条记录。",
            "time_text": "2026-05-10",
            "event_type": "record",
            "location_text": "远程",
            "sort_time": "2026-05-10T00:00:00+00:00",
            "participants": [
                {"id": "person-9", "display_name": "赵六"},
            ],
            "source_note_title": "其他记录",
        },
    ]

    suggestions = build_related_event_suggestions(current_event, candidates, {"evt-2": 0.91})

    assert len(suggestions) == 1
    assert suggestions[0]["id"] == "evt-2"
    assert "共享人物" in suggestions[0]["connection_reasons"]
    assert "同地点" in suggestions[0]["connection_reasons"]
    assert "语义相近" in suggestions[0]["connection_reasons"]
    assert suggestions[0]["shared_participants"] == ["张三"]


def test_build_entity_timeline_fragments_sorts_by_time_and_assigns_labels() -> None:
    fragments = build_entity_timeline_fragments(
        [
            {
                "id": "evt-2",
                "title": "补充记录",
                "summary": "第二次出现",
                "time_text": "2026-04-19",
                "event_type": "record",
                "location_text": "会议室A",
                "sort_time": "2026-04-19T00:00:00+00:00",
                "role": "参与者",
                "relation_type": "参与",
                "source_note_title": "补充卷宗",
            },
            {
                "id": "evt-1",
                "title": "项目启动会",
                "summary": "第一次出现",
                "time_text": "2026-04-18",
                "event_type": "meeting",
                "location_text": "会议室A",
                "sort_time": "2026-04-18T00:00:00+00:00",
                "role": "参与者",
                "relation_type": "参与",
                "source_note_title": "启动卷宗",
            },
        ]
    )

    assert [item["event_id"] for item in fragments] == ["evt-1", "evt-2"]
    assert fragments[0]["chapter_label"] == "初现"
    assert fragments[1]["chapter_label"] == "最近回响"
    assert fragments[1]["position"] == 2


def test_build_graph_overview_network_deduplicates_edges_and_reports_stats() -> None:
    overview = build_graph_overview_network(
        event_rows=[
            {"id": "evt-1", "title": "项目启动会", "time_text": "2026-04-18", "event_type": "meeting", "importance": 0.8},
            {"id": "evt-2", "title": "补充记录", "time_text": "2026-04-19", "event_type": "record", "importance": 0.7},
        ],
        entity_rows=[
            {"id": "ent-1", "display_name": "张三", "entity_type": "person", "importance": 0.9},
        ],
        event_entity_links=[
            {"event_id": "evt-1", "entity_id": "ent-1", "role": "参与者", "weight": 0.8},
            {"event_id": "evt-1", "entity_id": "ent-1", "role": "参与者", "weight": 0.8},
        ],
        event_event_links=[
            {"source_id": "evt-1", "target_id": "evt-2", "reasons": ["共享人物", "时间接近"], "weight": 0.72},
            {"source_id": "evt-2", "target_id": "evt-1", "reasons": ["共享人物", "时间接近"], "weight": 0.72},
        ],
        timeline_rows=[
            {"id": "tl-1", "event_id": "evt-1", "title": "项目启动会"},
            {"id": "tl-2", "event_id": "evt-2", "title": "补充记录"},
        ],
    )

    assert overview["stats"] == {
        "event_count": 2,
        "entity_count": 1,
        "timeline_count": 2,
        "edge_count": 2,
    }
    assert len(overview["nodes"]) == 3
    assert overview["edges"][0]["edge_type"] == "participates_in"
    assert overview["edges"][1]["edge_type"] == "relates_to"


def test_graph_workspace_filters_keep_unconnected_nodes_without_active_graph_filters() -> None:
    workspace = {
        "scope": "overview",
        "title": "测试图谱",
        "description": "测试",
        "anchor": None,
        "nodes": [
            {"id": "evt-1", "node_type": "event", "label": "事件一", "subtitle": "2026-04-18", "meta": []},
            {"id": "ent-1", "node_type": "entity", "label": "人物一", "subtitle": "person", "meta": []},
            {"id": "evt-2", "node_type": "event", "label": "孤立事件", "subtitle": "2026-04-19", "meta": []},
        ],
        "edges": [{"source_id": "evt-1", "target_id": "ent-1", "edge_type": "participates_in", "label": "参与", "weight": 0.8}],
        "timeline_focus": [{"id": "evt-1", "event_id": "evt-1", "title": "事件一"}],
        "stats": {},
    }

    filtered = apply_workspace_filters(workspace, normalize_graph_filters())

    assert {node["id"] for node in filtered["nodes"]} == {"evt-1", "ent-1", "evt-2"}
    assert filtered["filters"]["applied"]["node_types"] == []


def test_graph_workspace_filters_apply_relation_weight_and_time_window() -> None:
    workspace = {
        "scope": "overview",
        "title": "测试图谱",
        "description": "测试",
        "anchor": None,
        "nodes": [
            {"id": "evt-1", "node_type": "event", "label": "保留事件", "subtitle": "2026-04-18", "meta": []},
            {"id": "ent-1", "node_type": "entity", "label": "保留人物", "subtitle": "person", "meta": []},
            {"id": "evt-2", "node_type": "event", "label": "过早事件", "subtitle": "2026-04-01", "meta": []},
            {"id": "ent-2", "node_type": "entity", "label": "低权重人物", "subtitle": "person", "meta": []},
        ],
        "edges": [
            {"source_id": "evt-1", "target_id": "ent-1", "edge_type": "participates_in", "label": "参与", "weight": 0.8},
            {"source_id": "evt-1", "target_id": "ent-2", "edge_type": "participates_in", "label": "弱关联", "weight": 0.3},
            {"source_id": "evt-2", "target_id": "ent-1", "edge_type": "participates_in", "label": "过早", "weight": 0.9},
        ],
        "timeline_focus": [
            {"id": "evt-1", "event_id": "evt-1", "title": "保留事件"},
            {"id": "evt-2", "event_id": "evt-2", "title": "过早事件"},
        ],
        "stats": {},
    }

    filtered = apply_workspace_filters(
        workspace,
        normalize_graph_filters(relation_types="participates_in", start="2026-04-10", min_weight=0.7),
    )

    assert {node["id"] for node in filtered["nodes"]} == {"evt-1", "ent-1"}
    assert [edge["label"] for edge in filtered["edges"]] == ["参与"]
    assert [item["event_id"] for item in filtered["timeline_focus"]] == ["evt-1"]


def test_graph_workspace_conflicts_flag_low_confidence_label_conflict_and_orphan_nodes() -> None:
    nodes = [
        {"id": "evt-1", "node_type": "event", "label": "事件一", "subtitle": "2026-04-18", "meta": []},
        {"id": "ent-1", "node_type": "entity", "label": "人物一", "subtitle": "person", "meta": []},
        {"id": "ent-2", "node_type": "entity", "label": "孤立人物", "subtitle": "person", "meta": []},
    ]
    edges = [
        {"source_id": "evt-1", "target_id": "ent-1", "edge_type": "participates_in", "label": "参与者", "weight": 0.4},
        {"source_id": "evt-1", "target_id": "ent-1", "edge_type": "participates_in", "label": "主持人", "weight": 0.8},
    ]

    conflicts = build_workspace_conflicts(nodes, edges)

    assert {item["conflict_type"] for item in conflicts} == {
        "low_confidence_edge",
        "relation_label_conflict",
        "orphan_node",
    }
    assert any(item["node_ids"] == ["ent-2"] for item in conflicts)


def test_graph_workspace_conflicts_offer_relation_id_resolution_actions() -> None:
    nodes = [
        {"id": "evt-1", "node_type": "event", "label": "事件一", "subtitle": "event", "meta": []},
        {"id": "ent-1", "node_type": "entity", "label": "人物一", "subtitle": "person", "meta": []},
    ]
    edges = [
        {
            "id": "relation:rel-1",
            "relation_id": "rel-1",
            "fact_type": "relation",
            "source_id": "evt-1",
            "target_id": "ent-1",
            "source_type": "event",
            "target_type": "entity",
            "edge_type": "supports",
            "label": "supports",
            "weight": 0.3,
            "evidence_count": 1,
            "is_editable": True,
        }
    ]

    conflicts = build_workspace_conflicts(nodes, edges)

    low_confidence = next(item for item in conflicts if item["conflict_type"] == "low_confidence_edge")
    assert low_confidence["actions"] == [
        {
            "label": "删除低置信关系",
            "action_type": "remove_relation",
            "relation_id": "rel-1",
            "owner_type": "event",
            "owner_id": "evt-1",
        }
    ]


def test_graph_action_diff_summary_describes_relation_shape_changes() -> None:
    action = ReviewAction(
        target_type="relation",
        target_id="rel-1",
        action_type="update_relation",
        payload_json={
            "before": {
                "source_type": "event",
                "source_id": "evt-1",
                "relation_type": "supports",
                "target_type": "entity",
                "target_id": "ent-1",
            },
            "after": {
                "source_type": "event",
                "source_id": "evt-1",
                "relation_type": "blocks",
                "target_type": "entity",
                "target_id": "ent-1",
            },
        },
    )

    summary = graph_action_diff_summary(action)

    assert summary is not None
    assert "supports" in summary
    assert "blocks" in summary
    assert "relation_type" in summary


def test_attach_canonical_relation_edges_exposes_first_class_relation_id() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[User.__table__, Event.__table__, Entity.__table__, Relation.__table__],
    )
    Session = sessionmaker(bind=engine)
    with Session() as db:
        db.add(User(id="user-graph", username="graph", password_hash="hash", display_name="Graph"))
        db.add(Event(id="event-graph", user_id="user-graph", title="事件", status="active", time_precision="day"))
        db.add(
            Entity(
                id="entity-graph",
                user_id="user-graph",
                entity_type="person",
                canonical_name="人物",
                display_name="人物",
                alias_json=[],
                normalized_name="人物",
                status="active",
            )
        )
        db.add(
            Relation(
                id="relation-graph",
                user_id="user-graph",
                source_type="event",
                source_id="event-graph",
                relation_type="supports",
                target_type="entity",
                target_id="entity-graph",
                evidence_count=2,
                confidence_score=0.42,
                meta_json={"source": "llm_relation"},
            )
        )
        db.commit()
        workspace = {
            "nodes": [
                {"id": "event-graph", "node_type": "event"},
                {"id": "entity-graph", "node_type": "entity"},
            ],
            "edges": [],
        }

        enriched = attach_canonical_relation_edges(db, workspace, user_id="user-graph")

    assert enriched["edges"] == [
        {
            "id": "relation:relation-graph",
            "relation_id": "relation-graph",
            "fact_type": "relation",
            "source_id": "event-graph",
            "target_id": "entity-graph",
            "source_type": "event",
            "target_type": "entity",
            "edge_type": "supports",
            "label": "supports",
            "weight": 0.42,
            "evidence_count": 2,
            "is_editable": True,
        }
    ]


def test_graph_viewpoints_can_be_renamed_and_deleted_by_owner() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[User.__table__, GraphViewpoint.__table__])
    Session = sessionmaker(bind=engine)
    with Session() as db:
        db.add(User(id="user-view", username="view", password_hash="hash", display_name="View"))
        db.commit()
        created = create_graph_viewpoint(
            db,
            user_id="user-view",
            payload={"name": "旧视角", "scope": "overview"},
        )

        updated = update_graph_viewpoint(
            db,
            user_id="user-view",
            viewpoint_id=created["id"],
            payload={"name": "新视角"},
        )
        deleted = delete_graph_viewpoint(db, user_id="user-view", viewpoint_id=created["id"])

    assert updated["name"] == "新视角"
    assert deleted == {"id": created["id"], "status": "deleted"}


def test_graph_conflict_disposition_retains_data_and_marks_conflict_inactive() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[User.__table__, GraphConflictDisposition.__table__, ReviewAction.__table__],
    )
    Session = sessionmaker(bind=engine)
    conflict = {
        "id": "low-confidence-event-entity-supports",
        "severity": "medium",
        "conflict_type": "low_confidence_edge",
        "title": "低置信关系",
        "summary": "需要人工确认",
        "node_ids": ["event", "entity"],
        "edge_label": "supports",
        "href": "/graph",
        "actions": [],
    }
    with Session() as db:
        db.add(User(id="user-conflict", username="conflict", password_hash="hash", display_name="Conflict"))
        db.commit()
        disposition = set_graph_conflict_disposition(
            db,
            user_id="user-conflict",
            conflict_id=conflict["id"],
            payload={"disposition": "keep", "note": "人工确认应保留", **conflict},
        )
        decorated = apply_graph_conflict_dispositions(db, user_id="user-conflict", conflicts=[conflict])
        audit = db.query(ReviewAction).one()

    assert disposition["disposition"] == "keep"
    assert decorated[0]["is_active"] is False
    assert decorated[0]["disposition_note"] == "人工确认应保留"
    assert audit.status_before == "open"
    assert audit.status_after == "keep"


def test_find_graph_path_explains_relation_and_participation_hops() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[User.__table__, Event.__table__, Entity.__table__, EventEntity.__table__, Relation.__table__],
    )
    Session = sessionmaker(bind=engine)
    with Session() as db:
        db.add(User(id="user-path", username="path", password_hash="hash", display_name="Path"))
        db.add_all(
            [
                Event(id="event-a", user_id="user-path", title="事件 A", status="active", time_precision="day"),
                Entity(
                    id="entity-b",
                    user_id="user-path",
                    entity_type="person",
                    canonical_name="人物 B",
                    display_name="人物 B",
                    alias_json=[],
                    normalized_name="人物b",
                    status="active",
                ),
                Entity(
                    id="entity-c",
                    user_id="user-path",
                    entity_type="person",
                    canonical_name="人物 C",
                    display_name="人物 C",
                    alias_json=[],
                    normalized_name="人物c",
                    status="active",
                ),
            ]
        )
        db.flush()
        db.add(EventEntity(event_id="event-a", entity_id="entity-b", role="主持人", relation_type="hosts"))
        db.add(
            Relation(
                id="relation-b-c",
                user_id="user-path",
                source_type="entity",
                source_id="entity-b",
                relation_type="supports",
                target_type="entity",
                target_id="entity-c",
                evidence_count=2,
                confidence_score=0.8,
                meta_json={},
            )
        )
        db.commit()

        result = find_graph_path(
            db,
            user_id="user-path",
            source_type="event",
            source_id="event-a",
            target_type="entity",
            target_id="entity-c",
            max_depth=3,
        )

    assert result["found"] is True
    assert result["total_hops"] == 2
    assert [item["label"] for item in result["nodes"]] == ["事件 A", "人物 B", "人物 C"]
    assert "hosts" in result["edges"][0]["explanation"]
    assert "2 条证据" in result["edges"][1]["explanation"]

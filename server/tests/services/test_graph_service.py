from app.services.graph_service import (
    build_entity_timeline_fragments,
    build_graph_overview_network,
    build_related_event_suggestions,
)


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

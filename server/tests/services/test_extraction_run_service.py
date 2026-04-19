from app.services.extraction_run_service import compare_extraction_payloads, summarize_run_payload


def test_compare_extraction_payloads_detects_summary_entity_and_event_changes() -> None:
    base_payload = {
        "summary": {
            "title": "项目启动会议",
            "short_summary": "张三和李四讨论图谱导入。",
            "canonical_text": "2026-04-18 张三和李四在会议室A召开项目启动会。",
            "category": "knowledge",
            "tags": ["启动会"],
        },
        "entities": [
            {
                "entity_type": "person",
                "canonical_name": "张三",
                "aliases": [],
                "description": "参与者",
                "confidence": 0.75,
            }
        ],
        "events": [
            {
                "title": "项目启动会议",
                "event_type": "meeting",
                "summary": "讨论图谱导入。",
                "time": {"time_text": "2026-04-18", "timeline_sort_time": "2026-04-18T00:00:00+00:00"},
                "participants": [{"entity_temp_id": "ent_1"}],
                "locations": [{"name": "会议室A"}],
                "confidence": 0.7,
            }
        ],
        "relations": [
            {
                "source_ref": {"type": "entity", "temp_id": "ent_1"},
                "relation_type": "participates_in",
                "target_ref": {"type": "event", "temp_id": "evt_1"},
                "confidence": 0.75,
            }
        ],
        "similarity_hints": [],
        "style_payload": {
            "title": "命运卷宗：项目启动会议",
            "character_cards": [{"display_name": "张三", "epithet": "事件见证者"}],
            "event_narrative": [{"headline": "序章", "body": "张三留下回响。"}],
        },
    }
    candidate_payload = {
        **base_payload,
        "summary": {
            **base_payload["summary"],
            "title": "项目启动会：图谱导入",
            "tags": ["启动会", "图谱"],
        },
        "entities": [
            *base_payload["entities"],
            {
                "entity_type": "person",
                "canonical_name": "李四",
                "aliases": [],
                "description": "参与者",
                "confidence": 0.78,
            },
        ],
        "events": [
            {
                **base_payload["events"][0],
                "summary": "讨论图谱导入与拆分计划。",
                "participants": [{"entity_temp_id": "ent_1"}, {"entity_temp_id": "ent_2"}],
            }
        ],
    }

    diff = compare_extraction_payloads(base_payload, candidate_payload)

    assert diff["changed"] is True
    assert diff["summary"]["changed"] is True
    assert [item["field"] for item in diff["summary"]["fields"] if item["changed"]] == ["title", "tags"]
    assert diff["entities"]["added"][0]["name"] == "李四"
    assert diff["entities"]["unchanged_count"] == 1
    assert diff["events"]["changed_items"][0]["candidate"]["participant_count"] == 2
    assert diff["relations"]["changed"] is False


def test_compare_extraction_payloads_reports_unchanged_payloads() -> None:
    payload = {
        "summary": {"title": "启动会", "short_summary": "摘要", "canonical_text": "正文", "category": "knowledge", "tags": []},
        "entities": [],
        "events": [],
        "relations": [],
        "similarity_hints": [],
        "style_payload": {"title": "命运卷宗", "character_cards": [], "event_narrative": []},
    }

    diff = compare_extraction_payloads(payload, payload)

    assert diff["changed"] is False
    assert diff["summary"]["changed"] is False
    assert diff["entities"]["base_count"] == 0


def test_summarize_run_payload_counts_core_sections() -> None:
    summary = summarize_run_payload(
        {
            "summary": {"title": "启动会", "category": "knowledge"},
            "entities": [{}, {}],
            "events": [{}],
            "relations": [{}, {}, {}],
            "similarity_hints": [{}],
        }
    )

    assert summary == {
        "title": "启动会",
        "category": "knowledge",
        "entity_count": 2,
        "event_count": 1,
        "relation_count": 3,
        "similarity_hint_count": 1,
    }

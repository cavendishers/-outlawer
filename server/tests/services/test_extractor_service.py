from app.core.config import get_settings
from app.domains.extraction.chat_provider import ChatModelProvider
from app.domains.extraction.extractor import build_extraction_payload
from app.domains.extraction.openrouter import (
    build_media_content_item,
    chunk_model_candidates,
    extract_json_object,
    get_model_candidates,
    infer_audio_format,
)


def test_build_extraction_payload_contains_expected_layers(monkeypatch) -> None:
    monkeypatch.setenv("EXTRACTOR_PROVIDER", "heuristic")
    get_settings.cache_clear()

    payload = build_extraction_payload(
        note_id="note-1",
        asset_id="asset-1",
        text="2026-04-18 张三和李四在会议室A召开项目启动会，讨论图谱与导入流程。",
    )

    assert payload["source"]["note_id"] == "note-1"
    assert payload["summary"]["title"]
    assert payload["events"][0]["title"] == "项目启动会议"
    assert payload["timeline"][0]["title"] == payload["events"][0]["title"]
    assert payload["style_payload"]["theme"] == "chunibyo"
    assert payload["embedding"]
    assert any(entity["canonical_name"] == "张三" for entity in payload["entities"])
    get_settings.cache_clear()


def test_build_extraction_payload_keeps_relation_shape_stable(monkeypatch) -> None:
    monkeypatch.setenv("EXTRACTOR_PROVIDER", "heuristic")
    get_settings.cache_clear()

    payload = build_extraction_payload(
        note_id="note-2",
        asset_id=None,
        text="王五在2026-04-19复盘项目启动会。",
    )

    relation_types = {item["relation_type"] for item in payload["relations"]}
    assert "source_of" in relation_types
    assert "participates_in" in relation_types
    assert payload["events"][0]["time"]["timeline_sort_time"]
    get_settings.cache_clear()


def test_build_extraction_payload_filters_noisy_person_candidates(monkeypatch) -> None:
    monkeypatch.setenv("EXTRACTOR_PROVIDER", "heuristic")
    get_settings.cache_clear()

    payload = build_extraction_payload(
        note_id="note-3",
        asset_id=None,
        text="2026-04-19 张三和李四再次记录项目启动会，补充图谱拆分与导入流程。",
    )

    person_names = [entity["canonical_name"] for entity in payload["entities"] if entity["entity_type"] == "person"]

    assert person_names == ["张三", "李四"]
    assert [item["entity_temp_id"] for item in payload["events"][0]["participants"]] == ["ent_1", "ent_2"]
    get_settings.cache_clear()


def test_build_extraction_payload_uses_deepseek_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("EXTRACTOR_PROVIDER", "deepseek")
    monkeypatch.setenv("CHAT_API_KEY", "test-key")
    monkeypatch.setenv("CHAT_MODEL", "deepseek-chat")
    get_settings.cache_clear()

    class FakeProvider(ChatModelProvider):
        def extract_structured_knowledge(self, note_id: str, asset_id: str | None, text: str) -> dict:
            return {
                "summary": {
                    "title": "命运启动记录",
                    "short_summary": "张三与李四确认知识库建设方向。",
                    "canonical_text": text,
                    "category": "project",
                    "tags": ["启动会", "知识库"],
                },
                "entities": [
                    {
                        "temp_id": "ent_a",
                        "entity_type": "person",
                        "name": "张三",
                        "canonical_name": "张三",
                        "aliases": [],
                        "description": "发起人",
                        "confidence": 0.92,
                        "evidence": [{"text": "张三", "start": 11, "end": 13}],
                    },
                    {
                        "temp_id": "ent_b",
                        "entity_type": "person",
                        "name": "李四",
                        "canonical_name": "李四",
                        "aliases": [],
                        "description": "参与者",
                        "confidence": 0.9,
                        "evidence": [{"text": "李四", "start": 14, "end": 16}],
                    },
                ],
                "events": [
                    {
                        "temp_id": "evt_ai",
                        "title": "知识库启动会",
                        "event_type": "meeting",
                        "summary": "确定在线知识库的建设方向。",
                        "description": "围绕人物、事件、时间线和 AI 整理能力展开讨论。",
                        "time": {
                            "time_text": "2026-04-18",
                            "start_time": "2026-04-18T00:00:00+00:00",
                            "end_time": None,
                            "time_precision": "day",
                            "timeline_sort_time": "2026-04-18T00:00:00+00:00",
                        },
                        "participants": [
                            {"entity_temp_id": "ent_a", "role": "participant", "relation_type": "participates_in"},
                            {"entity_temp_id": "ent_b", "role": "participant", "relation_type": "participates_in"},
                        ],
                        "locations": [{"name": "会议室A", "entity_temp_id": None}],
                        "confidence": 0.88,
                        "evidence": [{"text": "启动会", "start": 0, "end": 3}],
                    }
                ],
                "similarity_hints": [
                    {"target_type": "note", "target_id": "note_old_1", "reason": "主题接近", "confidence": 0.8}
                ],
                "style_payload": {
                    "theme": "chunibyo",
                    "title": "命运卷宗：知识库启动会",
                    "character_cards": [
                        {
                            "entity_temp_id": "ent_a",
                            "display_name": "张三",
                            "epithet": "起始之钥",
                            "aura": "在静默中推开序章之门。",
                        }
                    ],
                    "event_narrative": [
                        {
                            "event_temp_id": "evt_ai",
                            "headline": "序章会议",
                            "body": "命运的知识之轮开始转动。",
                        }
                    ],
                },
            }

    monkeypatch.setattr("app.domains.extraction.extractor.build_chat_model_provider", lambda: FakeProvider())

    payload = build_extraction_payload(
        note_id="note-ai",
        asset_id="asset-ai",
        text="2026-04-18 张三和李四在会议室A召开项目启动会，讨论图谱与导入流程。",
    )

    assert payload["source"]["extractor_name"] == "deepseek"
    assert payload["summary"]["title"] == "命运启动记录"
    assert payload["events"][0]["title"] == "知识库启动会"
    assert len(payload["entities"]) == 2
    assert [entity["canonical_name"] for entity in payload["entities"]] == ["张三", "李四"]
    assert [item["entity_temp_id"] for item in payload["events"][0]["participants"]] == ["ent_a", "ent_b"]
    assert payload["style_payload"]["title"] == "命运卷宗：知识库启动会"
    assert payload["similarity_hints"][0]["target_type"] == "note"
    assert payload["relations"][1]["target_ref"]["temp_id"] == "evt_ai"

    monkeypatch.delenv("EXTRACTOR_PROVIDER", raising=False)
    monkeypatch.delenv("CHAT_API_KEY", raising=False)
    monkeypatch.delenv("CHAT_MODEL", raising=False)
    get_settings.cache_clear()


def test_build_extraction_payload_auto_falls_back_without_chat_key(monkeypatch) -> None:
    monkeypatch.setenv("EXTRACTOR_PROVIDER", "auto")
    monkeypatch.delenv("CHAT_API_KEY", raising=False)
    monkeypatch.delenv("CHAT_MODEL", raising=False)
    get_settings.cache_clear()

    payload = build_extraction_payload(
        note_id="note-auto",
        asset_id=None,
        text="2026-04-18 张三和李四在会议室A召开项目启动会，讨论图谱与导入流程。",
    )

    assert payload["source"]["extractor_name"] == "heuristic_pipeline"
    assert payload["summary"]["title"]
    get_settings.cache_clear()


def test_openrouter_model_candidates_include_free_fallbacks(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_MODEL", "google/gemma-3-27b-it:free")
    get_settings.cache_clear()

    candidates = get_model_candidates()

    assert candidates[0] == "google/gemma-3-27b-it:free"
    assert "qwen/qwen3-next-80b-a3b-instruct:free" in candidates
    assert len(candidates) == len(set(candidates))

    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    get_settings.cache_clear()


def test_openrouter_model_candidates_are_chunked_by_three() -> None:
    batches = chunk_model_candidates(
        [
            "model-1",
            "model-2",
            "model-3",
            "model-4",
            "model-5",
            "model-6",
            "model-7",
        ]
    )

    assert batches == [
        ["model-1", "model-2", "model-3"],
        ["model-4", "model-5", "model-6"],
        ["model-7"],
    ]


def test_multimodal_helpers_build_expected_content_items() -> None:
    image_item = build_media_content_item("image", "image/png", b"png-bytes")
    audio_item = build_media_content_item("audio", "audio/mpeg", b"mp3-bytes")
    video_item = build_media_content_item("video", "video/mp4", b"mp4-bytes")

    assert image_item["type"] == "image_url"
    assert image_item["image_url"]["url"].startswith("data:image/png;base64,")
    assert audio_item["type"] == "input_audio"
    assert audio_item["input_audio"]["format"] == "mp3"
    assert video_item["type"] == "video_url"
    assert video_item["video_url"]["url"].startswith("data:video/mp4;base64,")


def test_multimodal_helpers_parse_json_with_fences_and_audio_format_fallbacks() -> None:
    parsed = extract_json_object("```json\n{\"canonical_text\":\"图像里写着张三\"}\n```")

    assert parsed["canonical_text"] == "图像里写着张三"
    assert infer_audio_format("audio/x-wav") == "wav"
    assert infer_audio_format("audio/ogg") == "ogg"

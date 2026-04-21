import logging
import re
from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings
from app.domains.extraction.openrouter import openrouter_enabled, request_openrouter_extraction
from app.utils.datetime import extract_time
from app.utils.text import extract_tags, normalize_name, summarize_text, text_to_vector

logger = logging.getLogger("outlawer.extractor")

ENTITY_STOPWORDS = {
    "今天",
    "昨天",
    "会议",
    "项目",
    "记录",
    "启动",
    "启动会",
    "讨论",
    "图谱",
    "导入",
    "流程",
    "会议室",
    "召开",
    "复盘",
}

COMMON_CHINESE_SURNAMES = set(
    "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜"
    "戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳鲍史唐"
    "费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平"
    "黄和穆萧尹姚邵湛汪祁毛禹狄米贝明臧计伏成戴谈宋茅庞熊纪舒屈项祝"
    "董梁杜阮蓝闵席季麻强贾路娄危江童颜郭梅盛林刁钟徐邱骆高夏蔡田樊"
    "胡凌霍虞万支柯昝管卢莫经房裘缪干解应宗丁宣贲邓郁单杭洪包诸左石"
    "崔吉钮龚程嵇邢滑裴陆荣翁荀羊於惠甄曲家封芮羿储靳汲邴糜松井段富"
    "巫乌焦巴弓牧隗山谷车侯宓蓬全郗班仰秋仲伊宫宁仇栾暴甘斜厉戎祖武"
    "符刘景詹束龙叶幸司韶郜黎蓟薄印宿白怀蒲台从鄂索咸籍赖卓蔺屠蒙池"
    "乔阴鬱胥能苍双闻莘党翟谭贡劳逄姬申扶堵冉宰郦雍郤璩桑桂濮牛寿通"
    "边扈燕冀郏浦尚农温别庄晏柴瞿阎充慕连茹习宦艾鱼容向古易慎戈廖庾"
    "终暨居衡步都耿满弘匡国文寇广禄阙东欧殳沃利蔚越夔隆师巩厍聂晁勾"
    "敖融冷訾辛阚那简饶空曾毋沙乜养鞠须丰巢关蒯相查后荆红游竺权逯盖"
    "益桓公"
)
COMMON_COMPOUND_SURNAMES = {
    "欧阳",
    "司马",
    "上官",
    "诸葛",
    "东方",
    "独孤",
    "夏侯",
    "尉迟",
    "长孙",
    "宇文",
    "司徒",
    "司空",
    "慕容",
    "令狐",
}
PERSON_CONTEXT_STOPWORDS = ENTITY_STOPWORDS | {"再次", "补充", "确认", "提出", "参与"}
PERSON_INVALID_PARTICLES = {"和", "与", "及", "在", "于", "的"}
PERSON_INVALID_SUFFIXES = {"在", "于", "的", "再"}
PERSON_BOUNDARY_PATTERN = r"(?=在|于|再次|记录|发起|补充|确认|讨论|参加|出席|复盘|提出|召开|，|。|,|$)"


def is_valid_entity_candidate(value: str) -> bool:
    normalized = normalize_name(value)
    if not normalized or normalized in ENTITY_STOPWORDS:
        return False
    return not any(stopword in value for stopword in ENTITY_STOPWORDS if len(stopword) > 1)


def is_valid_person_name(value: str) -> bool:
    candidate = value.strip()
    if re.fullmatch(r"[A-Z][a-z]+(?:\s[A-Z][a-z]+){0,2}", candidate):
        return True
    if not re.fullmatch(r"[\u4e00-\u9fff]{2,4}", candidate):
        return False
    if any(particle in candidate for particle in PERSON_INVALID_PARTICLES):
        return False
    if any(candidate.endswith(suffix) for suffix in PERSON_INVALID_SUFFIXES):
        return False
    if any(stopword in candidate for stopword in PERSON_CONTEXT_STOPWORDS if len(stopword) > 1):
        return False
    if candidate[:2] in COMMON_COMPOUND_SURNAMES:
        return 1 <= len(candidate[2:]) <= 2
    return candidate[0] in COMMON_CHINESE_SURNAMES


def is_valid_ai_entity_candidate(name: str, entity_type: str) -> bool:
    if not is_valid_entity_candidate(name):
        return False
    if entity_type == "person":
        return is_valid_person_name(name)
    return True


def build_heuristic_extraction_payload(note_id: str, asset_id: str | None, text: str) -> dict:
    start_time, time_text, precision = extract_time(text)
    title = summarize_text(text, limit=32) or "未命名记录"
    tags = extract_tags(text)

    raw_entities = []
    for match in re.finditer(rf"([\u4e00-\u9fff]{{2,4}})和([\u4e00-\u9fff]{{2,4}}?){PERSON_BOUNDARY_PATTERN}", text):
        for candidate in (match.group(1), match.group(2)):
            if is_valid_person_name(candidate):
                raw_entities.append(candidate)

    for match in re.finditer(
        rf"([\u4e00-\u9fff]{{2,4}})(?=在|于|与|和|及|、|记录|发起|补充|确认|讨论|参加|出席|复盘|提出|召开)",
        text,
    ):
        candidate = match.group(1)
        if is_valid_person_name(candidate):
            raw_entities.append(candidate)

    for candidate in re.findall(r"[A-Z][a-z]+(?:\s[A-Z][a-z]+){0,2}", text):
        if is_valid_person_name(candidate):
            raw_entities.append(candidate)

    entity_names = []
    for name in raw_entities:
        if name not in entity_names:
            entity_names.append(name)
    entity_names = entity_names[:5]

    event_type = "meeting" if "会" in text else "record"
    event_title = "项目启动会议" if "启动" in text and "会" in text else title

    entities = []
    for index, name in enumerate(entity_names):
        entities.append(
            {
                "temp_id": f"ent_{index + 1}",
                "entity_type": "person",
                "name": name,
                "canonical_name": name,
                "aliases": [],
                "description": None,
                "confidence": 0.75,
                "evidence": [{"text": name, "start": text.find(name), "end": text.find(name) + len(name)}],
                "resolution_hint": {
                    "normalized_name": normalize_name(name),
                    "possible_existing_entity_ids": [],
                    "match_strategy": "normalized_name",
                },
            }
        )

    event = {
        "temp_id": "evt_1",
        "title": event_title,
        "event_type": event_type,
        "summary": summarize_text(text),
        "description": text,
        "time": {
            "time_text": time_text,
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": None,
            "time_precision": precision,
            "timeline_sort_time": start_time.isoformat() if start_time else datetime.now(UTC).isoformat(),
        },
        "participants": [
            {
                "entity_temp_id": entity["temp_id"],
                "role": "participant",
                "relation_type": "participates_in",
            }
            for entity in entities
        ],
        "locations": [],
        "confidence": 0.7,
        "evidence": [{"text": summarize_text(text, 48), "start": 0, "end": min(len(text), 48)}],
        "resolution_hint": {
            "possible_existing_event_ids": [],
            "match_strategy": "title+date",
        },
    }

    relations = [
        {
            "source_ref": {"type": "note", "id": note_id},
            "relation_type": "source_of",
            "target_ref": {"type": "event", "temp_id": "evt_1"},
            "confidence": 1.0,
            "evidence": [],
        }
    ]

    for entity in entities:
        relations.append(
            {
                "source_ref": {"type": "entity", "temp_id": entity["temp_id"]},
                "relation_type": "participates_in",
                "target_ref": {"type": "event", "temp_id": "evt_1"},
                "confidence": entity["confidence"],
                "evidence": entity["evidence"],
            }
        )

    timeline = [
        {
            "event_temp_id": "evt_1",
            "title": event_title,
            "summary": summarize_text(text),
            "display_time": time_text or "待校准",
            "sort_time": event["time"]["timeline_sort_time"],
            "time_precision": precision,
            "importance_score": 0.7,
        }
    ]

    style_payload = {
        "theme": "chunibyo",
        "title": f"命运卷宗：{event_title}",
        "character_cards": [
            {
                "entity_temp_id": entity["temp_id"],
                "display_name": entity["canonical_name"],
                "epithet": "事件见证者",
                "aura": f"{entity['canonical_name']}在碎片中留下回响。",
            }
            for entity in entities
        ],
        "event_narrative": [
            {
                "event_temp_id": "evt_1",
                "headline": f"序章：{event_title}",
                "body": f"在被记录的时间缝隙里，{summarize_text(text, 60)}",
            }
        ],
    }

    return {
        "source": {
            "note_id": note_id,
            "asset_id": asset_id,
            "content_type": "text",
            "language": "zh-CN",
            "extractor_name": "heuristic_pipeline",
            "extractor_version": "v1",
        },
        "summary": {
            "title": title,
            "short_summary": summarize_text(text),
            "canonical_text": text,
            "category": "knowledge",
            "tags": tags,
        },
        "entities": entities,
        "events": [event],
        "relations": relations,
        "timeline": timeline,
        "similarity_hints": [],
        "style_payload": style_payload,
        "embedding": text_to_vector(text),
    }


def build_extraction_payload(note_id: str, asset_id: str | None, text: str) -> dict:
    settings = get_settings()
    base_payload = build_heuristic_extraction_payload(note_id, asset_id, text)
    provider = settings.extractor_provider.lower()
    should_use_openrouter = provider == "openrouter" or (provider == "auto" and openrouter_enabled())
    if not should_use_openrouter:
        return base_payload

    try:
        ai_payload = request_openrouter_extraction(note_id, asset_id, text)
        return merge_openrouter_payload(note_id, asset_id, text, base_payload, ai_payload, settings.openrouter_model)
    except Exception as exc:  # noqa: BLE001
        logger.exception("openrouter_extraction_failed note_id=%s error=%s", note_id, exc)
        return base_payload


def merge_openrouter_payload(
    note_id: str,
    asset_id: str | None,
    text: str,
    base_payload: dict[str, Any],
    ai_payload: dict[str, Any],
    model_name: str | None,
) -> dict:
    summary = merge_summary(base_payload["summary"], ai_payload.get("summary"), text)
    entities = merge_entities(base_payload["entities"], ai_payload.get("entities"))
    event = merge_event(base_payload["events"][0], ai_payload.get("events"), entities)
    relations = build_relations(note_id, entities, event["temp_id"])
    timeline = build_timeline_from_event(event)
    style_payload = merge_style_payload(base_payload["style_payload"], ai_payload.get("style_payload"), entities, event)

    return {
        "source": {
            "note_id": note_id,
            "asset_id": asset_id,
            "content_type": "text",
            "language": "zh-CN",
            "extractor_name": "openrouter",
            "extractor_version": model_name or "account-default",
        },
        "summary": summary,
        "entities": entities,
        "events": [event],
        "relations": relations,
        "timeline": timeline,
        "similarity_hints": merge_similarity_hints(ai_payload.get("similarity_hints")),
        "style_payload": style_payload,
        "embedding": text_to_vector(text),
    }


def merge_summary(base_summary: dict[str, Any], ai_summary: Any, text: str) -> dict[str, Any]:
    if not isinstance(ai_summary, dict):
        return base_summary
    tags = ai_summary.get("tags")
    return {
        "title": safe_string(ai_summary.get("title"), base_summary["title"]),
        "short_summary": safe_string(ai_summary.get("short_summary"), base_summary["short_summary"]),
        "canonical_text": safe_string(ai_summary.get("canonical_text"), text),
        "category": safe_string(ai_summary.get("category"), base_summary["category"]),
        "tags": [item for item in tags if isinstance(item, str) and item][:5] if isinstance(tags, list) else base_summary["tags"],
    }


def merge_entities(base_entities: list[dict[str, Any]], ai_entities: Any) -> list[dict[str, Any]]:
    if not isinstance(ai_entities, list):
        return base_entities

    candidate_entities: list[dict[str, Any]] = []
    for index, item in enumerate(ai_entities):
        if not isinstance(item, dict):
            continue
        name = safe_string(item.get("canonical_name") or item.get("name"), "")
        entity_type = safe_string(item.get("entity_type"), "concept")
        if entity_type not in {"person", "org", "place", "concept"}:
            entity_type = "concept"
        normalized_name = normalize_name(name)
        if not normalized_name or not is_valid_ai_entity_candidate(name, entity_type):
            continue
        candidate_entities.append(
            {
                "temp_id": safe_string(item.get("temp_id"), f"ent_{index + 1}"),
                "entity_type": entity_type,
                "name": safe_string(item.get("name"), name),
                "canonical_name": name,
                "aliases": [alias for alias in item.get("aliases", []) if isinstance(alias, str)] if isinstance(item.get("aliases"), list) else [],
                "description": safe_string_or_none(item.get("description")),
                "confidence": safe_float(item.get("confidence"), 0.75),
                "evidence": merge_evidence_list(item.get("evidence"), name),
                "resolution_hint": {
                    "normalized_name": normalized_name,
                    "possible_existing_entity_ids": [],
                    "match_strategy": "normalized_name",
                },
            }
        )

    candidate_entities.sort(
        key=lambda entity: (
            len(entity["resolution_hint"]["normalized_name"]),
            -safe_float(entity.get("confidence"), 0.75),
        )
    )

    merged_entities: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for entity in candidate_entities:
        normalized_name = entity["resolution_hint"]["normalized_name"]
        if normalized_name in seen_names:
            continue
        if entity["entity_type"] == "person" and any(
            normalized_name in existing_name or existing_name in normalized_name for existing_name in seen_names
        ):
            continue
        seen_names.add(normalized_name)
        merged_entities.append(entity)

    return merged_entities[:5] or base_entities


def merge_event(base_event: dict[str, Any], ai_events: Any, entities: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(ai_events, list) or not ai_events or not isinstance(ai_events[0], dict):
        return attach_participants_to_all_entities(base_event, entities)

    ai_event = ai_events[0]
    entity_name_map = {
        normalize_name(entity["canonical_name"]): entity["temp_id"]
        for entity in entities
    }
    participants = []
    seen_participants: set[str] = set()
    if isinstance(ai_event.get("participants"), list):
        for item in ai_event["participants"]:
            if not isinstance(item, dict):
                continue
            entity_temp_id = safe_string_or_none(item.get("entity_temp_id"))
            entity_name = safe_string_or_none(item.get("entity_name"))
            if not entity_temp_id and entity_name:
                entity_temp_id = entity_name_map.get(normalize_name(entity_name))
            if not entity_temp_id and entities:
                entity_temp_id = entities[0]["temp_id"]
            if not entity_temp_id or entity_temp_id in seen_participants:
                continue
            seen_participants.add(entity_temp_id)
            participants.append(
                {
                    "entity_temp_id": entity_temp_id,
                    "role": safe_string_or_none(item.get("role")) or "participant",
                    "relation_type": safe_string(item.get("relation_type"), "participates_in"),
                }
            )
    if not participants:
        participants = [
            {
                "entity_temp_id": entity["temp_id"],
                "role": "participant",
                "relation_type": "participates_in",
            }
            for entity in entities
        ]

    time_block = ai_event.get("time") if isinstance(ai_event.get("time"), dict) else {}
    merged_event = {
        "temp_id": safe_string(ai_event.get("temp_id"), "evt_1"),
        "title": safe_string(ai_event.get("title"), base_event["title"]),
        "event_type": safe_string(ai_event.get("event_type"), base_event["event_type"]),
        "summary": safe_string(ai_event.get("summary"), base_event["summary"]),
        "description": safe_string(ai_event.get("description"), base_event["description"]),
        "time": {
            "time_text": safe_string_or_none(time_block.get("time_text")) or base_event["time"]["time_text"],
            "start_time": safe_iso_or_none(time_block.get("start_time")) or base_event["time"]["start_time"],
            "end_time": safe_iso_or_none(time_block.get("end_time")),
            "time_precision": safe_string(time_block.get("time_precision"), base_event["time"]["time_precision"]),
            "timeline_sort_time": safe_iso_or_none(time_block.get("timeline_sort_time")) or base_event["time"]["timeline_sort_time"],
        },
        "participants": participants,
        "locations": merge_locations(ai_event.get("locations")),
        "confidence": safe_float(ai_event.get("confidence"), base_event["confidence"]),
        "evidence": merge_evidence_list(ai_event.get("evidence"), merged_event_title := safe_string(ai_event.get("title"), base_event["title"])),
        "resolution_hint": {
            "possible_existing_event_ids": [],
            "match_strategy": "title+date",
        },
    }
    if not merged_event["evidence"]:
        merged_event["evidence"] = [{"text": merged_event_title, "start": 0, "end": len(merged_event_title)}]
    return merged_event


def attach_participants_to_all_entities(base_event: dict[str, Any], entities: list[dict[str, Any]]) -> dict[str, Any]:
    event = dict(base_event)
    event["participants"] = [
        {
            "entity_temp_id": entity["temp_id"],
            "role": "participant",
            "relation_type": "participates_in",
        }
        for entity in entities
    ]
    return event


def build_relations(note_id: str, entities: list[dict[str, Any]], event_temp_id: str) -> list[dict[str, Any]]:
    relations = [
        {
            "source_ref": {"type": "note", "id": note_id},
            "relation_type": "source_of",
            "target_ref": {"type": "event", "temp_id": event_temp_id},
            "confidence": 1.0,
            "evidence": [],
        }
    ]
    for entity in entities:
        relations.append(
            {
                "source_ref": {"type": "entity", "temp_id": entity["temp_id"]},
                "relation_type": "participates_in",
                "target_ref": {"type": "event", "temp_id": event_temp_id},
                "confidence": entity["confidence"],
                "evidence": entity["evidence"],
            }
        )
    return relations


def build_timeline_from_event(event: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "event_temp_id": event["temp_id"],
            "title": event["title"],
            "summary": event["summary"],
            "display_time": event["time"]["time_text"] or "待校准",
            "sort_time": event["time"]["timeline_sort_time"],
            "time_precision": event["time"]["time_precision"],
            "importance_score": min(max(safe_float(event.get("confidence"), 0.7), 0.1), 1.0),
        }
    ]


def merge_style_payload(
    base_style_payload: dict[str, Any],
    ai_style_payload: Any,
    entities: list[dict[str, Any]],
    event: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(ai_style_payload, dict):
        return rebuild_style_payload(base_style_payload, entities, event)

    entity_name_map = {
        normalize_name(entity["canonical_name"]): entity["temp_id"]
        for entity in entities
    }
    character_cards = []
    if isinstance(ai_style_payload.get("character_cards"), list):
        for entity in ai_style_payload["character_cards"]:
            if not isinstance(entity, dict):
                continue
            entity_temp_id = safe_string_or_none(entity.get("entity_temp_id"))
            entity_name = safe_string_or_none(entity.get("entity_name")) or safe_string_or_none(entity.get("display_name"))
            if not entity_temp_id and entity_name:
                entity_temp_id = entity_name_map.get(normalize_name(entity_name))
            if not entity_temp_id:
                continue
            character_cards.append(
                {
                    "entity_temp_id": entity_temp_id,
                    "display_name": safe_string(entity.get("display_name"), entity_name or "无名角色"),
                    "epithet": safe_string(entity.get("epithet"), "事件见证者"),
                    "aura": safe_string(entity.get("aura"), "在碎片中留下回响。"),
                }
            )
    if not character_cards:
        character_cards = rebuild_style_payload(base_style_payload, entities, event)["character_cards"]

    event_narrative = []
    if isinstance(ai_style_payload.get("event_narrative"), list):
        for item in ai_style_payload["event_narrative"]:
            if not isinstance(item, dict):
                continue
            event_narrative.append(
                {
                    "event_temp_id": safe_string(item.get("event_temp_id"), event["temp_id"]),
                    "headline": safe_string(item.get("headline"), f"序章：{event['title']}"),
                    "body": safe_string(item.get("body"), f"在被记录的时间缝隙里，{event['summary']}"),
                }
            )
    if not event_narrative:
        event_narrative = rebuild_style_payload(base_style_payload, entities, event)["event_narrative"]

    return {
        "theme": "chunibyo",
        "title": safe_string(ai_style_payload.get("title"), base_style_payload.get("title") or f"命运卷宗：{event['title']}"),
        "character_cards": character_cards,
        "event_narrative": event_narrative,
    }


def rebuild_style_payload(
    base_style_payload: dict[str, Any],
    entities: list[dict[str, Any]],
    event: dict[str, Any],
) -> dict[str, Any]:
    return {
        "theme": "chunibyo",
        "title": safe_string(base_style_payload.get("title"), f"命运卷宗：{event['title']}"),
        "character_cards": [
            {
                "entity_temp_id": entity["temp_id"],
                "display_name": entity["canonical_name"],
                "epithet": "事件见证者",
                "aura": f"{entity['canonical_name']}在碎片中留下回响。",
            }
            for entity in entities
        ],
        "event_narrative": [
            {
                "event_temp_id": event["temp_id"],
                "headline": f"序章：{event['title']}",
                "body": f"在被记录的时间缝隙里，{event['summary']}",
            }
        ],
    }


def merge_similarity_hints(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    hints = []
    for item in value[:5]:
        if not isinstance(item, dict):
            continue
        target_type = safe_string_or_none(item.get("target_type"))
        target_id = safe_string_or_none(item.get("target_id"))
        if not target_type or not target_id:
            continue
        hints.append(
            {
                "target_type": target_type,
                "target_id": target_id,
                "reason": safe_string(item.get("reason"), "内容相近"),
                "confidence": safe_float(item.get("confidence"), 0.6),
            }
        )
    return hints


def merge_locations(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    merged = []
    for item in value[:3]:
        if not isinstance(item, dict):
            continue
        name = safe_string_or_none(item.get("name"))
        if not name:
            continue
        merged.append({"name": name, "entity_temp_id": safe_string_or_none(item.get("entity_temp_id"))})
    return merged


def merge_evidence_list(value: Any, fallback_text: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return [{"text": fallback_text, "start": 0, "end": len(fallback_text)}]

    evidence = []
    for item in value[:5]:
        if not isinstance(item, dict):
            continue
        text = safe_string_or_none(item.get("text"))
        if not text:
            continue
        start = item.get("start")
        end = item.get("end")
        evidence.append(
            {
                "text": text,
                "start": start if isinstance(start, int) else 0,
                "end": end if isinstance(end, int) else len(text),
            }
        )
    return evidence or [{"text": fallback_text, "start": 0, "end": len(fallback_text)}]


def safe_string(value: Any, fallback: str) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else fallback


def safe_string_or_none(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def safe_float(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def safe_iso_or_none(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()

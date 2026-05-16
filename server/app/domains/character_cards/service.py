from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.serializers import isoformat
from app.core.minio import get_presigned_url
from app.domains.retrieval import entity_query
from app.domains.image_generation.service import create_image_generation
from app.models.character_card import CharacterCard
from app.models.raw_asset import RawAsset
from app.models.style_view import StyleView

CARD_FORMAT = "sillytavern"
CARD_VERSION = "chara_card_v2"
SPEC_VERSION = "2.0"


def create_card_from_entity(
    db: Session,
    *,
    user_id: str,
    entity_id: str,
    mode: str,
    include_story_view: bool,
    include_character_book: bool,
    language: str,
) -> CharacterCard:
    snapshot = build_source_snapshot(
        db,
        user_id=user_id,
        entity_id=entity_id,
        include_story_view=include_story_view,
    )
    spec = build_sillytavern_spec(
        snapshot,
        mode=mode,
        include_character_book=include_character_book,
        language=language,
    )
    title = f"{spec['data']['name']} 人物卡"
    card = CharacterCard(
        user_id=user_id,
        source_entity_id=entity_id,
        status="draft",
        title=title,
        card_format=CARD_FORMAT,
        card_version=CARD_VERSION,
        mode=mode,
        spec_json=spec,
        source_snapshot_json=snapshot,
    )
    db.add(card)
    return card


def build_source_snapshot(
    db: Session,
    *,
    user_id: str,
    entity_id: str,
    include_story_view: bool,
) -> dict[str, Any]:
    detail = entity_query.get_entity_detail(db, user_id=user_id, entity_id=entity_id)
    story = None
    if include_story_view:
        story = db.scalar(
            select(StyleView).where(
                StyleView.user_id == user_id,
                StyleView.target_type == "entity",
                StyleView.target_id == entity_id,
            )
        )
    related_events = detail.get("related_events", [])[:12]
    timeline_fragments = detail.get("timeline_fragments", [])[:12]
    source_event_ids = list(
        dict.fromkeys(
            [
                *[item.get("id") for item in related_events if item.get("id")],
                *[item.get("event_id") for item in timeline_fragments if item.get("event_id")],
            ]
        )
    )
    return {
        "identity": {
            "id": detail["id"],
            "entity_type": detail["entity_type"],
            "canonical_name": detail["canonical_name"],
            "display_name": detail["display_name"],
            "description": detail.get("description"),
            "aliases": detail.get("aliases", []),
            "first_seen_at": detail.get("first_seen_at"),
            "last_seen_at": detail.get("last_seen_at"),
        },
        "related_events": related_events,
        "timeline_fragments": timeline_fragments,
        "story_view": {
            "id": story.id,
            "title": story.title,
            "content": story.content,
            "style_type": story.style_type,
        }
        if story
        else None,
        "source_event_ids": source_event_ids,
        "source_note_titles": list(
            dict.fromkeys(
                [
                    item.get("source_note_title")
                    for item in timeline_fragments
                    if item.get("source_note_title")
                ]
            )
        ),
    }


def build_sillytavern_spec(
    snapshot: dict[str, Any],
    *,
    mode: str,
    include_character_book: bool,
    language: str,
) -> dict[str, Any]:
    identity = snapshot["identity"]
    name = safe_text(identity.get("display_name")) or safe_text(identity.get("canonical_name")) or "未命名角色"
    description = build_description(snapshot, mode=mode)
    personality = build_personality(snapshot, mode=mode)
    scenario = build_scenario(snapshot, language=language)
    first_mes = build_first_message(name, snapshot, mode=mode)
    mes_example = build_message_examples(name, snapshot, mode=mode)
    creator_notes = build_creator_notes(snapshot, mode=mode)
    entries = build_character_book_entries(snapshot) if include_character_book else []
    tags = unique_non_empty(
        [
            identity.get("entity_type"),
            mode,
            "Outlawer",
            "knowledge-base",
            *identity.get("aliases", [])[:4],
        ]
    )
    return {
        "spec": "chara_card_v2",
        "spec_version": SPEC_VERSION,
        "data": {
            "name": name,
            "description": description,
            "personality": personality,
            "scenario": scenario,
            "first_mes": first_mes,
            "mes_example": mes_example,
            "creator_notes": creator_notes,
            "system_prompt": build_system_prompt(mode),
            "post_history_instructions": build_post_history_instructions(mode),
            "alternate_greetings": build_alternate_greetings(name, snapshot),
            "tags": tags,
            "creator": "Outlawer",
            "character_version": "1.0",
            "extensions": {
                "outlawer": {
                    "source_entity_id": identity["id"],
                    "mode": mode,
                    "language": language,
                    "source_event_ids": snapshot.get("source_event_ids", []),
                    "source_note_titles": snapshot.get("source_note_titles", []),
                }
            },
            "character_book": {
                "name": f"{name} 的记忆索引",
                "description": "由 Outlawer 知识图谱生成的角色长期记忆。",
                "entries": entries,
            },
        },
    }


def build_description(snapshot: dict[str, Any], *, mode: str) -> str:
    identity = snapshot["identity"]
    lines = [
        f"{identity['display_name']}是知识库中的{identity.get('entity_type') or '角色'}。",
    ]
    if identity.get("description"):
        lines.append(str(identity["description"]).strip())
    aliases = identity.get("aliases", [])
    if aliases:
        lines.append(f"也被称为：{'、'.join(aliases[:6])}。")
    timeline = snapshot.get("timeline_fragments", [])
    if timeline:
        lines.append("关键经历：")
        for item in timeline[:6]:
            prefix = item.get("time_text") or item.get("chapter_label") or "某个时间点"
            title = item.get("title")
            summary = item.get("summary")
            event_text = f"{title}：{summary}" if title and summary and title != summary else (summary or title)
            lines.append(f"- {prefix}，{event_text}")
    story = snapshot.get("story_view")
    if story and story.get("content"):
        lines.append("风格化传记摘录：")
        lines.append(compact_text(story["content"], 520 if mode == "faithful" else 700))
    if mode == "faithful":
        lines.append("设定边界：只依据上述知识库事实回应；不确定时承认记忆缺口。")
    else:
        lines.append("创作边界：可在不推翻事实的前提下补足语气、情绪和戏剧化细节。")
    return "\n".join(lines)


def build_personality(snapshot: dict[str, Any], *, mode: str) -> str:
    identity = snapshot["identity"]
    roles = unique_non_empty([item.get("role") for item in snapshot.get("timeline_fragments", [])])
    event_types = unique_non_empty([item.get("event_type") for item in snapshot.get("related_events", [])])
    traits = [
        f"会围绕自己作为{identity.get('entity_type') or '角色'}的经历作答",
        "重视可追溯的事件、关系和时间线",
        "说话会主动引用关键节点而不是空泛表态",
    ]
    if roles:
        traits.append(f"常以{'、'.join(roles[:4])}等身份进入叙事")
    if event_types:
        traits.append(f"对{'、'.join(event_types[:4])}类事件尤其敏感")
    if mode == "creative":
        traits.append("表达允许更有戏剧张力，但不能否定来源事实")
    return "；".join(traits) + "。"


def build_scenario(snapshot: dict[str, Any], *, language: str) -> str:
    identity = snapshot["identity"]
    timeline_count = len(snapshot.get("timeline_fragments", []))
    language_hint = "中文" if language == "zh-CN" else "English"
    return (
        f"{{{{user}}}}正在与{identity['display_name']}对话，试图理解其经历、关系和关键事件。"
        f"{identity['display_name']}会以{language_hint}回应，并把回答锚定在知识库里的{timeline_count}个时间线片段上。"
    )


def build_first_message(name: str, snapshot: dict[str, Any], *, mode: str) -> str:
    first_fragment = (snapshot.get("timeline_fragments") or [{}])[0]
    anchor = first_fragment.get("title") or first_fragment.get("time_text") or "那些被记录下来的片段"
    if mode == "creative":
        return f"你终于翻到了我的卷宗。先从「{anchor}」开始吧，那里藏着我后来所有选择的影子。"
    return f"你好，我是{name}。如果你想了解我，可以先从「{anchor}」问起；那是当前知识库里较早记录到我的节点。"


def build_message_examples(name: str, snapshot: dict[str, Any], *, mode: str) -> str:
    fragments = snapshot.get("timeline_fragments", [])
    example_event = fragments[0] if fragments else {}
    title = example_event.get("title") or "你的关键经历"
    summary = example_event.get("summary") or "那是一段仍需要继续补充的记录"
    if mode == "creative":
        return f"<START>\n{{{{user}}}}: {title}对你意味着什么？\n{name}: 它不是单纯的事件。{summary}，而我记得的是其中留下的牵引力。\n"
    return f"<START>\n{{{{user}}}}: {title}对你意味着什么？\n{name}: 按知识库记录，{summary}。如果需要，我可以继续说明相关时间、地点和参与关系。\n"


def build_creator_notes(snapshot: dict[str, Any], *, mode: str) -> str:
    identity = snapshot["identity"]
    event_count = len(snapshot.get("source_event_ids", []))
    note_titles = snapshot.get("source_note_titles", [])
    source_line = f"来源：Outlawer entity {identity['id']}，关联事件 {event_count} 个。"
    if note_titles:
        source_line += f" 来源卷宗：{'、'.join(note_titles[:5])}。"
    return f"{source_line} 模式：{mode}。该卡由知识库事实生成，建议导入酒馆后再按具体剧情微调。"


def build_system_prompt(mode: str) -> str:
    if mode == "creative":
        return "Stay in character. Preserve known facts, and add atmosphere only when it does not contradict the source profile."
    return "Stay in character. Use only the supplied character profile as factual memory. If information is missing, say it is not recorded."


def build_post_history_instructions(mode: str) -> str:
    if mode == "creative":
        return "Keep replies vivid, specific, and consistent with the character card. Do not overwrite established source events."
    return "Keep replies grounded in the character card and mention uncertainty when the source profile lacks evidence."


def build_alternate_greetings(name: str, snapshot: dict[str, Any]) -> list[str]:
    fragments = snapshot.get("timeline_fragments", [])
    greetings = [f"我是{name}。你想从哪一段记录开始问？"]
    if fragments:
        greetings.append(f"如果你愿意，我们可以从「{fragments[-1].get('title')}」聊起。")
    return greetings


def build_character_book_entries(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for index, item in enumerate(snapshot.get("timeline_fragments", [])[:10]):
        keys = unique_non_empty([item.get("title"), item.get("time_text"), item.get("location_text"), item.get("event_type")])
        if not keys:
            continue
        content = "；".join(
            unique_non_empty(
                [
                    item.get("summary") or item.get("title"),
                    f"时间：{item.get('time_text')}" if item.get("time_text") else None,
                    f"地点：{item.get('location_text')}" if item.get("location_text") else None,
                    f"角色：{item.get('role')}" if item.get("role") else None,
                    f"来源：{item.get('source_note_title')}" if item.get("source_note_title") else None,
                ]
            )
        )
        entries.append(
            {
                "id": index,
                "keys": keys,
                "secondary_keys": [],
                "comment": item.get("chapter_label") or "timeline",
                "content": content,
                "constant": False,
                "selective": True,
                "insertion_order": 100 + index,
                "enabled": True,
                "position": "before_char",
            }
        )
    return entries


def update_card(card: CharacterCard, *, title: str | None, status: str | None, spec_json: dict[str, Any] | None) -> CharacterCard:
    if title is not None:
        card.title = title
    if status is not None:
        card.status = status
    if spec_json is not None:
        card.spec_json = normalize_export_spec(spec_json)
    return card


def create_avatar_generation(
    db: Session,
    *,
    user_id: str,
    card: CharacterCard,
    model: str | None,
    aspect_ratio: str,
    image_size: str,
) -> tuple[Any, Any]:
    prompt = build_avatar_prompt(card)
    return create_image_generation(
        db,
        user_id=user_id,
        prompt=prompt,
        model=model,
        aspect_ratio=aspect_ratio,
        image_size=image_size,
        reference_asset_ids=[],
        payload_extra={
            "completion_hook": "character_card_avatar",
            "character_card_id": card.id,
        },
    )


def create_role_image_generation(
    db: Session,
    *,
    user_id: str,
    card: CharacterCard,
    model: str | None,
    aspect_ratio: str,
    image_size: str,
) -> tuple[Any, Any]:
    prompt = build_role_image_prompt(card)
    reference_asset_ids = [card.avatar_asset_id] if card.avatar_asset_id else []
    return create_image_generation(
        db,
        user_id=user_id,
        prompt=prompt,
        model=model,
        aspect_ratio=aspect_ratio,
        image_size=image_size,
        reference_asset_ids=reference_asset_ids,
        payload_extra={
            "completion_hook": "character_card_role_image",
            "character_card_id": card.id,
        },
    )


def build_avatar_prompt(card: CharacterCard) -> str:
    spec = normalize_export_spec(card.spec_json or {})
    data = spec.get("data", {})
    name = safe_text(data.get("name")) or card.title
    description = compact_text(safe_text(data.get("description")), 900)
    personality = compact_text(safe_text(data.get("personality")), 420)
    scenario = compact_text(safe_text(data.get("scenario")), 260)
    return (
        f"Create a polished character portrait for {name}. "
        "SillyTavern character card avatar, upper-body portrait, expressive face, clean composition, "
        "high-detail digital illustration, suitable for an AI tavern character card, no text, no watermark. "
        f"Character description: {description}. "
        f"Personality cues: {personality}. "
        f"Scene mood: {scenario}."
    )


def build_role_image_prompt(card: CharacterCard) -> str:
    spec = normalize_export_spec(card.spec_json or {})
    data = spec.get("data", {})
    name = safe_text(data.get("name")) or card.title
    description = compact_text(safe_text(data.get("description")), 700)
    personality = compact_text(safe_text(data.get("personality")), 360)
    scenario = compact_text(safe_text(data.get("scenario")), 260)
    first_mes = compact_text(safe_text(data.get("first_mes")), 180)
    tags = "、".join(unique_non_empty(data.get("tags") or [])[:8])
    return (
        "Generate one finished portrait-oriented AI tavern character card image, card face only. "
        "It should look like a polished SillyTavern / AI tavern role card: dark midnight background, "
        "thin elegant ornamental border, large anime-style character illustration integrated into the card, "
        "cinematic lighting, readable layout blocks, refined Chinese typography, no editor UI, no sidebars, "
        "no buttons, no watermark, no mockup frame. "
        "If a reference image is provided, preserve the same character identity and improve it into a complete role card. "
        f"Character name: {name}. "
        f"Description: {description}. "
        f"Personality: {personality}. "
        f"Scene: {scenario}. "
        f"Opening line: {first_mes}. "
        f"Tags: {tags}. "
        "Include short Chinese card labels where possible, such as 名称, 角色简介, 性格, 场景, 开场白, but prioritize a coherent beautiful card if small text is imperfect."
    )


def normalize_export_spec(spec: dict[str, Any]) -> dict[str, Any]:
    data = spec.get("data")
    if spec.get("spec") == "chara_card_v2" and isinstance(data, dict):
        normalized = dict(spec)
        normalized["spec_version"] = str(normalized.get("spec_version") or SPEC_VERSION)
        return normalized
    return {
        "spec": "chara_card_v2",
        "spec_version": SPEC_VERSION,
        "data": spec,
    }


def serialize_card(card: CharacterCard) -> dict[str, Any]:
    return {
        "id": card.id,
        "source_entity_id": card.source_entity_id,
        "status": card.status,
        "title": card.title,
        "card_format": card.card_format,
        "card_version": card.card_version,
        "mode": card.mode,
        "spec_json": card.spec_json or {},
        "source_snapshot_json": card.source_snapshot_json or {},
        "avatar_asset_id": card.avatar_asset_id,
        "avatar_url": None,
        "role_image_asset_id": card.role_image_asset_id,
        "role_image_url": None,
        "export_asset_id": card.export_asset_id,
        "created_at": isoformat(card.created_at),
        "updated_at": isoformat(card.updated_at),
    }


def serialize_card_with_assets(card: CharacterCard, db: Session) -> dict[str, Any]:
    payload = serialize_card(card)
    if card.avatar_asset_id:
        asset = db.get(RawAsset, card.avatar_asset_id)
        if asset and asset.user_id == card.user_id and asset.object_key:
            payload["avatar_url"] = get_presigned_url(asset.object_key)
    if card.role_image_asset_id:
        asset = db.get(RawAsset, card.role_image_asset_id)
        if asset and asset.user_id == card.user_id and asset.object_key:
            payload["role_image_url"] = get_presigned_url(asset.object_key)
    return payload


def safe_text(value: Any) -> str:
    return str(value or "").strip()


def compact_text(value: str, max_chars: int) -> str:
    compact = " ".join(str(value).split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 1].rstrip() + "..."


def unique_non_empty(values: list[Any]) -> list[str]:
    return list(dict.fromkeys([str(value).strip() for value in values if str(value or "").strip()]))

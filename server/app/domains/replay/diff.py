from datetime import datetime
from typing import Any, Callable

from app.utils.text import normalize_name


def compare_extraction_payloads(base_payload: dict[str, Any], candidate_payload: dict[str, Any]) -> dict[str, Any]:
    summary = diff_summary(base_payload.get("summary"), candidate_payload.get("summary"))
    entities = diff_collection(
        normalize_entities(base_payload.get("entities")),
        normalize_entities(candidate_payload.get("entities")),
        key_fn=lambda item: item["key"],
    )
    events = diff_collection(
        normalize_events(base_payload.get("events")),
        normalize_events(candidate_payload.get("events")),
        key_fn=lambda item: item["key"],
    )
    relations = diff_collection(
        normalize_relations(base_payload.get("relations")),
        normalize_relations(candidate_payload.get("relations")),
        key_fn=lambda item: item["key"],
    )
    similarity_hints = diff_collection(
        normalize_similarity_hints(base_payload.get("similarity_hints")),
        normalize_similarity_hints(candidate_payload.get("similarity_hints")),
        key_fn=lambda item: item["key"],
    )
    style = diff_style(base_payload.get("style_payload"), candidate_payload.get("style_payload"))
    changed = any(
        section["changed"]
        for section in [summary, entities, events, relations, similarity_hints, style]
    )
    return {
        "changed": changed,
        "summary": summary,
        "entities": entities,
        "events": events,
        "relations": relations,
        "similarity_hints": similarity_hints,
        "style_payload": style,
    }


def summarize_run_payload(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    return {
        "title": safe_string(summary.get("title")) if isinstance(summary, dict) else "",
        "category": safe_string(summary.get("category")) if isinstance(summary, dict) else "",
        "entity_count": len(payload.get("entities")) if isinstance(payload.get("entities"), list) else 0,
        "event_count": len(payload.get("events")) if isinstance(payload.get("events"), list) else 0,
        "relation_count": len(payload.get("relations")) if isinstance(payload.get("relations"), list) else 0,
        "similarity_hint_count": len(payload.get("similarity_hints")) if isinstance(payload.get("similarity_hints"), list) else 0,
    }


def diff_summary(base_value: object, candidate_value: object) -> dict[str, Any]:
    base = base_value if isinstance(base_value, dict) else {}
    candidate = candidate_value if isinstance(candidate_value, dict) else {}
    fields = []
    for field in ["title", "short_summary", "canonical_text", "category", "tags"]:
        base_field = comparable_value(base.get(field))
        candidate_field = comparable_value(candidate.get(field))
        fields.append(
            {
                "field": field,
                "base": base_field,
                "candidate": candidate_field,
                "changed": base_field != candidate_field,
            }
        )
    return {
        "changed": any(item["changed"] for item in fields),
        "fields": fields,
    }


def diff_style(base_value: object, candidate_value: object) -> dict[str, Any]:
    base = normalize_style_payload(base_value)
    candidate = normalize_style_payload(candidate_value)
    fields = []
    for field in ["title", "character_cards", "event_narrative"]:
        base_field = comparable_value(base.get(field))
        candidate_field = comparable_value(candidate.get(field))
        fields.append(
            {
                "field": field,
                "base": base_field,
                "candidate": candidate_field,
                "changed": base_field != candidate_field,
            }
        )
    return {
        "changed": any(item["changed"] for item in fields),
        "fields": fields,
    }


def diff_collection(
    base_items: list[dict[str, Any]],
    candidate_items: list[dict[str, Any]],
    *,
    key_fn: Callable[[dict[str, Any]], str],
) -> dict[str, Any]:
    base_by_key = {key_fn(item): item for item in base_items}
    candidate_by_key = {key_fn(item): item for item in candidate_items}
    added_keys = sorted(candidate_by_key.keys() - base_by_key.keys())
    removed_keys = sorted(base_by_key.keys() - candidate_by_key.keys())
    shared_keys = sorted(base_by_key.keys() & candidate_by_key.keys())

    changed = []
    unchanged_count = 0
    for key in shared_keys:
        if base_by_key[key] == candidate_by_key[key]:
            unchanged_count += 1
            continue
        changed.append({"key": key, "base": base_by_key[key], "candidate": candidate_by_key[key]})

    return {
        "changed": bool(added_keys or removed_keys or changed),
        "added": [candidate_by_key[key] for key in added_keys],
        "removed": [base_by_key[key] for key in removed_keys],
        "changed_items": changed,
        "unchanged_count": unchanged_count,
        "base_count": len(base_items),
        "candidate_count": len(candidate_items),
    }


def normalize_entities(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    items = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = safe_string(item.get("canonical_name") or item.get("name"))
        entity_type = safe_string(item.get("entity_type"))
        if not name:
            continue
        items.append(
            {
                "key": f"{entity_type}:{normalize_name(name)}",
                "name": name,
                "entity_type": entity_type,
                "aliases": normalize_string_list(item.get("aliases")),
                "description": safe_string(item.get("description")),
                "confidence": comparable_value(item.get("confidence")),
            }
        )
    return sorted(items, key=lambda item: item["key"])


def normalize_events(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    items = []
    for item in value:
        if not isinstance(item, dict):
            continue
        title = safe_string(item.get("title"))
        time_value = item.get("time") if isinstance(item.get("time"), dict) else {}
        sort_time = safe_string(time_value.get("timeline_sort_time")) if isinstance(time_value, dict) else ""
        if not title:
            continue
        items.append(
            {
                "key": f"{normalize_name(title)}:{sort_time}",
                "title": title,
                "event_type": safe_string(item.get("event_type")),
                "summary": safe_string(item.get("summary")),
                "time_text": safe_string(time_value.get("time_text")) if isinstance(time_value, dict) else "",
                "timeline_sort_time": sort_time,
                "participant_count": len(item.get("participants")) if isinstance(item.get("participants"), list) else 0,
                "location_names": normalize_location_names(item.get("locations")),
                "confidence": comparable_value(item.get("confidence")),
            }
        )
    return sorted(items, key=lambda item: item["key"])


def normalize_relations(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    items = []
    for item in value:
        if not isinstance(item, dict):
            continue
        source_ref = item.get("source_ref") if isinstance(item.get("source_ref"), dict) else {}
        target_ref = item.get("target_ref") if isinstance(item.get("target_ref"), dict) else {}
        relation_type = safe_string(item.get("relation_type"))
        source = normalize_reference(source_ref)
        target = normalize_reference(target_ref)
        if not relation_type or not source or not target:
            continue
        items.append(
            {
                "key": f"{source}->{relation_type}->{target}",
                "source": source,
                "relation_type": relation_type,
                "target": target,
                "confidence": comparable_value(item.get("confidence")),
            }
        )
    return sorted(items, key=lambda item: item["key"])


def normalize_similarity_hints(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    items = []
    for item in value:
        if not isinstance(item, dict):
            continue
        target_type = safe_string(item.get("target_type"))
        target_id = safe_string(item.get("target_id"))
        reason = safe_string(item.get("reason"))
        if not target_type or not target_id:
            continue
        items.append(
            {
                "key": f"{target_type}:{target_id}:{normalize_name(reason)}",
                "target_type": target_type,
                "target_id": target_id,
                "reason": reason,
                "confidence": comparable_value(item.get("confidence")),
            }
        )
    return sorted(items, key=lambda item: item["key"])


def normalize_style_payload(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        "title": safe_string(value.get("title")),
        "character_cards": [
            {
                "entity_name": safe_string(item.get("entity_name") or item.get("display_name")),
                "epithet": safe_string(item.get("epithet")),
            }
            for item in value.get("character_cards", [])
            if isinstance(item, dict)
        ]
        if isinstance(value.get("character_cards"), list)
        else [],
        "event_narrative": [
            {
                "headline": safe_string(item.get("headline")),
                "body": safe_string(item.get("body")),
            }
            for item in value.get("event_narrative", [])
            if isinstance(item, dict)
        ]
        if isinstance(value.get("event_narrative"), list)
        else [],
    }


def normalize_reference(value: object) -> str:
    if not isinstance(value, dict):
        return ""
    reference_type = safe_string(value.get("type"))
    reference_id = safe_string(value.get("id") or value.get("temp_id"))
    if not reference_type or not reference_id:
        return ""
    return f"{reference_type}:{reference_id}"


def normalize_location_names(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    names = []
    for item in value:
        if isinstance(item, dict):
            name = safe_string(item.get("name"))
        else:
            name = safe_string(item)
        if name and name not in names:
            names.append(name)
    return names


def normalize_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    items = []
    for item in value:
        text = safe_string(item)
        if text and text not in items:
            items.append(text)
    return items


def comparable_value(value: object) -> Any:
    if isinstance(value, str):
        return truncate_text(value.strip())
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [comparable_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): comparable_value(item) for key, item in sorted(value.items())}
    return str(value)


def safe_string(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def truncate_text(value: str, limit: int = 500) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit]}..."


def serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None

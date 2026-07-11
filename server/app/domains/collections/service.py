from __future__ import annotations

import json
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.serializers import isoformat
from app.core.pagination import PageParams, paginate_query
from app.models.collection import KnowledgeCollection, KnowledgeCollectionItem
from app.models.entity import Entity
from app.models.event import Event
from app.models.graph_viewpoint import GraphViewpoint
from app.models.manual_knowledge import ManualKnowledgeEvidence
from app.models.note import Note
from app.models.raw_asset import RawAsset
from app.models.review import ReviewAction


ITEM_MODELS = {
    "note": Note,
    "raw_asset": RawAsset,
    "entity": Entity,
    "event": Event,
    "graph_viewpoint": GraphViewpoint,
}


def list_collections(
    db: Session, *, user_id: str, params: PageParams
) -> tuple[list[dict[str, Any]], int]:
    query = select(KnowledgeCollection).where(KnowledgeCollection.user_id == user_id).order_by(KnowledgeCollection.updated_at.desc())
    rows, total = paginate_query(db, query, params)
    return [serialize_collection(row, stats=build_collection_stats(db, user_id=user_id, collection_id=row.id)) for row in rows], total


def create_collection(db: Session, *, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    row = KnowledgeCollection(
        user_id=user_id,
        title=_required(payload.get("title"), "Title is required"),
        description=_optional(payload.get("description")),
        collection_type=_optional(payload.get("collection_type")) or "topic",
        status="active",
        story_style="documentary",
    )
    db.add(row)
    db.flush()
    _audit(db, user_id=user_id, target_type="collection", target_id=row.id, action_type="create_collection", payload={"title": row.title})
    db.commit()
    db.refresh(row)
    return serialize_collection(row, stats=_empty_collection_stats())


def get_collection_detail(db: Session, *, user_id: str, collection_id: str) -> dict[str, Any]:
    row = get_owned_collection(db, user_id=user_id, collection_id=collection_id)
    items = list(
        db.scalars(
            select(KnowledgeCollectionItem)
            .where(KnowledgeCollectionItem.collection_id == row.id)
            .order_by(KnowledgeCollectionItem.sort_order, KnowledgeCollectionItem.created_at)
        ).all()
    )
    return {
        **serialize_collection(row, stats=build_collection_stats(db, user_id=user_id, collection_id=row.id, items=items)),
        "items": [serialize_collection_item(db, user_id=user_id, row=item) for item in items],
    }


def update_collection(db: Session, *, user_id: str, collection_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    row = get_owned_collection(db, user_id=user_id, collection_id=collection_id)
    for field in ("title", "description", "collection_type", "status"):
        if field not in payload or payload[field] is None:
            continue
        setattr(row, field, _required(payload[field], f"{field} is required") if field in {"title", "collection_type", "status"} else _optional(payload[field]))
    db.add(row)
    _audit(db, user_id=user_id, target_type="collection", target_id=row.id, action_type="update_collection", payload=payload)
    db.commit()
    return get_collection_detail(db, user_id=user_id, collection_id=row.id)


def delete_collection(db: Session, *, user_id: str, collection_id: str) -> dict[str, str]:
    row = get_owned_collection(db, user_id=user_id, collection_id=collection_id)
    for item in db.scalars(select(KnowledgeCollectionItem).where(KnowledgeCollectionItem.collection_id == row.id)).all():
        db.delete(item)
    db.delete(row)
    db.commit()
    return {"id": collection_id, "status": "deleted"}


def add_collection_item(db: Session, *, user_id: str, collection_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    collection = get_owned_collection(db, user_id=user_id, collection_id=collection_id)
    item_type = _required(payload.get("item_type"), "Item type is required").lower()
    item_id = _required(payload.get("item_id"), "Item id is required")
    _resolve_owned_item(db, user_id=user_id, item_type=item_type, item_id=item_id)
    existing = db.scalar(
        select(KnowledgeCollectionItem).where(
            KnowledgeCollectionItem.collection_id == collection.id,
            KnowledgeCollectionItem.item_type == item_type,
            KnowledgeCollectionItem.item_id == item_id,
        )
    )
    if existing:
        raise ValueError("Item is already in this collection")
    order = payload.get("sort_order")
    if order is None:
        maximum = db.scalar(select(func.max(KnowledgeCollectionItem.sort_order)).where(KnowledgeCollectionItem.collection_id == collection.id))
        order = int(maximum if maximum is not None else -1) + 1
    row = KnowledgeCollectionItem(
        collection_id=collection.id,
        item_type=item_type,
        item_id=item_id,
        sort_order=int(order),
        curator_note=_optional(payload.get("curator_note")),
    )
    db.add(row)
    db.flush()
    _audit(
        db,
        user_id=user_id,
        target_type="collection",
        target_id=collection.id,
        action_type="add_collection_item",
        payload={"collection_item_id": row.id, "item_type": item_type, "item_id": item_id},
    )
    db.commit()
    db.refresh(row)
    return serialize_collection_item(db, user_id=user_id, row=row)


def update_collection_item(
    db: Session, *, user_id: str, collection_id: str, collection_item_id: str, payload: dict[str, Any]
) -> dict[str, Any]:
    get_owned_collection(db, user_id=user_id, collection_id=collection_id)
    row = db.get(KnowledgeCollectionItem, collection_item_id)
    if row is None or row.collection_id != collection_id:
        raise ValueError("Collection item not found")
    if payload.get("sort_order") is not None:
        row.sort_order = int(payload["sort_order"])
    if "curator_note" in payload:
        row.curator_note = _optional(payload.get("curator_note"))
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize_collection_item(db, user_id=user_id, row=row)


def remove_collection_item(
    db: Session, *, user_id: str, collection_id: str, collection_item_id: str
) -> dict[str, str]:
    get_owned_collection(db, user_id=user_id, collection_id=collection_id)
    row = db.get(KnowledgeCollectionItem, collection_item_id)
    if row is None or row.collection_id != collection_id:
        raise ValueError("Collection item not found")
    db.delete(row)
    db.commit()
    return {"id": collection_item_id, "status": "deleted"}


def reorder_collection_items(
    db: Session, *, user_id: str, collection_id: str, item_ids: list[str]
) -> dict[str, Any]:
    get_owned_collection(db, user_id=user_id, collection_id=collection_id)
    rows = list(db.scalars(select(KnowledgeCollectionItem).where(KnowledgeCollectionItem.collection_id == collection_id)).all())
    current_ids = {row.id for row in rows}
    if len(item_ids) != len(set(item_ids)) or set(item_ids) != current_ids:
        raise ValueError("Item order must include every collection item exactly once")
    by_id = {row.id: row for row in rows}
    for index, item_id in enumerate(item_ids):
        by_id[item_id].sort_order = index
        db.add(by_id[item_id])
    _audit(db, user_id=user_id, target_type="collection", target_id=collection_id, action_type="reorder_collection_items", payload={"item_ids": item_ids})
    db.commit()
    return {"item_ids": item_ids, "status": "updated"}


def bulk_remove_collection_items(
    db: Session, *, user_id: str, collection_id: str, item_ids: list[str]
) -> dict[str, Any]:
    get_owned_collection(db, user_id=user_id, collection_id=collection_id)
    requested = set(item_ids)
    if not requested:
        raise ValueError("At least one collection item is required")
    rows = list(
        db.scalars(
            select(KnowledgeCollectionItem).where(
                KnowledgeCollectionItem.collection_id == collection_id,
                KnowledgeCollectionItem.id.in_(requested),
            )
        ).all()
    )
    if {row.id for row in rows} != requested:
        raise ValueError("One or more collection items were not found")
    for row in rows:
        db.delete(row)
    removed_ids = [row.id for row in rows]
    _audit(db, user_id=user_id, target_type="collection", target_id=collection_id, action_type="bulk_remove_collection_items", payload={"item_ids": removed_ids})
    db.commit()
    return {"removed_ids": removed_ids, "status": "deleted"}


def update_collection_story(db: Session, *, user_id: str, collection_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    row = get_owned_collection(db, user_id=user_id, collection_id=collection_id)
    row.story_title = _optional(payload.get("title"))
    row.story_summary = _optional(payload.get("summary"))
    row.story_body = _optional(payload.get("body"))
    row.story_style = _optional(payload.get("style")) or "documentary"
    db.add(row)
    _audit(db, user_id=user_id, target_type="collection", target_id=row.id, action_type="update_collection_story", payload={"style": row.story_style})
    db.commit()
    return serialize_collection(row, stats=build_collection_stats(db, user_id=user_id, collection_id=row.id))["story"]


def compile_collection_story(db: Session, *, user_id: str, collection_id: str) -> dict[str, Any]:
    detail = get_collection_detail(db, user_id=user_id, collection_id=collection_id)
    row = get_owned_collection(db, user_id=user_id, collection_id=collection_id)
    timeline = build_collection_timeline(db, user_id=user_id, collection_id=collection_id)["items"]
    sections: list[str] = []
    if timeline:
        sections.append("## 时间线\n\n" + "\n".join(f"- **{item['display_time'] or '时间待考'}｜{item['title']}**：{item['summary'] or item['curator_note'] or '暂无摘要'}" for item in timeline))
    non_events = [item for item in detail["items"] if item["item_type"] != "event"]
    if non_events:
        sections.append("## 关键材料与人物\n\n" + "\n".join(f"- **{item['label']}**（{item['item_type']}）：{item['curator_note'] or item['subtitle'] or '已收录'}" for item in non_events))
    row.story_title = row.story_title or row.title
    row.story_summary = row.story_summary or row.description or f"由 {len(detail['items'])} 条专题材料整理而成。"
    row.story_body = "\n\n".join(sections) or "当前专题尚未收录可编排的材料。"
    db.add(row)
    _audit(db, user_id=user_id, target_type="collection", target_id=row.id, action_type="compile_collection_story", payload={"item_count": len(detail["items"]), "timeline_count": len(timeline)})
    db.commit()
    return serialize_collection(row, stats=detail["stats"])["story"]


def list_collection_candidates(
    db: Session,
    *,
    user_id: str,
    collection_id: str,
    query: str | None,
    item_type: str | None,
    params: PageParams,
) -> tuple[list[dict[str, Any]], int]:
    get_owned_collection(db, user_id=user_id, collection_id=collection_id)
    allowed_types = [item_type] if item_type else list(ITEM_MODELS)
    if any(value not in ITEM_MODELS for value in allowed_types):
        raise ValueError("Unsupported collection item type")
    existing = {
        (row.item_type, row.item_id)
        for row in db.scalars(select(KnowledgeCollectionItem).where(KnowledgeCollectionItem.collection_id == collection_id)).all()
    }
    cleaned_query = (query or "").strip()
    candidates: list[dict[str, Any]] = []
    for candidate_type in allowed_types:
        candidates.extend(_query_candidates_for_type(db, user_id=user_id, item_type=candidate_type, query=cleaned_query))
    candidates = [item for item in candidates if (item["item_type"], item["item_id"]) not in existing]
    candidates.sort(key=lambda item: (item["item_type"], item["label"].lower()))
    total = len(candidates)
    start = (params.page - 1) * params.page_size
    return candidates[start : start + params.page_size], total


def build_collection_timeline(db: Session, *, user_id: str, collection_id: str) -> dict[str, Any]:
    get_owned_collection(db, user_id=user_id, collection_id=collection_id)
    links = list(
        db.scalars(
            select(KnowledgeCollectionItem)
            .where(KnowledgeCollectionItem.collection_id == collection_id, KnowledgeCollectionItem.item_type == "event")
            .order_by(KnowledgeCollectionItem.sort_order, KnowledgeCollectionItem.created_at)
        ).all()
    )
    events = {
        row.id: row
        for row in db.scalars(select(Event).where(Event.user_id == user_id, Event.id.in_([link.item_id for link in links]))).all()
    } if links else {}
    ordered = sorted(
        ((link, events[link.item_id]) for link in links if link.item_id in events),
        key=lambda pair: (pair[1].timeline_sort_time is None, pair[1].timeline_sort_time, pair[0].sort_order),
    )
    return {
        "collection_id": collection_id,
        "items": [
            {
                "event_id": event.id,
                "title": event.title,
                "summary": event.summary,
                "display_time": event.time_text,
                "sort_time": isoformat(event.timeline_sort_time),
                "location_text": event.location_text,
                "curator_note": link.curator_note,
                "href": f"/events/{event.id}",
            }
            for link, event in ordered
        ],
    }


def export_collection(db: Session, *, user_id: str, collection_id: str, export_format: str) -> dict[str, str]:
    detail = get_collection_detail(db, user_id=user_id, collection_id=collection_id)
    timeline = build_collection_timeline(db, user_id=user_id, collection_id=collection_id)
    safe_name = "-".join(detail["title"].split()) or "collection"
    if export_format == "json":
        content = json.dumps({"collection": detail, "timeline": timeline["items"]}, ensure_ascii=False, indent=2)
        return {"format": "json", "filename": f"{safe_name}.json", "mime_type": "application/json", "content": content}
    if export_format != "markdown":
        raise ValueError("Export format must be markdown or json")
    story = detail["story"]
    lines = [f"# {story['title'] or detail['title']}"]
    if story["summary"]:
        lines.extend(["", story["summary"]])
    if story["body"]:
        lines.extend(["", story["body"]])
    lines.extend(["", "## 收录对象", ""])
    lines.extend(f"- [{item['label']}]({item['href']}) — {item['curator_note'] or item['subtitle'] or item['item_type']}" for item in detail["items"])
    return {"format": "markdown", "filename": f"{safe_name}.md", "mime_type": "text/markdown", "content": "\n".join(lines) + "\n"}


def get_owned_collection(db: Session, *, user_id: str, collection_id: str) -> KnowledgeCollection:
    row = db.get(KnowledgeCollection, collection_id)
    if row is None or row.user_id != user_id:
        raise ValueError("Collection not found")
    return row


def serialize_collection(row: KnowledgeCollection, *, stats: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.id,
        "title": row.title,
        "description": row.description,
        "collection_type": row.collection_type,
        "status": row.status,
        "item_count": stats["total"],
        "story": {"title": row.story_title, "summary": row.story_summary, "body": row.story_body, "style": row.story_style},
        "stats": stats,
        "created_at": isoformat(row.created_at),
        "updated_at": isoformat(row.updated_at),
    }


def build_collection_stats(
    db: Session,
    *,
    user_id: str,
    collection_id: str,
    items: list[KnowledgeCollectionItem] | None = None,
) -> dict[str, Any]:
    rows = items if items is not None else list(
        db.scalars(select(KnowledgeCollectionItem).where(KnowledgeCollectionItem.collection_id == collection_id)).all()
    )
    by_type: dict[str, int] = {}
    eligible: list[KnowledgeCollectionItem] = []
    for row in rows:
        by_type[row.item_type] = by_type.get(row.item_type, 0) + 1
        if row.item_type in {"entity", "event"}:
            eligible.append(row)
    linked_targets = set()
    if eligible:
        target_ids = [row.item_id for row in eligible]
        linked_targets = {
            (target_type, target_id)
            for target_type, target_id in db.execute(
                select(ManualKnowledgeEvidence.target_type, ManualKnowledgeEvidence.target_id).where(
                    ManualKnowledgeEvidence.user_id == user_id,
                    ManualKnowledgeEvidence.target_id.in_(target_ids),
                )
            ).all()
        }
    linked_count = sum(1 for row in eligible if (row.item_type, row.item_id) in linked_targets)
    eligible_count = len(eligible)
    return {
        "total": len(rows),
        "by_type": by_type,
        "evidence_eligible_count": eligible_count,
        "evidence_linked_count": linked_count,
        "evidence_coverage": round(linked_count / eligible_count, 4) if eligible_count else 0,
    }


def _empty_collection_stats() -> dict[str, Any]:
    return {"total": 0, "by_type": {}, "evidence_eligible_count": 0, "evidence_linked_count": 0, "evidence_coverage": 0}


def _query_candidates_for_type(
    db: Session, *, user_id: str, item_type: str, query: str
) -> list[dict[str, Any]]:
    model = ITEM_MODELS[item_type]
    statement = select(model).where(model.user_id == user_id)
    if query:
        pattern = f"%{query}%"
        if item_type == "note":
            statement = statement.where(or_(Note.title.ilike(pattern), Note.summary.ilike(pattern)))
        elif item_type == "raw_asset":
            statement = statement.where(or_(RawAsset.title.ilike(pattern), RawAsset.asset_type.ilike(pattern)))
        elif item_type == "entity":
            statement = statement.where(or_(Entity.display_name.ilike(pattern), Entity.canonical_name.ilike(pattern), Entity.description.ilike(pattern)))
        elif item_type == "event":
            statement = statement.where(or_(Event.title.ilike(pattern), Event.summary.ilike(pattern), Event.description.ilike(pattern)))
        else:
            statement = statement.where(or_(GraphViewpoint.name.ilike(pattern), GraphViewpoint.description.ilike(pattern)))
    rows = list(db.scalars(statement.order_by(model.updated_at.desc()).limit(50)).all())
    return [_candidate_presentation(item_type, row) for row in rows]


def _candidate_presentation(item_type: str, target: Any) -> dict[str, Any]:
    label, subtitle, href = _item_presentation(item_type, target)
    meta = None
    if item_type == "event":
        meta = target.time_text or target.event_type
    elif item_type == "entity":
        meta = target.entity_type
    elif item_type == "raw_asset":
        meta = target.asset_type
    elif item_type == "note":
        meta = target.category
    else:
        meta = target.scope
    return {"item_type": item_type, "item_id": target.id, "label": label, "subtitle": subtitle, "meta": meta, "href": href}


def serialize_collection_item(db: Session, *, user_id: str, row: KnowledgeCollectionItem) -> dict[str, Any]:
    target = _resolve_owned_item(db, user_id=user_id, item_type=row.item_type, item_id=row.item_id)
    label, subtitle, href = _item_presentation(row.item_type, target)
    has_evidence = False
    if row.item_type in {"entity", "event"}:
        has_evidence = db.scalar(
            select(ManualKnowledgeEvidence.id).where(
                ManualKnowledgeEvidence.user_id == user_id,
                ManualKnowledgeEvidence.target_type == row.item_type,
                ManualKnowledgeEvidence.target_id == row.item_id,
            ).limit(1)
        ) is not None
    return {
        "id": row.id,
        "item_type": row.item_type,
        "item_id": row.item_id,
        "label": label,
        "subtitle": subtitle,
        "href": href,
        "sort_order": row.sort_order,
        "curator_note": row.curator_note,
        "has_evidence": has_evidence,
        "created_at": isoformat(row.created_at),
    }


def _resolve_owned_item(db: Session, *, user_id: str, item_type: str, item_id: str) -> Any:
    model = ITEM_MODELS.get(item_type)
    if model is None:
        raise ValueError("Unsupported collection item type")
    target = db.get(model, item_id)
    if target is None or target.user_id != user_id:
        raise ValueError("Collection item target not found")
    return target


def _item_presentation(item_type: str, target: Any) -> tuple[str, str | None, str]:
    if item_type == "note":
        return target.title, target.summary, f"/notes/{target.id}"
    if item_type == "raw_asset":
        return target.title, target.asset_type, "/operations"
    if item_type == "entity":
        return target.display_name, target.description, f"/story/entity/{target.id}"
    if item_type == "event":
        return target.title, target.summary, f"/events/{target.id}"
    return target.name, target.description, target_href(target)


def target_href(target: GraphViewpoint) -> str:
    params = []
    if target.anchor_type and target.anchor_id:
        params.extend([(f"{target.anchor_type}_id", target.anchor_id), ("active_node_id", target.anchor_id)])
    query = "&".join(f"{key}={value}" for key, value in params)
    return f"/graph?{query}" if query else "/graph"


def _item_counts(db: Session, collection_ids: list[str]) -> dict[str, int]:
    if not collection_ids:
        return {}
    rows = db.execute(
        select(KnowledgeCollectionItem.collection_id, func.count(KnowledgeCollectionItem.id))
        .where(KnowledgeCollectionItem.collection_id.in_(collection_ids))
        .group_by(KnowledgeCollectionItem.collection_id)
    ).all()
    return {collection_id: int(count) for collection_id, count in rows}


def _audit(db: Session, *, user_id: str, target_type: str, target_id: str, action_type: str, payload: dict[str, Any]) -> None:
    db.add(ReviewAction(user_id=user_id, target_type=target_type, target_id=target_id, action_type=action_type, status_before=None, status_after="active", payload_json=payload))


def _required(value: Any, message: str) -> str:
    cleaned = str(value).strip() if value is not None else ""
    if not cleaned:
        raise ValueError(message)
    return cleaned


def _optional(value: Any) -> str | None:
    cleaned = str(value).strip() if value is not None else ""
    return cleaned or None

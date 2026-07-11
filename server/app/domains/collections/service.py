from __future__ import annotations

import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.serializers import isoformat
from app.core.pagination import PageParams, paginate_query
from app.models.collection import KnowledgeCollection, KnowledgeCollectionItem
from app.models.entity import Entity
from app.models.event import Event
from app.models.graph_viewpoint import GraphViewpoint
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
    counts = _item_counts(db, [row.id for row in rows])
    return [serialize_collection(row, item_count=counts.get(row.id, 0)) for row in rows], total


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
    return serialize_collection(row, item_count=0)


def get_collection_detail(db: Session, *, user_id: str, collection_id: str) -> dict[str, Any]:
    row = get_owned_collection(db, user_id=user_id, collection_id=collection_id)
    items = list(
        db.scalars(
            select(KnowledgeCollectionItem)
            .where(KnowledgeCollectionItem.collection_id == row.id)
            .order_by(KnowledgeCollectionItem.sort_order, KnowledgeCollectionItem.created_at)
        ).all()
    )
    return {**serialize_collection(row, item_count=len(items)), "items": [serialize_collection_item(db, user_id=user_id, row=item) for item in items]}


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


def update_collection_story(db: Session, *, user_id: str, collection_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    row = get_owned_collection(db, user_id=user_id, collection_id=collection_id)
    row.story_title = _optional(payload.get("title"))
    row.story_summary = _optional(payload.get("summary"))
    row.story_body = _optional(payload.get("body"))
    row.story_style = _optional(payload.get("style")) or "documentary"
    db.add(row)
    _audit(db, user_id=user_id, target_type="collection", target_id=row.id, action_type="update_collection_story", payload={"style": row.story_style})
    db.commit()
    return serialize_collection(row, item_count=_item_counts(db, [row.id]).get(row.id, 0))["story"]


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
    return serialize_collection(row, item_count=len(detail["items"]))["story"]


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


def serialize_collection(row: KnowledgeCollection, *, item_count: int) -> dict[str, Any]:
    return {
        "id": row.id,
        "title": row.title,
        "description": row.description,
        "collection_type": row.collection_type,
        "status": row.status,
        "item_count": item_count,
        "story": {"title": row.story_title, "summary": row.story_summary, "body": row.story_body, "style": row.story_style},
        "created_at": isoformat(row.created_at),
        "updated_at": isoformat(row.updated_at),
    }


def serialize_collection_item(db: Session, *, user_id: str, row: KnowledgeCollectionItem) -> dict[str, Any]:
    target = _resolve_owned_item(db, user_id=user_id, item_type=row.item_type, item_id=row.item_id)
    label, subtitle, href = _item_presentation(row.item_type, target)
    return {
        "id": row.id,
        "item_type": row.item_type,
        "item_id": row.item_id,
        "label": label,
        "subtitle": subtitle,
        "href": href,
        "sort_order": row.sort_order,
        "curator_note": row.curator_note,
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

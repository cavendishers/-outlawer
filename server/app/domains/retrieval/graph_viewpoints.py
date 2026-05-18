from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.serializers import isoformat
from app.models.graph_viewpoint import GraphViewpoint


def list_graph_viewpoints(db: Session, *, user_id: str, limit: int = 20) -> dict[str, Any]:
    rows = db.scalars(
        select(GraphViewpoint)
        .where(GraphViewpoint.user_id == user_id)
        .order_by(GraphViewpoint.updated_at.desc())
        .limit(limit)
    ).all()
    return {"items": [serialize_graph_viewpoint(row) for row in rows], "total": len(rows)}


def create_graph_viewpoint(
    db: Session,
    *,
    user_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ValueError("Viewpoint name is required")
    viewpoint = GraphViewpoint(
        user_id=user_id,
        name=name[:120],
        description=clean_optional_string(payload.get("description")),
        scope=clean_optional_string(payload.get("scope")) or "overview",
        anchor_type=clean_optional_string(payload.get("anchor_type")),
        anchor_id=clean_optional_string(payload.get("anchor_id")),
        filters_json=payload.get("filters_json") if isinstance(payload.get("filters_json"), dict) else {},
        layout_json=payload.get("layout_json") if isinstance(payload.get("layout_json"), dict) else {},
    )
    db.add(viewpoint)
    db.commit()
    db.refresh(viewpoint)
    return serialize_graph_viewpoint(viewpoint)


def serialize_graph_viewpoint(viewpoint: GraphViewpoint) -> dict[str, Any]:
    return {
        "id": viewpoint.id,
        "name": viewpoint.name,
        "description": viewpoint.description,
        "scope": viewpoint.scope,
        "anchor_type": viewpoint.anchor_type,
        "anchor_id": viewpoint.anchor_id,
        "filters_json": viewpoint.filters_json or {},
        "layout_json": viewpoint.layout_json or {},
        "href": build_graph_viewpoint_href(viewpoint),
        "created_at": isoformat(viewpoint.created_at),
        "updated_at": isoformat(viewpoint.updated_at),
    }


def build_graph_viewpoint_href(viewpoint: GraphViewpoint) -> str:
    params: list[tuple[str, str]] = []
    if viewpoint.anchor_type == "event" and viewpoint.anchor_id:
        params.append(("event_id", viewpoint.anchor_id))
    elif viewpoint.anchor_type == "entity" and viewpoint.anchor_id:
        params.append(("entity_id", viewpoint.anchor_id))

    filters = viewpoint.filters_json or {}
    for key in ["node_types", "relation_types"]:
        value = filters.get(key)
        if isinstance(value, list) and value:
            params.append((key, ",".join(str(item) for item in value if item)))
    for key in ["start", "end", "min_weight", "depth", "active_node_id"]:
        value = filters.get(key)
        if value not in {None, "", 0, "0"}:
            params.append((key, str(value)))

    if not params:
        return "/graph"
    return f"/graph?{urlencode(params)}"


def clean_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None

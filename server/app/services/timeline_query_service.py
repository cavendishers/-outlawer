from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.serializers import serialize_timeline_item
from app.core.pagination import PageParams, paginate_query
from app.models.event import TimelineItem
from app.services.graph_service import get_graph_overview


def list_timeline_items(
    db: Session,
    *,
    user_id: str,
    params: PageParams,
    start: str | None = None,
    end: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    query = select(TimelineItem).where(TimelineItem.user_id == user_id)
    if start:
        query = query.where(TimelineItem.sort_time >= datetime.fromisoformat(start))
    if end:
        query = query.where(TimelineItem.sort_time <= datetime.fromisoformat(end))
    items, total = paginate_query(db, query.order_by(TimelineItem.sort_time.desc()), params)
    return [serialize_timeline_item(item) for item in items], total


def get_timeline_overview(db: Session, *, user_id: str) -> dict[str, Any]:
    return get_graph_overview(db, user_id)

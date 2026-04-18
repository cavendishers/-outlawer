from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.serializers import serialize_timeline_item
from app.api.deps import DbSession, get_current_user
from app.core.pagination import normalize_page_params, paginate_query
from app.core.responses import ok, paginated
from app.models.event import TimelineItem
from app.services.graph_service import get_graph_overview

router = APIRouter()


@router.get("")
def get_timeline(
    db: DbSession,
    page: int = 1,
    page_size: int = 20,
    user=Depends(get_current_user),
) -> dict:
    params = normalize_page_params(page, page_size)
    query = select(TimelineItem).where(TimelineItem.user_id == user.id).order_by(TimelineItem.sort_time.desc())
    items, total = paginate_query(db, query, params)
    return paginated(
        items=[serialize_timeline_item(item) for item in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/overview")
def get_timeline_overview(db: DbSession, user=Depends(get_current_user)) -> dict:
    return ok(get_graph_overview(db, user.id))


@router.get("/range")
def get_timeline_range(
    db: DbSession,
    page: int = 1,
    page_size: int = 20,
    user=Depends(get_current_user),
    start: str | None = None,
    end: str | None = None,
) -> dict:
    params = normalize_page_params(page, page_size)
    query = select(TimelineItem).where(TimelineItem.user_id == user.id)
    if start:
        query = query.where(TimelineItem.sort_time >= datetime.fromisoformat(start))
    if end:
        query = query.where(TimelineItem.sort_time <= datetime.fromisoformat(end))
    items, total = paginate_query(db, query.order_by(TimelineItem.sort_time.desc()), params)
    return paginated(
        items=[serialize_timeline_item(item) for item in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
        extra={"start": start, "end": end},
    )

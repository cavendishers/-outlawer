from fastapi import APIRouter, Depends
from app.api.deps import DbSession, get_current_user
from app.core.pagination import normalize_page_params
from app.core.responses import ok, paginated
from app.schemas.common import Envelope, PaginatedData
from app.schemas.timeline import TimelineItemResponse, TimelineOverviewResponse, TimelineRangeResponse
from app.domains.retrieval import timeline_query

router = APIRouter()


@router.get("", response_model=Envelope[PaginatedData[TimelineItemResponse]])
def get_timeline(
    db: DbSession,
    page: int = 1,
    page_size: int = 20,
    user=Depends(get_current_user),
) -> dict:
    params = normalize_page_params(page, page_size)
    items, total = timeline_query.list_timeline_items(db, user_id=user.id, params=params)
    return paginated(
        items=items,
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/overview", response_model=Envelope[TimelineOverviewResponse])
def get_timeline_overview(db: DbSession, user=Depends(get_current_user)) -> dict:
    return ok(timeline_query.get_timeline_overview(db, user_id=user.id))


@router.get("/range", response_model=Envelope[TimelineRangeResponse])
def get_timeline_range(
    db: DbSession,
    page: int = 1,
    page_size: int = 20,
    user=Depends(get_current_user),
    start: str | None = None,
    end: str | None = None,
) -> dict:
    params = normalize_page_params(page, page_size)
    items, total = timeline_query.list_timeline_items(
        db,
        user_id=user.id,
        params=params,
        start=start,
        end=end,
    )
    return paginated(
        items=items,
        total=total,
        page=params.page,
        page_size=params.page_size,
        extra={"start": start, "end": end},
    )

from fastapi import APIRouter, Depends
from app.api.deps import DbSession, get_current_user
from app.core.pagination import normalize_page_params
from app.core.responses import ok, paginated
from app.services import timeline_query_service

router = APIRouter()


@router.get("")
def get_timeline(
    db: DbSession,
    page: int = 1,
    page_size: int = 20,
    user=Depends(get_current_user),
) -> dict:
    params = normalize_page_params(page, page_size)
    items, total = timeline_query_service.list_timeline_items(db, user_id=user.id, params=params)
    return paginated(
        items=items,
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/overview")
def get_timeline_overview(db: DbSession, user=Depends(get_current_user)) -> dict:
    return ok(timeline_query_service.get_timeline_overview(db, user_id=user.id))


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
    items, total = timeline_query_service.list_timeline_items(
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

from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import DbSession, get_current_user
from app.core.pagination import normalize_page_params
from app.core.responses import ok, paginated
from app.schemas.common import Envelope, PaginatedData
from app.schemas.event import EventDetailResponse, EventResponse
from app.schemas.manual_authoring import ManualEventCreateRequest, ManualEventCreateResponse
from app.domains.knowledge import manual_authoring
from app.domains.retrieval import event_query

router = APIRouter()


@router.post("", response_model=Envelope[ManualEventCreateResponse], status_code=status.HTTP_201_CREATED)
def create_event(
    payload: ManualEventCreateRequest,
    db: DbSession,
    user=Depends(get_current_user),
) -> dict:
    try:
        return ok(manual_authoring.create_manual_event(db, user_id=user.id, payload=payload.model_dump()))
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=Envelope[PaginatedData[EventResponse]])
def list_events(
    db: DbSession,
    page: int = 1,
    page_size: int = 20,
    user=Depends(get_current_user),
) -> dict:
    params = normalize_page_params(page, page_size)
    events, total = event_query.list_events(db, user_id=user.id, params=params)
    return paginated(
        items=events,
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/{event_id}", response_model=Envelope[EventDetailResponse])
def get_event(event_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(event_query.get_event_detail(db, user_id=user.id, event_id=event_id))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

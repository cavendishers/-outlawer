from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import DbSession, get_current_user
from app.core.pagination import normalize_page_params
from app.core.responses import ok, paginated
from app.schemas.common import Envelope, PaginatedData
from app.schemas.entity import EntityDetailResponse, EntityEventListResponse, EntityResponse
from app.services import entity_query_service

router = APIRouter()


@router.get("", response_model=Envelope[PaginatedData[EntityResponse]])
def list_entities(
    db: DbSession,
    page: int = 1,
    page_size: int = 20,
    user=Depends(get_current_user),
) -> dict:
    params = normalize_page_params(page, page_size)
    entities, total = entity_query_service.list_entities(db, user_id=user.id, params=params)
    return paginated(
        items=entities,
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/{entity_id}", response_model=Envelope[EntityDetailResponse])
def get_entity(entity_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(entity_query_service.get_entity_detail(db, user_id=user.id, entity_id=entity_id))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")


@router.get("/{entity_id}/events", response_model=Envelope[EntityEventListResponse])
def entity_events(entity_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok({"items": entity_query_service.list_entity_events(db, user_id=user.id, entity_id=entity_id)})
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")

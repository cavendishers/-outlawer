from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import DbSession, get_current_user
from app.core.pagination import normalize_page_params
from app.core.responses import ok, paginated
from app.domains.collections import service
from app.schemas.collection import (
    CollectionCreateRequest,
    CollectionDeletedResponse,
    CollectionDetailResponse,
    CollectionExportResponse,
    CollectionItemCreateRequest,
    CollectionItemDeletedResponse,
    CollectionItemResponse,
    CollectionItemUpdateRequest,
    CollectionResponse,
    CollectionStoryResponse,
    CollectionStoryUpdateRequest,
    CollectionTimelineResponse,
    CollectionUpdateRequest,
)
from app.schemas.common import Envelope, PaginatedData

router = APIRouter()


@router.get("", response_model=Envelope[PaginatedData[CollectionResponse]])
def list_knowledge_collections(
    db: DbSession,
    page: int = 1,
    page_size: int = 20,
    user=Depends(get_current_user),
) -> dict:
    params = normalize_page_params(page, page_size)
    rows, total = service.list_collections(db, user_id=user.id, params=params)
    return paginated(items=rows, total=total, page=params.page, page_size=params.page_size)


@router.post("", response_model=Envelope[CollectionResponse], status_code=status.HTTP_201_CREATED)
def create_knowledge_collection(
    payload: CollectionCreateRequest,
    db: DbSession,
    user=Depends(get_current_user),
) -> dict:
    return _write(lambda: service.create_collection(db, user_id=user.id, payload=payload.model_dump(mode="json")), db)


@router.get("/{collection_id}", response_model=Envelope[CollectionDetailResponse])
def get_knowledge_collection(collection_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(service.get_collection_detail(db, user_id=user.id, collection_id=collection_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{collection_id}", response_model=Envelope[CollectionDetailResponse])
def update_knowledge_collection(
    collection_id: str,
    payload: CollectionUpdateRequest,
    db: DbSession,
    user=Depends(get_current_user),
) -> dict:
    return _write(
        lambda: service.update_collection(
            db, user_id=user.id, collection_id=collection_id, payload=payload.model_dump(exclude_unset=True, mode="json")
        ),
        db,
    )


@router.delete("/{collection_id}", response_model=Envelope[CollectionDeletedResponse])
def delete_knowledge_collection(collection_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    return _write(lambda: service.delete_collection(db, user_id=user.id, collection_id=collection_id), db)


@router.post("/{collection_id}/items", response_model=Envelope[CollectionItemResponse], status_code=status.HTTP_201_CREATED)
def add_knowledge_collection_item(
    collection_id: str,
    payload: CollectionItemCreateRequest,
    db: DbSession,
    user=Depends(get_current_user),
) -> dict:
    return _write(
        lambda: service.add_collection_item(db, user_id=user.id, collection_id=collection_id, payload=payload.model_dump(mode="json")),
        db,
    )


@router.patch("/{collection_id}/items/{collection_item_id}", response_model=Envelope[CollectionItemResponse])
def update_knowledge_collection_item(
    collection_id: str,
    collection_item_id: str,
    payload: CollectionItemUpdateRequest,
    db: DbSession,
    user=Depends(get_current_user),
) -> dict:
    return _write(
        lambda: service.update_collection_item(
            db,
            user_id=user.id,
            collection_id=collection_id,
            collection_item_id=collection_item_id,
            payload=payload.model_dump(exclude_unset=True, mode="json"),
        ),
        db,
    )


@router.delete("/{collection_id}/items/{collection_item_id}", response_model=Envelope[CollectionItemDeletedResponse])
def remove_knowledge_collection_item(
    collection_id: str,
    collection_item_id: str,
    db: DbSession,
    user=Depends(get_current_user),
) -> dict:
    return _write(
        lambda: service.remove_collection_item(
            db, user_id=user.id, collection_id=collection_id, collection_item_id=collection_item_id
        ),
        db,
    )


@router.put("/{collection_id}/story", response_model=Envelope[CollectionStoryResponse])
def update_knowledge_collection_story(
    collection_id: str,
    payload: CollectionStoryUpdateRequest,
    db: DbSession,
    user=Depends(get_current_user),
) -> dict:
    return _write(
        lambda: service.update_collection_story(
            db, user_id=user.id, collection_id=collection_id, payload=payload.model_dump(mode="json")
        ),
        db,
    )


@router.post("/{collection_id}/story/compile", response_model=Envelope[CollectionStoryResponse])
def compile_knowledge_collection_story(collection_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    return _write(lambda: service.compile_collection_story(db, user_id=user.id, collection_id=collection_id), db)


@router.get("/{collection_id}/timeline", response_model=Envelope[CollectionTimelineResponse])
def get_knowledge_collection_timeline(collection_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(service.build_collection_timeline(db, user_id=user.id, collection_id=collection_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{collection_id}/export", response_model=Envelope[CollectionExportResponse])
def export_knowledge_collection(
    collection_id: str,
    db: DbSession,
    format: str = "markdown",
    user=Depends(get_current_user),
) -> dict:
    try:
        return ok(service.export_collection(db, user_id=user.id, collection_id=collection_id, export_format=format))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def _write(action, db: DbSession) -> dict:
    try:
        return ok(action())
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import DbSession, get_current_user
from app.core.responses import ok
from app.domains.retrieval import graph_paths, graph_workspace
from app.domains.governance import graph_conflicts
from app.domains.knowledge import manual_authoring
from app.schemas.common import Envelope
from app.schemas.graph import (
    GraphConflictDispositionRequest,
    GraphConflictDispositionResponse,
    GraphPathResponse,
    GraphWorkspaceNodeDetailResponse,
    GraphWorkspaceResponse,
)
from app.schemas.manual_authoring import GraphManualNodeCreateRequest, GraphManualNodeCreateResponse

router = APIRouter()


@router.post("/manual-nodes", response_model=Envelope[GraphManualNodeCreateResponse], status_code=status.HTTP_201_CREATED)
def create_graph_manual_node(
    payload: GraphManualNodeCreateRequest,
    db: DbSession,
    user=Depends(get_current_user),
) -> dict:
    try:
        return ok(manual_authoring.create_graph_manual_node(db, user_id=user.id, payload=payload.model_dump()))
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/path", response_model=Envelope[GraphPathResponse])
def get_graph_path(
    source_type: str,
    source_id: str,
    target_type: str,
    target_id: str,
    db: DbSession,
    max_depth: int = 4,
    user=Depends(get_current_user),
) -> dict:
    try:
        return ok(
            graph_paths.find_graph_path(
                db,
                user_id=user.id,
                source_type=source_type,
                source_id=source_id,
                target_type=target_type,
                target_id=target_id,
                max_depth=max_depth,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/conflicts/{conflict_id}/disposition",
    response_model=Envelope[GraphConflictDispositionResponse],
)
def set_graph_conflict_disposition(
    conflict_id: str,
    payload: GraphConflictDispositionRequest,
    db: DbSession,
    user=Depends(get_current_user),
) -> dict:
    try:
        return ok(
            graph_conflicts.set_graph_conflict_disposition(
                db,
                user_id=user.id,
                conflict_id=conflict_id,
                payload=payload.model_dump(mode="json"),
            )
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/workspace", response_model=Envelope[GraphWorkspaceResponse])
def get_graph_workspace(
    db: DbSession,
    event_id: str | None = None,
    entity_id: str | None = None,
    collection_id: str | None = None,
    node_types: str | None = None,
    relation_types: str | None = None,
    start: str | None = None,
    end: str | None = None,
    min_weight: float | None = None,
    depth: int | None = None,
    user=Depends(get_current_user),
) -> dict:
    try:
        return ok(
            graph_workspace.get_graph_workspace(
                db,
                user_id=user.id,
                event_id=event_id,
                entity_id=entity_id,
                collection_id=collection_id,
                node_types=node_types,
                relation_types=relation_types,
                start=start,
                end=end,
                min_weight=min_weight,
                depth=depth,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/nodes/{node_type}/{node_id}", response_model=Envelope[GraphWorkspaceNodeDetailResponse])
def get_graph_node_detail(
    node_type: str,
    node_id: str,
    db: DbSession,
    event_id: str | None = None,
    entity_id: str | None = None,
    collection_id: str | None = None,
    node_types: str | None = None,
    relation_types: str | None = None,
    start: str | None = None,
    end: str | None = None,
    min_weight: float | None = None,
    depth: int | None = None,
    user=Depends(get_current_user),
) -> dict:
    try:
        return ok(
            graph_workspace.get_graph_node_detail(
                db,
                user_id=user.id,
                node_type=node_type,
                node_id=node_id,
                event_id=event_id,
                entity_id=entity_id,
                collection_id=collection_id,
                node_types=node_types,
                relation_types=relation_types,
                start=start,
                end=end,
                min_weight=min_weight,
                depth=depth,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

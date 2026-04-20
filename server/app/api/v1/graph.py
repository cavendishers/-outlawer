from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import DbSession, get_current_user
from app.core.responses import ok
from app.schemas.common import Envelope
from app.schemas.graph import GraphWorkspaceNodeDetailResponse, GraphWorkspaceResponse
from app.services import graph_workspace_service

router = APIRouter()


@router.get("/workspace", response_model=Envelope[GraphWorkspaceResponse])
def get_graph_workspace(
    db: DbSession,
    event_id: str | None = None,
    entity_id: str | None = None,
    user=Depends(get_current_user),
) -> dict:
    try:
        return ok(
            graph_workspace_service.get_graph_workspace(
                db,
                user_id=user.id,
                event_id=event_id,
                entity_id=entity_id,
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
    user=Depends(get_current_user),
) -> dict:
    try:
        return ok(
            graph_workspace_service.get_graph_node_detail(
                db,
                user_id=user.id,
                node_type=node_type,
                node_id=node_id,
                event_id=event_id,
                entity_id=entity_id,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

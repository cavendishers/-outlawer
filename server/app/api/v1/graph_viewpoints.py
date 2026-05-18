from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import DbSession, get_current_user
from app.core.responses import ok
from app.domains.retrieval import graph_viewpoints
from app.schemas.common import CollectionData, Envelope
from app.schemas.graph_viewpoint import GraphViewpointCreateRequest, GraphViewpointResponse

router = APIRouter()


@router.get("", response_model=Envelope[CollectionData[GraphViewpointResponse]])
def list_graph_viewpoint_items(db: DbSession, user=Depends(get_current_user)) -> dict:
    return ok(graph_viewpoints.list_graph_viewpoints(db, user_id=user.id))


@router.post("", response_model=Envelope[GraphViewpointResponse])
def create_graph_viewpoint_item(
    payload: GraphViewpointCreateRequest,
    db: DbSession,
    user=Depends(get_current_user),
) -> dict:
    try:
        return ok(graph_viewpoints.create_graph_viewpoint(db, user_id=user.id, payload=payload.model_dump(mode="json")))
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

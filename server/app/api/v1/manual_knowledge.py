from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import DbSession, get_current_user
from app.core.responses import ok
from app.domains.knowledge import manual_authoring
from app.schemas.common import Envelope
from app.schemas.manual_authoring import ManualEvidenceCreateRequest, ManualEvidenceListResponse, ManualEvidenceResponse

router = APIRouter()


@router.get("/evidence", response_model=Envelope[ManualEvidenceListResponse])
def get_manual_evidence(
    target_type: str,
    target_id: str,
    db: DbSession,
    user=Depends(get_current_user),
) -> dict:
    try:
        return ok(manual_authoring.list_manual_evidence(db, user_id=user.id, target_type=target_type, target_id=target_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/evidence", response_model=Envelope[ManualEvidenceResponse], status_code=status.HTTP_201_CREATED)
def create_manual_evidence(
    payload: ManualEvidenceCreateRequest,
    db: DbSession,
    user=Depends(get_current_user),
) -> dict:
    try:
        return ok(manual_authoring.attach_manual_evidence(db, user_id=user.id, payload=payload.model_dump(mode="json")))
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

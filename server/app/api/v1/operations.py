from fastapi import APIRouter, Depends

from app.api.deps import DbSession, get_current_user
from app.core.responses import ok
from app.schemas.common import Envelope
from app.schemas.operations import OperationsOverviewResponse
from app.services import operations_service

router = APIRouter()


@router.get("/overview", response_model=Envelope[OperationsOverviewResponse])
def get_operations_overview(db: DbSession, user=Depends(get_current_user)) -> dict:
    return ok(operations_service.get_operations_overview(db, user_id=user.id))

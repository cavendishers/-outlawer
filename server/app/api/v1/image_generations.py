from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession, get_current_user
from app.core.pagination import normalize_page_params, paginate_query
from app.core.responses import ok, paginated
from app.domains.image_generation.service import create_image_generation, serialize_image_generation
from app.models.image_generation import ImageGeneration
from app.schemas.common import Envelope, PaginatedData
from app.schemas.image_generation import (
    ImageGenerationCreateRequest,
    ImageGenerationCreateResponse,
    ImageGenerationResponse,
)
from app.shared.messaging.jobs import dispatch_job

router = APIRouter()


@router.post("", response_model=Envelope[ImageGenerationCreateResponse])
def create_generation(payload: ImageGenerationCreateRequest, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        generation, job = create_image_generation(
            db,
            user_id=user.id,
            prompt=payload.prompt,
            model=payload.model,
            aspect_ratio=payload.aspect_ratio,
            image_size=payload.image_size,
            reference_asset_ids=payload.reference_asset_ids,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    db.refresh(generation)
    db.refresh(job)
    dispatch_job(job)
    return ok({"generation_id": generation.id, "job_id": job.id, "status": generation.status})


@router.get("", response_model=Envelope[PaginatedData[ImageGenerationResponse]])
def list_generations(
    db: DbSession,
    page: int = 1,
    page_size: int = 20,
    user=Depends(get_current_user),
) -> dict:
    params = normalize_page_params(page, page_size, max_page_size=50)
    query = select(ImageGeneration).where(ImageGeneration.user_id == user.id).order_by(ImageGeneration.created_at.desc())
    generations, total = paginate_query(db, query, params)
    return paginated(
        items=[serialize_image_generation(generation, db) for generation in generations],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/{generation_id}", response_model=Envelope[ImageGenerationResponse])
def get_generation(generation_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    generation = db.get(ImageGeneration, generation_id)
    if not generation or generation.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image generation not found")
    return ok(serialize_image_generation(generation, db, include_assets=True))

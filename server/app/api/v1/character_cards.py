import json
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select

from app.api.deps import DbSession, get_current_user
from app.core.minio import download_bytes
from app.core.pagination import normalize_page_params, paginate_query
from app.core.responses import ok, paginated
from app.domains.character_cards.service import (
    create_card_from_entity,
    create_avatar_generation,
    create_role_image_generation,
    normalize_export_spec,
    serialize_card,
    serialize_card_with_assets,
    update_card,
)
from app.models.character_card import CharacterCard
from app.models.raw_asset import RawAsset
from app.schemas.character_card import (
    CharacterCardCreateRequest,
    CharacterCardCreateResponse,
    CharacterCardAvatarGenerateRequest,
    CharacterCardAvatarGenerateResponse,
    CharacterCardResponse,
    CharacterCardRoleImageGenerateRequest,
    CharacterCardRoleImageGenerateResponse,
    CharacterCardUpdateRequest,
)
from app.schemas.common import Envelope, PaginatedData

router = APIRouter()


@router.post("/from-entity/{entity_id}", response_model=Envelope[CharacterCardCreateResponse])
def create_from_entity(
    entity_id: str,
    payload: CharacterCardCreateRequest,
    db: DbSession,
    user=Depends(get_current_user),
) -> dict:
    try:
        card = create_card_from_entity(
            db,
            user_id=user.id,
            entity_id=entity_id,
            mode=payload.mode,
            include_story_view=payload.include_story_view,
            include_character_book=payload.include_character_book,
            language=payload.language,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    db.commit()
    db.refresh(card)
    return ok({"card": serialize_card_with_assets(card, db)})


@router.get("", response_model=Envelope[PaginatedData[CharacterCardResponse]])
def list_cards(
    db: DbSession,
    page: int = 1,
    page_size: int = 20,
    entity_id: str | None = None,
    user=Depends(get_current_user),
) -> dict:
    params = normalize_page_params(page, page_size, max_page_size=50)
    query = select(CharacterCard).where(CharacterCard.user_id == user.id)
    if entity_id:
        query = query.where(CharacterCard.source_entity_id == entity_id)
    query = query.order_by(CharacterCard.updated_at.desc())
    cards, total = paginate_query(db, query, params)
    return paginated(
        items=[serialize_card_with_assets(card, db) for card in cards],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/{card_id}", response_model=Envelope[CharacterCardResponse])
def get_card(card_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    card = get_owned_card(db, user_id=user.id, card_id=card_id)
    return ok(serialize_card_with_assets(card, db))


@router.patch("/{card_id}", response_model=Envelope[CharacterCardResponse])
def patch_card(
    card_id: str,
    payload: CharacterCardUpdateRequest,
    db: DbSession,
    user=Depends(get_current_user),
) -> dict:
    card = get_owned_card(db, user_id=user.id, card_id=card_id)
    update_card(card, title=payload.title, status=payload.status, spec_json=payload.spec_json)
    db.add(card)
    db.commit()
    db.refresh(card)
    return ok(serialize_card_with_assets(card, db))


@router.post("/{card_id}/regenerate", response_model=Envelope[CharacterCardResponse])
def regenerate_card(
    card_id: str,
    payload: CharacterCardCreateRequest,
    db: DbSession,
    user=Depends(get_current_user),
) -> dict:
    card = get_owned_card(db, user_id=user.id, card_id=card_id)
    try:
        regenerated = create_card_from_entity(
            db,
            user_id=user.id,
            entity_id=card.source_entity_id,
            mode=payload.mode,
            include_story_view=payload.include_story_view,
            include_character_book=payload.include_character_book,
            language=payload.language,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    card.mode = regenerated.mode
    card.spec_json = regenerated.spec_json
    card.source_snapshot_json = regenerated.source_snapshot_json
    card.title = regenerated.title
    db.expunge(regenerated)
    db.add(card)
    db.commit()
    db.refresh(card)
    return ok(serialize_card_with_assets(card, db))


@router.post("/{card_id}/generate-avatar", response_model=Envelope[CharacterCardAvatarGenerateResponse])
def generate_avatar(
    card_id: str,
    payload: CharacterCardAvatarGenerateRequest,
    db: DbSession,
    user=Depends(get_current_user),
) -> dict:
    card = get_owned_card(db, user_id=user.id, card_id=card_id)
    try:
        generation, job = create_avatar_generation(
            db,
            user_id=user.id,
            card=card,
            model=payload.model,
            aspect_ratio=payload.aspect_ratio,
            image_size=payload.image_size,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    db.refresh(card)
    db.refresh(generation)
    db.refresh(job)
    from app.shared.messaging.jobs import dispatch_job

    dispatch_job(job)
    return ok(
        {
            "card": serialize_card_with_assets(card, db),
            "generation_id": generation.id,
            "job_id": job.id,
            "status": generation.status,
        }
    )


@router.post("/{card_id}/generate-role-image", response_model=Envelope[CharacterCardRoleImageGenerateResponse])
def generate_role_image(
    card_id: str,
    payload: CharacterCardRoleImageGenerateRequest,
    db: DbSession,
    user=Depends(get_current_user),
) -> dict:
    card = get_owned_card(db, user_id=user.id, card_id=card_id)
    try:
        generation, job = create_role_image_generation(
            db,
            user_id=user.id,
            card=card,
            model=payload.model,
            aspect_ratio=payload.aspect_ratio,
            image_size=payload.image_size,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    db.refresh(card)
    db.refresh(generation)
    db.refresh(job)
    from app.shared.messaging.jobs import dispatch_job

    dispatch_job(job)
    return ok(
        {
            "card": serialize_card_with_assets(card, db),
            "generation_id": generation.id,
            "job_id": job.id,
            "status": generation.status,
        }
    )


@router.get("/{card_id}/export.json")
def export_card_json(card_id: str, db: DbSession, user=Depends(get_current_user)) -> Response:
    card = get_owned_card(db, user_id=user.id, card_id=card_id)
    spec = normalize_export_spec(card.spec_json or {})
    content = json.dumps(spec, ensure_ascii=False, indent=2)
    filename = sanitize_filename(spec.get("data", {}).get("name") or card.title or "character-card")
    encoded_filename = quote(f"{filename}.json")
    return Response(
        content=content,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=\"character-card.json\"; filename*=UTF-8''{encoded_filename}"},
    )


@router.get("/{card_id}/avatar")
def get_card_avatar(card_id: str, db: DbSession, user=Depends(get_current_user)) -> Response:
    card = get_owned_card(db, user_id=user.id, card_id=card_id)
    if not card.avatar_asset_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character card avatar not found")
    asset = db.get(RawAsset, card.avatar_asset_id)
    if not asset or asset.user_id != user.id or asset.asset_type != "image" or not asset.object_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character card avatar not found")
    content = download_bytes(asset.object_key)
    return Response(content=content, media_type=asset.mime_type or "image/png")


@router.get("/{card_id}/role-image")
def get_card_role_image(card_id: str, db: DbSession, user=Depends(get_current_user)) -> Response:
    card = get_owned_card(db, user_id=user.id, card_id=card_id)
    if not card.role_image_asset_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character card role image not found")
    asset = db.get(RawAsset, card.role_image_asset_id)
    if not asset or asset.user_id != user.id or asset.asset_type != "image" or not asset.object_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character card role image not found")
    content = download_bytes(asset.object_key)
    return Response(content=content, media_type=asset.mime_type or "image/png")


def get_owned_card(db: DbSession, *, user_id: str, card_id: str) -> CharacterCard:
    card = db.get(CharacterCard, card_id)
    if not card or card.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character card not found")
    return card


def sanitize_filename(value: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in value.strip())
    return cleaned.strip("-") or "character-card"

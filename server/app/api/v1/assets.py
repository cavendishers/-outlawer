from hashlib import sha256
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select

from app.api.serializers import serialize_asset
from app.api.deps import DbSession, get_current_user
from app.core.config import get_settings
from app.core.minio import get_presigned_url, upload_bytes
from app.core.pagination import normalize_page_params, paginate_query
from app.core.responses import ok, paginated
from app.models.raw_asset import RawAsset

router = APIRouter()
settings = get_settings()


@router.post("/upload")
async def upload_asset(
    db: DbSession,
    user=Depends(get_current_user),  # type: ignore[name-defined]
    title: str = Form(...),
    asset_type: str = Form(...),
    original_text: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
) -> dict:
    if asset_type not in {"text", "audio", "image", "video"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported asset type")
    if asset_type == "text" and not original_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Text assets require original_text")
    if asset_type != "text" and file is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File assets require a file upload")

    object_key = None
    checksum = None
    mime_type = None
    file_size = None
    if file:
        content = await file.read()
        object_key = f"{user.id}/{uuid4()}-{file.filename}"
        mime_type = file.content_type
        file_size = len(content)
        checksum = sha256(content).hexdigest()
        upload_bytes(object_key, content, mime_type or "application/octet-stream")

    asset = RawAsset(
        user_id=user.id,
        asset_type=asset_type,
        source_type="manual",
        title=title,
        original_text=original_text,
        bucket_name=settings.minio_bucket if object_key else None,
        object_key=object_key,
        mime_type=mime_type,
        file_size=file_size,
        checksum=checksum,
        status="uploaded",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return ok(serialize_asset(asset))


@router.get("")
def list_assets(
    db: DbSession,
    page: int = 1,
    page_size: int = 20,
    user=Depends(get_current_user),
) -> dict:
    params = normalize_page_params(page, page_size)
    query = select(RawAsset).where(RawAsset.user_id == user.id).order_by(RawAsset.created_at.desc())
    assets, total = paginate_query(db, query, params)
    return paginated(
        items=[
            serialize_asset(asset, raw_url=get_presigned_url(asset.object_key) if asset.object_key else None)
            for asset in assets
        ],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/{asset_id}")
def get_asset(asset_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    asset = db.get(RawAsset, asset_id)
    if not asset or asset.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return ok(serialize_asset(asset, raw_url=get_presigned_url(asset.object_key) if asset.object_key else None))


@router.get("/{asset_id}/raw")
def get_asset_raw(asset_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    asset = db.get(RawAsset, asset_id)
    if not asset or asset.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return ok(
        {
            "asset_id": asset.id,
            "original_text": asset.original_text,
            "raw_url": get_presigned_url(asset.object_key) if asset.object_key else None,
        }
    )

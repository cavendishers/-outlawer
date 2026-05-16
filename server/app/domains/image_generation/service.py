from __future__ import annotations

import base64
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import PurePosixPath
from uuid import uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.serializers import serialize_asset, isoformat
from app.core.config import get_settings
from app.core.minio import download_bytes, get_presigned_url, upload_bytes
from app.models.ai_job import AIJob
from app.models.image_generation import ImageGeneration
from app.models.raw_asset import RawAsset
from app.domains.image_generation.sy_gpt import SyGPTImageClient, decode_data_url, resolve_model_config

GENERATION_STATUS_PENDING = "pending"
GENERATION_STATUS_RUNNING = "running"
GENERATION_STATUS_COMPLETED = "completed"
GENERATION_STATUS_FAILED = "failed"

JOB_STATUS_PENDING = "pending"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_FAILED = "failed"


def create_image_generation(
    db: Session,
    *,
    user_id: str,
    prompt: str,
    model: str | None,
    aspect_ratio: str,
    image_size: str,
    reference_asset_ids: list[str],
    payload_extra: dict | None = None,
) -> tuple[ImageGeneration, AIJob]:
    settings = get_settings()
    if not settings.sy_gpt_api_key:
        raise RuntimeError("SY_GPT_API_KEY is not configured")
    resolved = resolve_model_config(model, aspect_ratio, image_size)
    validate_reference_assets(db, user_id=user_id, reference_asset_ids=reference_asset_ids)
    generation = ImageGeneration(
        user_id=user_id,
        status=GENERATION_STATUS_PENDING,
        prompt=prompt.strip(),
        model_name=resolved.request_model,
        aspect_ratio=resolved.aspect_ratio,
        image_size=resolved.image_size,
        reference_asset_ids=reference_asset_ids,
        result_urls=[],
        result_asset_ids=[],
        raw_response_json={},
    )
    db.add(generation)
    db.flush()
    job_payload = {
        "generation_id": generation.id,
        "model": generation.model_name,
        "aspect_ratio": generation.aspect_ratio,
        "image_size": generation.image_size,
        "reference_asset_ids": reference_asset_ids,
    }
    if payload_extra:
        job_payload.update(payload_extra)
    job = AIJob(
        user_id=user_id,
        job_type="image_generation",
        target_type="image_generation",
        target_id=generation.id,
        status=JOB_STATUS_PENDING,
        payload_json=job_payload,
    )
    db.add(job)
    db.flush()
    generation.job_id = job.id
    db.add(generation)
    return generation, job


def validate_reference_assets(db: Session, *, user_id: str, reference_asset_ids: list[str]) -> list[RawAsset]:
    assets: list[RawAsset] = []
    for asset_id in reference_asset_ids:
        asset = db.get(RawAsset, asset_id)
        if not asset or asset.user_id != user_id:
            raise ValueError("Reference asset not found")
        if asset.asset_type != "image":
            raise ValueError("Reference assets must be images")
        if not asset.object_key:
            raise ValueError("Reference image has no stored object")
        assets.append(asset)
    return assets


def process_image_generation(db: Session, job_id: str, *, client: SyGPTImageClient | None = None) -> None:
    job = db.get(AIJob, job_id)
    if not job:
        raise ValueError(f"AI job {job_id} not found")
    generation = db.get(ImageGeneration, job.target_id)
    if not generation:
        raise ValueError(f"Image generation {job.target_id} not found")

    started_at = datetime.now(UTC)
    job.status = JOB_STATUS_RUNNING
    job.error_message = None
    generation.status = GENERATION_STATUS_RUNNING
    generation.error_message = None
    generation.started_at = started_at
    generation.finished_at = None
    db.add_all([job, generation])
    db.commit()

    try:
        reference_images = build_reference_images(db, generation)
        active_client = client or SyGPTImageClient()
        result = active_client.generate(
            prompt=generation.prompt,
            model=generation.model_name,
            aspect_ratio=generation.aspect_ratio,
            image_size=generation.image_size,
            reference_images=reference_images,
        )
        result_asset_ids = persist_generated_images(
            db,
            generation=generation,
            image_urls=result.image_urls,
        )
        finished_at = datetime.now(UTC)
        generation.status = GENERATION_STATUS_COMPLETED
        generation.upstream_task_id = result.upstream_task_id
        generation.result_urls = summarize_result_urls(result.image_urls)
        generation.result_asset_ids = result_asset_ids
        generation.raw_response_json = result.raw_response
        generation.finished_at = finished_at
        job.status = JOB_STATUS_COMPLETED
        job.result_json = {
            "generation_id": generation.id,
            "result_asset_ids": result_asset_ids,
            "result_urls": generation.result_urls,
            "upstream_task_id": result.upstream_task_id,
        }
        apply_completion_hook(db, job, result_asset_ids)
        job.finished_at = finished_at
        db.add_all([generation, job])
        db.commit()
    except Exception as exc:  # noqa: BLE001
        mark_image_generation_failed(db, job_id, str(exc))
        raise


def build_reference_images(db: Session, generation: ImageGeneration) -> list[dict[str, str]]:
    assets = validate_reference_assets(db, user_id=generation.user_id, reference_asset_ids=generation.reference_asset_ids or [])
    images: list[dict[str, str]] = []
    for asset in assets:
        content = download_bytes(asset.object_key or "")
        if not content:
            raise ValueError("Reference image has no stored object")
        images.append(
            {
                "base64": base64.b64encode(content).decode("ascii"),
                "mime_type": asset.mime_type or "image/png",
            }
        )
    return images


def persist_generated_images(db: Session, *, generation: ImageGeneration, image_urls: list[str]) -> list[str]:
    asset_ids: list[str] = []
    for index, image_url in enumerate(image_urls, start=1):
        content, mime_type = load_generated_image(image_url)
        suffix = suffix_for_mime_type(mime_type)
        object_key = f"{generation.user_id}/generated/{generation.id}/{index}-{uuid4()}{suffix}"
        upload_bytes(object_key, content, mime_type)
        asset = RawAsset(
            user_id=generation.user_id,
            asset_type="image",
            source_type="image_generation",
            title=f"Generated image {index}",
            original_text=None,
            bucket_name=get_settings().minio_bucket,
            object_key=object_key,
            mime_type=mime_type,
            file_size=len(content),
            checksum=sha256(content).hexdigest(),
            status="uploaded",
        )
        db.add(asset)
        db.flush()
        asset_ids.append(asset.id)
    return asset_ids


def load_generated_image(image_url: str) -> tuple[bytes, str]:
    decoded = decode_data_url(image_url)
    if decoded:
        return decoded
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        response = client.get(image_url)
        response.raise_for_status()
        mime_type = response.headers.get("content-type", "image/png").split(";")[0].strip() or "image/png"
        return response.content, mime_type


def summarize_result_urls(image_urls: list[str]) -> list[str]:
    summaries: list[str] = []
    for value in image_urls:
        if value.startswith("data:image/"):
            header = value.split(",", 1)[0]
            summaries.append(f"{header},[base64]")
        else:
            summaries.append(value)
    return summaries


def mark_image_generation_failed(db: Session, job_id: str, message: str) -> None:
    db.rollback()
    job = db.get(AIJob, job_id)
    generation = db.get(ImageGeneration, job.target_id) if job else None
    finished_at = datetime.now(UTC)
    if job:
        job.status = JOB_STATUS_FAILED
        job.error_message = message
        job.finished_at = finished_at
        db.add(job)
    if generation:
        generation.status = GENERATION_STATUS_FAILED
        generation.error_message = message
        generation.finished_at = finished_at
        db.add(generation)
    db.commit()


def apply_completion_hook(db: Session, job: AIJob, result_asset_ids: list[str]) -> None:
    hook = (job.payload_json or {}).get("completion_hook")
    if hook not in {"character_card_avatar", "character_card_role_image"} or not result_asset_ids:
        return
    card_id = (job.payload_json or {}).get("character_card_id")
    if not card_id:
        return
    from app.models.character_card import CharacterCard

    card = db.get(CharacterCard, card_id)
    if not card or card.user_id != job.user_id:
        return
    if hook == "character_card_avatar":
        card.avatar_asset_id = result_asset_ids[0]
    if hook == "character_card_role_image":
        card.role_image_asset_id = result_asset_ids[0]
    db.add(card)


def serialize_image_generation(generation: ImageGeneration, db: Session, *, include_assets: bool = False) -> dict:
    result_assets = []
    if include_assets and generation.result_asset_ids:
        assets = db.scalars(select(RawAsset).where(RawAsset.id.in_(generation.result_asset_ids))).all()
        asset_by_id = {asset.id: asset for asset in assets}
        result_assets = [
            serialize_asset(asset, raw_url=get_presigned_url(asset.object_key) if asset.object_key else None)
            for asset_id in generation.result_asset_ids
            if (asset := asset_by_id.get(asset_id))
        ]
    return {
        "id": generation.id,
        "job_id": generation.job_id,
        "status": generation.status,
        "prompt": generation.prompt,
        "model_name": generation.model_name,
        "aspect_ratio": generation.aspect_ratio,
        "image_size": generation.image_size,
        "reference_asset_ids": generation.reference_asset_ids or [],
        "upstream_task_id": generation.upstream_task_id,
        "result_urls": generation.result_urls or [],
        "result_asset_ids": generation.result_asset_ids or [],
        "error_message": generation.error_message,
        "raw_response_json": generation.raw_response_json or {},
        "result_assets": result_assets,
        "created_at": isoformat(generation.created_at),
        "updated_at": isoformat(generation.updated_at),
        "started_at": isoformat(generation.started_at),
        "finished_at": isoformat(generation.finished_at),
    }


def suffix_for_mime_type(mime_type: str) -> str:
    subtype = PurePosixPath(mime_type.split("/", 1)[-1]).name.lower()
    return {
        "jpeg": ".jpg",
        "jpg": ".jpg",
        "png": ".png",
        "webp": ".webp",
        "gif": ".gif",
    }.get(subtype, ".png")

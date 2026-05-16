import base64
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.database import Base
from app.domains.image_generation import service
from app.domains.image_generation.sy_gpt import (
    ImageGenerationResult,
    extract_images,
    map_task_status,
    resolve_model_config,
)
from app.models.ai_job import AIJob
from app.models.character_card import CharacterCard
from app.models.entity import Entity
from app.models.image_generation import ImageGeneration
from app.models.raw_asset import RawAsset
from app.models.user import User
from app.shared.messaging.jobs import JOB_TASKS


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[User.__table__, AIJob.__table__, RawAsset.__table__, ImageGeneration.__table__, Entity.__table__, CharacterCard.__table__],
    )
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()


def add_user(db, user_id: str = "user-1") -> User:
    user = User(
        id=user_id,
        username=f"{user_id}@example.test",
        password_hash="hash",
        display_name="Tester",
        status="active",
    )
    db.add(user)
    db.commit()
    return user


def test_resolve_model_config_accepts_defaults_and_variants() -> None:
    default = resolve_model_config(None, None, None)
    variant = resolve_model_config("gpt-image-2-landscape-2k", None, None)

    assert default.request_model == "gpt-image-2"
    assert default.aspect_ratio == "9:16"
    assert default.image_size == "1K"
    assert variant.request_model == "gpt-image-2-landscape-2k"
    assert variant.aspect_ratio == "16:9"
    assert variant.image_size == "2K"


def test_resolve_model_config_rejects_unsupported_models() -> None:
    with pytest.raises(ValueError, match="Only gpt-image-2"):
        resolve_model_config("other-image-model", "1:1", "1K")

    with pytest.raises(ValueError, match="does not support 4K"):
        resolve_model_config("gpt-image-2-square-4k", "1:1", "1K")


def test_extract_images_from_common_response_shapes() -> None:
    payload = {
        "result": {
            "choices": [
                {
                    "message": {
                        "content": [
                            {"image_url": "https://cdn.example.test/image.png"},
                            {"b64_json": base64.b64encode(b"png" * 32).decode("ascii")},
                        ]
                    }
                }
            ],
            "inlineData": {"mimeType": "image/webp", "data": base64.b64encode(b"webp" * 32).decode("ascii")},
        }
    }

    images = extract_images(payload)

    assert "https://cdn.example.test/image.png" in images
    assert any(item.startswith("data:image/png;base64,") for item in images)
    assert any(item.startswith("data:image/webp;base64,") for item in images)
    assert map_task_status("succeeded") == "completed"
    assert map_task_status("canceled") == "cancelled"


def test_validate_reference_assets_requires_current_user_image_with_object() -> None:
    db = make_db()
    add_user(db)
    asset = RawAsset(
        id="asset-1",
        user_id="user-1",
        asset_type="text",
        source_type="manual",
        title="Not image",
        status="uploaded",
    )
    db.add(asset)
    db.commit()

    with pytest.raises(ValueError, match="must be images"):
        service.validate_reference_assets(db, user_id="user-1", reference_asset_ids=["asset-1"])


def test_process_image_generation_marks_job_completed_and_creates_raw_asset(monkeypatch) -> None:
    db = make_db()
    add_user(db)
    generation = ImageGeneration(
        id="generation-1",
        user_id="user-1",
        status="pending",
        prompt="draw a luminous archive",
        model_name="gpt-image-2",
        aspect_ratio="9:16",
        image_size="1K",
        reference_asset_ids=[],
        result_urls=[],
        result_asset_ids=[],
        raw_response_json={},
    )
    job = AIJob(
        id="job-1",
        user_id="user-1",
        job_type="image_generation",
        target_type="image_generation",
        target_id=generation.id,
        status="pending",
        payload_json={},
        result_json={},
    )
    generation.job_id = job.id
    db.add_all([generation, job])
    db.commit()
    uploads = []
    monkeypatch.setattr(service, "upload_bytes", lambda object_key, content, content_type: uploads.append((object_key, content, content_type)))

    class FakeClient:
        def generate(self, **kwargs):
            return ImageGenerationResult(
                image_urls=["data:image/png;base64,cG5n"],
                upstream_task_id="task-1",
                raw_response={"task": {"status": "completed"}},
            )

    service.process_image_generation(db, "job-1", client=FakeClient())
    db.refresh(generation)
    db.refresh(job)

    assert generation.status == "completed"
    assert generation.upstream_task_id == "task-1"
    assert generation.result_asset_ids
    assert generation.result_urls == ["data:image/png;base64,[base64]"]
    assert job.status == "completed"
    assert job.result_json["result_asset_ids"] == generation.result_asset_ids
    assert uploads and uploads[0][2] == "image/png"
    asset = db.get(RawAsset, generation.result_asset_ids[0])
    assert asset.asset_type == "image"
    assert asset.source_type == "image_generation"


def test_process_image_generation_completion_hook_sets_character_card_avatar(monkeypatch) -> None:
    db = make_db()
    add_user(db)
    entity = Entity(
        id="entity-avatar",
        user_id="user-1",
        entity_type="person",
        canonical_name="张三",
        display_name="张三",
        alias_json=[],
        normalized_name="张三",
        status="active",
    )
    card = CharacterCard(
        id="card-avatar",
        user_id="user-1",
        source_entity_id=entity.id,
        status="draft",
        title="张三 人物卡",
        card_format="sillytavern",
        card_version="chara_card_v2",
        mode="faithful",
        spec_json={},
        source_snapshot_json={},
    )
    generation = ImageGeneration(
        id="generation-avatar",
        user_id="user-1",
        status="pending",
        prompt="draw avatar",
        model_name="gpt-image-2-square",
        aspect_ratio="1:1",
        image_size="1K",
        reference_asset_ids=[],
        result_urls=[],
        result_asset_ids=[],
        raw_response_json={},
    )
    job = AIJob(
        id="job-avatar",
        user_id="user-1",
        job_type="image_generation",
        target_type="image_generation",
        target_id=generation.id,
        status="pending",
        payload_json={"completion_hook": "character_card_avatar", "character_card_id": card.id},
        result_json={},
    )
    generation.job_id = job.id
    db.add_all([entity, card, generation, job])
    db.commit()
    monkeypatch.setattr(service, "upload_bytes", lambda object_key, content, content_type: None)

    class FakeClient:
        def generate(self, **kwargs):
            return ImageGenerationResult(
                image_urls=["data:image/png;base64,cG5n"],
                upstream_task_id="task-avatar",
                raw_response={"task": {"status": "completed"}},
            )

    service.process_image_generation(db, job.id, client=FakeClient())
    db.refresh(card)

    assert card.avatar_asset_id == generation.result_asset_ids[0]


def test_process_image_generation_completion_hook_sets_character_card_role_image(monkeypatch) -> None:
    db = make_db()
    add_user(db)
    entity = Entity(
        id="entity-role-image",
        user_id="user-1",
        entity_type="person",
        canonical_name="艾琳",
        display_name="艾琳",
        alias_json=[],
        normalized_name="艾琳",
        status="active",
    )
    card = CharacterCard(
        id="card-role-image",
        user_id="user-1",
        source_entity_id=entity.id,
        status="draft",
        title="艾琳 人物卡",
        card_format="sillytavern",
        card_version="chara_card_v2",
        mode="faithful",
        spec_json={},
        source_snapshot_json={},
    )
    generation = ImageGeneration(
        id="generation-role-image",
        user_id="user-1",
        status="pending",
        prompt="draw role card",
        model_name="gpt-image-2-three-four",
        aspect_ratio="3:4",
        image_size="1K",
        reference_asset_ids=[],
        result_urls=[],
        result_asset_ids=[],
        raw_response_json={},
    )
    job = AIJob(
        id="job-role-image",
        user_id="user-1",
        job_type="image_generation",
        target_type="image_generation",
        target_id=generation.id,
        status="pending",
        payload_json={"completion_hook": "character_card_role_image", "character_card_id": card.id},
        result_json={},
    )
    generation.job_id = job.id
    db.add_all([entity, card, generation, job])
    db.commit()
    monkeypatch.setattr(service, "upload_bytes", lambda object_key, content, content_type: None)

    class FakeClient:
        def generate(self, **kwargs):
            return ImageGenerationResult(
                image_urls=["data:image/png;base64,cG5n"],
                upstream_task_id="task-role-image",
                raw_response={"task": {"status": "completed"}},
            )

    service.process_image_generation(db, job.id, client=FakeClient())
    db.refresh(card)

    assert card.role_image_asset_id == generation.result_asset_ids[0]


def test_process_image_generation_marks_job_failed_on_client_error() -> None:
    db = make_db()
    add_user(db)
    generation = ImageGeneration(
        id="generation-2",
        user_id="user-1",
        status="pending",
        prompt="draw a failed archive",
        model_name="gpt-image-2",
        aspect_ratio="9:16",
        image_size="1K",
        reference_asset_ids=[],
        result_urls=[],
        result_asset_ids=[],
        raw_response_json={},
    )
    job = AIJob(
        id="job-2",
        user_id="user-1",
        job_type="image_generation",
        target_type="image_generation",
        target_id=generation.id,
        status="pending",
        payload_json={},
        result_json={},
    )
    generation.job_id = job.id
    db.add_all([generation, job])
    db.commit()

    class FailingClient:
        def generate(self, **kwargs):
            raise ValueError("upstream failed")

    with pytest.raises(ValueError, match="upstream failed"):
        service.process_image_generation(db, "job-2", client=FailingClient())
    db.refresh(generation)
    db.refresh(job)

    assert generation.status == "failed"
    assert generation.error_message == "upstream failed"
    assert job.status == "failed"
    assert job.error_message == "upstream failed"
    assert isinstance(generation.finished_at, datetime)


def test_image_generation_job_type_is_dispatchable() -> None:
    assert "image_generation" in JOB_TASKS

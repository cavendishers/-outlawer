import argparse
import json
import os
import struct
import time
import wave
import zlib
from io import BytesIO
from uuid import uuid4

import httpx
from sqlalchemy import and_, delete, or_, select, update

from app.core.database import SessionLocal
from app.core.minio import get_minio_client, settings as minio_settings
from app.models.ai_job import AIJob
from app.models.asset_derivative import AssetDerivative
from app.models.character_card import CharacterCard
from app.models.embedding import Embedding
from app.models.entity import Entity, EntityAlias, EventEntity, NoteEntity, NoteEvent, Relation
from app.models.event import Event, TimelineItem
from app.models.extraction import ExtractionEvidence, ExtractionRun, MergeCandidate, ProjectionVersion
from app.models.image_generation import ImageGeneration
from app.models.note import Note, NoteChunk
from app.models.raw_asset import RawAsset
from app.models.review import ReviewAction
from app.models.style_view import StyleView


def bailian_configured() -> bool:
    return bool(os.getenv("BAILIAN_API_KEY"))


def assert_ok(response: httpx.Response) -> dict:
    response.raise_for_status()
    payload = response.json()
    assert payload["code"] == 0, payload
    return payload["data"]


def build_test_png(width: int = 2, height: int = 1) -> bytes:
    signature = b"\x89PNG\r\n\x1a\n"

    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + chunk_type
            + data
            + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    row = b"\x00" + b"\xff\xff\xff" * width
    idat = zlib.compress(row * height)
    return signature + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def build_test_wav(duration_seconds: int = 1, sample_rate: int = 16000) -> bytes:
    buffer = BytesIO()
    frame_count = duration_seconds * sample_rate
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * frame_count)
    return buffer.getvalue()


def assert_multimodal_derivatives(
    *,
    normalized_derivative: AssetDerivative | None,
    analysis_derivative: AssetDerivative | None,
    expected_ai_markers: list[str],
) -> None:
    assert normalized_derivative is not None
    if bailian_configured():
        assert any(marker in normalized_derivative.content for marker in expected_ai_markers), normalized_derivative.content
        assert analysis_derivative is not None
        analysis_payload = json.loads(analysis_derivative.content)
        assert analysis_payload.get("provider_name") == "bailian"
        assert analysis_payload.get("model_name")
        return

    parser_name = normalized_derivative.meta_json.get("parser")
    assert parser_name in {"bailian_not_configured", "bailian_multimodal_failed", "local_plus_openrouter_multimodal"}
    assert (
        "当前未能完成多模态内容识别" in normalized_derivative.content
        or any(marker in normalized_derivative.content for marker in expected_ai_markers)
    ), normalized_derivative.content


def build_run_marker() -> str:
    return f"E2E-{int(time.time())}-{uuid4().hex[:8]}"


def build_person_names() -> tuple[str, str]:
    chinese_digits = "甲乙丙丁戊己庚辛壬癸子丑寅卯辰巳午未申酉戌亥"
    suffix = uuid4().hex[:4]
    first = chinese_digits[int(suffix[:2], 16) % len(chinese_digits)]
    second = chinese_digits[int(suffix[2:], 16) % len(chinese_digits)]
    return f"张测{first}", f"李验{second}"


def track_projection_ids(created: dict[str, set[str]], note_id: str) -> None:
    event_ids, entity_ids = get_note_projection_ids(note_id)
    created["event_ids"].update(event_ids)
    created["entity_ids"].update(entity_ids)


def delete_where_ids(db, model: type, id_field, values: set[str]) -> None:
    if values:
        db.execute(delete(model).where(id_field.in_(values)))


def delete_where_owner_ids(db, model: type, owner_field, values: set[str], *conditions: object) -> None:
    if values:
        db.execute(delete(model).where(and_(owner_field.in_(values), *conditions)))


def cleanup_created_records(created: dict[str, set[str]]) -> None:
    note_ids = set(created["note_ids"])
    asset_ids = set(created["asset_ids"])
    job_ids = set(created["job_ids"])
    event_ids = set(created.get("event_ids", set()))
    entity_ids = set(created.get("entity_ids", set()))
    object_keys: list[str] = []

    if not note_ids and not asset_ids and not job_ids:
        return

    with SessionLocal() as db:
        if asset_ids:
            object_keys = [
                item
                for item in db.scalars(select(RawAsset.object_key).where(RawAsset.id.in_(asset_ids))).all()
                if item
            ]

        note_asset_ids = set[str]()
        if note_ids:
            note_asset_ids.update(db.scalars(select(Note.asset_id).where(Note.id.in_(note_ids), Note.asset_id.is_not(None))).all())
            asset_ids.update(note_asset_ids)
            event_ids.update(db.scalars(select(NoteEvent.event_id).where(NoteEvent.note_id.in_(note_ids))).all())
            event_ids.update(db.scalars(select(Event.id).where(Event.source_note_id.in_(note_ids))).all())
            entity_ids.update(db.scalars(select(NoteEntity.entity_id).where(NoteEntity.note_id.in_(note_ids))).all())
        if event_ids:
            entity_ids.update(db.scalars(select(EventEntity.entity_id).where(EventEntity.event_id.in_(event_ids))).all())

        if note_ids:
            notes = db.scalars(select(Note).where(Note.id.in_(note_ids))).all()
            for note in notes:
                note.active_projection_id = None
                db.add(note)
            db.flush()

        all_owner_ids = note_ids | event_ids | entity_ids

        delete_where_owner_ids(db, ReviewAction, ReviewAction.target_id, note_ids, ReviewAction.target_type == "note")
        delete_where_owner_ids(db, AIJob, AIJob.id, job_ids)
        delete_where_owner_ids(db, ImageGeneration, ImageGeneration.job_id, job_ids)
        if note_ids:
            db.execute(delete(AIJob).where(AIJob.target_type == "note", AIJob.target_id.in_(note_ids)))

        if event_ids or entity_ids:
            merge_conditions = []
            if event_ids:
                merge_conditions.extend(
                    [
                        and_(MergeCandidate.object_type == "event", MergeCandidate.source_id.in_(event_ids)),
                        and_(MergeCandidate.object_type == "event", MergeCandidate.candidate_id.in_(event_ids)),
                    ]
                )
            if entity_ids:
                merge_conditions.extend(
                    [
                        and_(MergeCandidate.object_type == "entity", MergeCandidate.source_id.in_(entity_ids)),
                        and_(MergeCandidate.object_type == "entity", MergeCandidate.candidate_id.in_(entity_ids)),
                    ]
                )
            db.execute(delete(MergeCandidate).where(or_(*merge_conditions)))

        if note_ids:
            db.execute(update(Event).where(Event.source_note_id.in_(note_ids), Event.id.not_in(event_ids)).values(source_note_id=None))

        delete_where_owner_ids(db, ExtractionEvidence, ExtractionEvidence.source_note_id, note_ids)
        if all_owner_ids:
            db.execute(
                delete(ExtractionEvidence).where(
                    or_(
                        ExtractionEvidence.target_id.in_(all_owner_ids),
                        ExtractionEvidence.source_asset_id.in_(asset_ids) if asset_ids else False,
                    )
                )
            )

        relation_conditions = []
        for object_type, ids in [("note", note_ids), ("event", event_ids), ("entity", entity_ids)]:
            if ids:
                relation_conditions.extend(
                    [
                        and_(Relation.source_type == object_type, Relation.source_id.in_(ids)),
                        and_(Relation.target_type == object_type, Relation.target_id.in_(ids)),
                    ]
                )
        if relation_conditions:
            db.execute(delete(Relation).where(or_(*relation_conditions)))

        delete_where_owner_ids(db, EventEntity, EventEntity.event_id, event_ids)
        delete_where_owner_ids(db, EventEntity, EventEntity.entity_id, entity_ids)
        delete_where_owner_ids(db, NoteEntity, NoteEntity.note_id, note_ids)
        delete_where_owner_ids(db, NoteEntity, NoteEntity.entity_id, entity_ids)
        delete_where_owner_ids(db, NoteEvent, NoteEvent.note_id, note_ids)
        delete_where_owner_ids(db, NoteEvent, NoteEvent.event_id, event_ids)
        delete_where_owner_ids(db, TimelineItem, TimelineItem.event_id, event_ids)
        delete_where_owner_ids(db, TimelineItem, TimelineItem.note_id, note_ids)

        delete_where_ids(db, CharacterCard, CharacterCard.source_entity_id, entity_ids)
        if all_owner_ids:
            db.execute(delete(StyleView).where(StyleView.target_id.in_(all_owner_ids)))
            db.execute(delete(Embedding).where(Embedding.owner_id.in_(all_owner_ids)))

        delete_where_owner_ids(db, ProjectionVersion, ProjectionVersion.note_id, note_ids)
        delete_where_owner_ids(db, ExtractionRun, ExtractionRun.note_id, note_ids)
        delete_where_owner_ids(db, NoteChunk, NoteChunk.note_id, note_ids)
        delete_where_ids(db, Event, Event.id, event_ids)
        delete_where_owner_ids(db, EntityAlias, EntityAlias.entity_id, entity_ids)
        delete_where_ids(db, Entity, Entity.id, entity_ids)
        delete_where_ids(db, Note, Note.id, note_ids)
        delete_where_owner_ids(db, AssetDerivative, AssetDerivative.asset_id, asset_ids)
        delete_where_ids(db, RawAsset, RawAsset.id, asset_ids)
        db.commit()

    if object_keys:
        client = get_minio_client()
        for object_key in object_keys:
            try:
                client.remove_object(minio_settings.minio_bucket, object_key)
            except Exception:
                pass


def wait_for_job(
    client: httpx.Client,
    *,
    base_url: str,
    headers: dict[str, str],
    job_id: str,
    timeout_seconds: int,
    poll_interval_seconds: int,
) -> dict:
    job_status = None
    for _ in range(max(1, timeout_seconds // max(1, poll_interval_seconds))):
        job_status = assert_ok(client.get(f"{base_url}/jobs/{job_id}", headers=headers))
        if job_status["status"] == "completed":
            return job_status
        time.sleep(poll_interval_seconds)
    assert job_status is not None
    assert job_status["status"] == "completed", job_status
    return job_status


def get_note_projection_ids(note_id: str) -> tuple[list[str], list[str]]:
    with SessionLocal() as db:
        event_ids = list(db.scalars(select(NoteEvent.event_id).where(NoteEvent.note_id == note_id)).all())
        entity_ids = list(db.scalars(select(NoteEntity.entity_id).where(NoteEntity.note_id == note_id)).all())
    return event_ids, entity_ids


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--phase", default="full", choices=["phase1", "phase2", "phase3", "full"])
    parser.add_argument("--job-timeout-seconds", type=int, default=180)
    parser.add_argument("--poll-interval-seconds", type=int, default=2)
    args = parser.parse_args()

    client = httpx.Client(timeout=20.0, trust_env=False)
    run_marker = build_run_marker()
    person_a, person_b = build_person_names()
    created: dict[str, set[str]] = {
        "asset_ids": set(),
        "note_ids": set(),
        "job_ids": set(),
        "event_ids": set(),
        "entity_ids": set(),
    }

    try:
        health = assert_ok(client.get(f"{args.base_url}/health"))
        assert health["status"] == "healthy"

        login = assert_ok(client.post(f"{args.base_url}/auth/login", json={"username": "admin", "password": "admin123456"}))
        token = login["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        me = assert_ok(client.get(f"{args.base_url}/auth/me", headers=headers))
        assert me["username"] == "admin"

        if args.phase == "phase1":
            print("Phase 1 e2e passed")
            return

        asset = assert_ok(
            client.post(
                f"{args.base_url}/assets/upload",
                headers=headers,
                data={
                    "title": f"{run_marker} 启动会记录",
                    "asset_type": "text",
                    "original_text": f"2026-04-18 {run_marker} {person_a}和{person_b}在会议室A进行资料导入研判，讨论图谱与导入流程。",
                },
            )
        )
        created["asset_ids"].add(asset["id"])
        asset_detail = assert_ok(client.get(f"{args.base_url}/assets/{asset['id']}", headers=headers))
        assert asset_detail["title"] == f"{run_marker} 启动会记录"

        if args.phase == "phase2":
            print("Phase 2 e2e passed")
            return

        note_create = assert_ok(client.post(f"{args.base_url}/notes", headers=headers, json={"asset_id": asset["id"]}))
        job_id = note_create["job_id"]
        note_id = note_create["note_id"]
        created["job_ids"].add(job_id)
        created["note_ids"].add(note_id)

        job_detail = assert_ok(client.get(f"{args.base_url}/jobs/{job_id}", headers=headers))
        assert job_detail["payload_json"]["asset_id"] == asset["id"]
        wait_for_job(
            client,
            base_url=args.base_url,
            headers=headers,
            job_id=job_id,
            timeout_seconds=args.job_timeout_seconds,
            poll_interval_seconds=args.poll_interval_seconds,
        )

        note = assert_ok(client.get(f"{args.base_url}/notes/{note_id}", headers=headers))
        assert note["status"] == "ready"
        analysis_workflow = assert_ok(client.get(f"{args.base_url}/notes/{note_id}/analysis-workflow", headers=headers))
        assert analysis_workflow["note"]["id"] == note_id
        assert analysis_workflow["steps"], analysis_workflow
        assert analysis_workflow["runs"], analysis_workflow
        assert "raw_result_json" in analysis_workflow["runs"][0]
        assert "normalized_result_json" in analysis_workflow["runs"][0]
        event_ids, entity_ids = get_note_projection_ids(note_id)
        assert event_ids, event_ids
        assert entity_ids, entity_ids
        created["event_ids"].update(event_ids)
        created["entity_ids"].update(entity_ids)
        event_id = event_ids[0]
        entity_id = entity_ids[0]

        entities = assert_ok(client.get(f"{args.base_url}/entities", headers=headers))
        assert any(item["id"] in entity_ids for item in entities["items"]), entities
        events = assert_ok(client.get(f"{args.base_url}/events", headers=headers))
        assert any(item["id"] in event_ids for item in events["items"]), events
        entity_detail = assert_ok(client.get(f"{args.base_url}/entities/{entity_id}", headers=headers))
        assert "timeline_fragments" in entity_detail
        timeline = assert_ok(client.get(f"{args.base_url}/timeline", headers=headers))
        assert any(item.get("event_id") in event_ids for item in timeline["items"]), timeline
        graph_overview = assert_ok(client.get(f"{args.base_url}/timeline/overview", headers=headers))
        assert "nodes" in graph_overview
        assert "edges" in graph_overview
        event_detail = assert_ok(client.get(f"{args.base_url}/events/{event_id}", headers=headers))
        assert "related_events" in event_detail
        event_workspace = assert_ok(client.get(f"{args.base_url}/graph/workspace", headers=headers, params={"event_id": event_id}))
        assert event_workspace["scope"] == "event"
        assert event_workspace["nodes"], event_workspace
        event_node_detail = assert_ok(client.get(f"{args.base_url}/graph/nodes/event/{event_id}", headers=headers, params={"event_id": event_id}))
        assert event_node_detail["node"]["id"] == event_id
        assert "anchor_actions" in event_node_detail
        story = assert_ok(client.get(f"{args.base_url}/views/story/note/{note_id}", headers=headers))
        assert story["title"]
        search = assert_ok(client.get(f"{args.base_url}/search", headers=headers, params={"q": "导入"}))
        assert search["items"], search
        entity_workspace = assert_ok(client.get(f"{args.base_url}/graph/workspace", headers=headers, params={"entity_id": entity_id}))
        assert entity_workspace["scope"] == "entity"
        assert entity_workspace["timeline_focus"] is not None
        entity_node_detail = assert_ok(client.get(f"{args.base_url}/graph/nodes/entity/{entity_id}", headers=headers, params={"entity_id": entity_id}))
        assert entity_node_detail["node"]["id"] == entity_id
        assert "connected_nodes" in entity_node_detail
        overview_workspace = assert_ok(client.get(f"{args.base_url}/graph/workspace", headers=headers))
        assert overview_workspace["scope"] == "overview"
        track_projection_ids(created, note_id)
        operations_overview = assert_ok(client.get(f"{args.base_url}/operations/overview", headers=headers))
        assert operations_overview["jobs"]["total"] >= 1
        assert operations_overview["assets"]["total"] >= 1
        assert "recent_actions" in operations_overview["activity"]

        if args.phase == "phase3":
            print("Phase 3 e2e passed")
            return

        image_asset = assert_ok(
            client.post(
                f"{args.base_url}/assets/upload",
                headers=headers,
                data={"title": f"{run_marker} 白板讨论照片", "asset_type": "image"},
                files={"file": ("launch.png", build_test_png(), "image/png")},
            )
        )
        created["asset_ids"].add(image_asset["id"])
        image_note_create = assert_ok(client.post(f"{args.base_url}/notes", headers=headers, json={"asset_id": image_asset["id"]}))
        image_job_id = image_note_create["job_id"]
        image_note_id = image_note_create["note_id"]
        created["job_ids"].add(image_job_id)
        created["note_ids"].add(image_note_id)
        wait_for_job(
            client,
            base_url=args.base_url,
            headers=headers,
            job_id=image_job_id,
            timeout_seconds=args.job_timeout_seconds,
            poll_interval_seconds=args.poll_interval_seconds,
        )

        image_note = assert_ok(client.get(f"{args.base_url}/notes/{image_note_id}", headers=headers))
        assert image_note["status"] == "ready"
        track_projection_ids(created, image_note_id)
        with SessionLocal() as db:
            normalized_derivative = db.scalar(
                select(AssetDerivative).where(
                    and_(AssetDerivative.asset_id == image_asset["id"], AssetDerivative.derivative_type == "normalized_text")
                )
            )
            analysis_derivative = db.scalar(
                select(AssetDerivative).where(
                    and_(AssetDerivative.asset_id == image_asset["id"], AssetDerivative.derivative_type == "analysis_json")
                )
            )
            assert_multimodal_derivatives(
                normalized_derivative=normalized_derivative,
                analysis_derivative=analysis_derivative,
                expected_ai_markers=["识别场景：", "识别物件：", "文档类型：", "规范化内容："],
            )
        image_asset_detail = assert_ok(client.get(f"{args.base_url}/assets/{image_asset['id']}", headers=headers))
        assert image_asset_detail["derivatives"], image_asset_detail
        assert any(item["derivative_type"] == "normalized_text" for item in image_asset_detail["derivatives"])

        audio_asset = assert_ok(
            client.post(
                f"{args.base_url}/assets/upload",
                headers=headers,
                data={"title": f"{run_marker} 后续待办录音", "asset_type": "audio"},
                files={"file": ("followup.wav", build_test_wav(), "audio/wav")},
            )
        )
        created["asset_ids"].add(audio_asset["id"])
        audio_note_create = assert_ok(client.post(f"{args.base_url}/notes", headers=headers, json={"asset_id": audio_asset["id"]}))
        audio_job_id = audio_note_create["job_id"]
        audio_note_id = audio_note_create["note_id"]
        created["job_ids"].add(audio_job_id)
        created["note_ids"].add(audio_note_id)
        wait_for_job(
            client,
            base_url=args.base_url,
            headers=headers,
            job_id=audio_job_id,
            timeout_seconds=args.job_timeout_seconds,
            poll_interval_seconds=args.poll_interval_seconds,
        )
        track_projection_ids(created, audio_note_id)

        with SessionLocal() as db:
            normalized_derivative = db.scalar(
                select(AssetDerivative).where(
                    and_(AssetDerivative.asset_id == audio_asset["id"], AssetDerivative.derivative_type == "normalized_text")
                )
            )
            analysis_derivative = db.scalar(
                select(AssetDerivative).where(
                    and_(AssetDerivative.asset_id == audio_asset["id"], AssetDerivative.derivative_type == "analysis_json")
                )
            )
            assert_multimodal_derivatives(
                normalized_derivative=normalized_derivative,
                analysis_derivative=analysis_derivative,
                expected_ai_markers=["对话类型：", "识别议题：", "音频片段：", "规范化内容："],
            )
        audio_asset_detail = assert_ok(client.get(f"{args.base_url}/assets/{audio_asset['id']}", headers=headers))
        assert audio_asset_detail["derivatives"], audio_asset_detail
        if bailian_configured():
            assert any(item["derivative_type"] == "analysis_json" for item in audio_asset_detail["derivatives"])

        reprocess = assert_ok(client.post(f"{args.base_url}/notes/{note_id}/reprocess", headers=headers))
        replay_job_id = reprocess["job_id"]
        created["job_ids"].add(replay_job_id)
        wait_for_job(
            client,
            base_url=args.base_url,
            headers=headers,
            job_id=replay_job_id,
            timeout_seconds=args.job_timeout_seconds,
            poll_interval_seconds=args.poll_interval_seconds,
        )
        track_projection_ids(created, note_id)

        extraction_runs = assert_ok(client.get(f"{args.base_url}/notes/{note_id}/extraction-runs", headers=headers))
        assert extraction_runs["total"] >= 2, extraction_runs
        analysis_workflow_after_reprocess = assert_ok(client.get(f"{args.base_url}/notes/{note_id}/analysis-workflow", headers=headers))
        assert analysis_workflow_after_reprocess["stats"]["run_count"] >= 2
        assert analysis_workflow_after_reprocess["stats"]["job_count"] >= 2
        applied_runs = [item for item in extraction_runs["items"] if item["is_applied"]]
        review_runs = [item for item in extraction_runs["items"] if item["status"] == "ready_for_review"]
        assert len(applied_runs) == 1, extraction_runs
        assert len(review_runs) == 1, extraction_runs
        current_applied_run_id = applied_runs[0]["id"]
        review_run_id = review_runs[0]["id"]
        extraction_run = assert_ok(client.get(f"{args.base_url}/notes/{note_id}/extraction-runs/{review_run_id}", headers=headers))
        assert extraction_run["summary"]["event_count"] >= 1
        assert extraction_run["provider_name"]
        assert extraction_run["model_name"]
        assert extraction_run["prompt_version"]
        assert extraction_run["schema_version"]
        assert extraction_run["input_hash"]
        assert extraction_run["run_kind"] == "reprocess"
        assert extraction_run["projection_status"] == "pending_review"
        extraction_compare = assert_ok(
            client.get(
                f"{args.base_url}/notes/{note_id}/extraction-runs/compare",
                headers=headers,
                params={"base_run_id": current_applied_run_id, "candidate_run_id": review_run_id},
            )
        )
        assert "summary" in extraction_compare["diff"]
        assert "entities" in extraction_compare["diff"]
        assert extraction_compare["candidate_run"]["id"] == review_run_id
        approved = assert_ok(
            client.post(
                f"{args.base_url}/notes/{note_id}/extraction-runs/{review_run_id}/approve",
                headers=headers,
                json={"note": "审批通过新的抽取草稿，确认草稿审批链路。"},
            )
        )
        assert approved["approved_run"]["id"] == review_run_id
        assert approved["approved_run"]["is_applied"] is True
        assert approved["approved_run"]["projection_status"] == "applied"
        assert approved["projection_result"]["projection_version_id"]
        assert approved["replay_actions"], approved
        assert approved["note"]["active_projection_id"] == approved["projection_result"]["projection_version_id"]
        extraction_runs_after_approve = assert_ok(client.get(f"{args.base_url}/notes/{note_id}/extraction-runs", headers=headers))
        applied_run_ids = [item["id"] for item in extraction_runs_after_approve["items"] if item["is_applied"]]
        assert applied_run_ids == [review_run_id], extraction_runs_after_approve
        replay_actions = assert_ok(client.get(f"{args.base_url}/notes/{note_id}/replay-actions", headers=headers))
        assert replay_actions["items"], replay_actions
        assert replay_actions["items"][0]["run_id"] == review_run_id
        assert replay_actions["items"][0]["projection_version_id"]
        assert replay_actions["items"][0]["note"] == "审批通过新的抽取草稿，确认草稿审批链路。"
        regenerated_story = assert_ok(client.post(f"{args.base_url}/notes/{note_id}/story/regenerate", headers=headers))
        assert regenerated_story["note_id"] == note_id
        assert regenerated_story["run_id"] == review_run_id
        assert regenerated_story["story_view"]["target_id"] == note_id
        replay_actions_after_story = assert_ok(client.get(f"{args.base_url}/notes/{note_id}/replay-actions", headers=headers))
        assert any(item["action_type"] == "regenerate_story_view" for item in replay_actions_after_story["items"])

        second_asset = assert_ok(
            client.post(
                f"{args.base_url}/assets/upload",
                headers=headers,
                data={
                    "title": f"{run_marker} 启动会补充记录",
                    "asset_type": "text",
                    "original_text": f"2026-04-19 {run_marker} {person_a}和{person_b}再次记录资料导入研判，补充图谱拆分与导入流程。",
                },
            )
        )
        created["asset_ids"].add(second_asset["id"])
        second_note_create = assert_ok(client.post(f"{args.base_url}/notes", headers=headers, json={"asset_id": second_asset["id"]}))
        second_job_id = second_note_create["job_id"]
        second_note_id = second_note_create["note_id"]
        created["job_ids"].add(second_job_id)
        created["note_ids"].add(second_note_id)
        wait_for_job(
            client,
            base_url=args.base_url,
            headers=headers,
            job_id=second_job_id,
            timeout_seconds=args.job_timeout_seconds,
            poll_interval_seconds=args.poll_interval_seconds,
        )
        track_projection_ids(created, second_note_id)

        similar = assert_ok(client.get(f"{args.base_url}/search/similar/{second_note_id}", headers=headers))
        assert similar["items"], similar
        unified = assert_ok(
            client.get(
                f"{args.base_url}/search/unified",
                headers=headers,
                params={"q": "导入", "seed_note_id": second_note_id},
            )
        )
        assert unified["notes"], unified
        assert unified["events"], unified
        assert "entities" in unified
        assert "similar_notes" in unified
        merge_candidates = assert_ok(client.get(f"{args.base_url}/search/merge-candidates", headers=headers, params={"object_type": "event"}))
        assert merge_candidates["items"], merge_candidates
        print("Full e2e passed")
    finally:
        cleanup_created_records(created)
        client.close()


if __name__ == "__main__":
    main()

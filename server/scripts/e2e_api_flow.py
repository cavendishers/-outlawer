import argparse
import json
import struct
import time
import wave
import zlib
from io import BytesIO

import httpx
from sqlalchemy import and_, select

from app.core.database import SessionLocal
from app.models.asset_derivative import AssetDerivative


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--phase", default="full", choices=["phase1", "phase2", "phase3", "full"])
    parser.add_argument("--job-timeout-seconds", type=int, default=180)
    parser.add_argument("--poll-interval-seconds", type=int, default=2)
    args = parser.parse_args()

    client = httpx.Client(timeout=20.0, trust_env=False)

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
                "title": "启动会记录",
                "asset_type": "text",
                "original_text": "2026-04-18 张三和李四在会议室A召开项目启动会，讨论图谱与导入流程。",
            },
        )
    )
    asset_detail = assert_ok(client.get(f"{args.base_url}/assets/{asset['id']}", headers=headers))
    assert asset_detail["title"] == "启动会记录"

    if args.phase == "phase2":
        print("Phase 2 e2e passed")
        return

    note_create = assert_ok(client.post(f"{args.base_url}/notes", headers=headers, json={"asset_id": asset["id"]}))
    job_id = note_create["job_id"]
    note_id = note_create["note_id"]
    job_detail = assert_ok(client.get(f"{args.base_url}/jobs/{job_id}", headers=headers))
    assert job_detail["payload_json"]["asset_id"] == asset["id"]
    job_status = None
    for _ in range(max(1, args.job_timeout_seconds // max(1, args.poll_interval_seconds))):
        job_status = assert_ok(client.get(f"{args.base_url}/jobs/{job_id}", headers=headers))
        if job_status["status"] == "completed":
            break
        time.sleep(args.poll_interval_seconds)
    assert job_status is not None
    assert job_status["status"] == "completed", job_status

    note = assert_ok(client.get(f"{args.base_url}/notes/{note_id}", headers=headers))
    assert note["status"] == "ready"
    entities = assert_ok(client.get(f"{args.base_url}/entities", headers=headers))
    assert entities["items"], entities
    events = assert_ok(client.get(f"{args.base_url}/events", headers=headers))
    assert events["items"], events
    entity_detail = assert_ok(client.get(f"{args.base_url}/entities/{entities['items'][0]['id']}", headers=headers))
    assert "timeline_fragments" in entity_detail
    timeline = assert_ok(client.get(f"{args.base_url}/timeline", headers=headers))
    assert timeline["items"], timeline
    graph_overview = assert_ok(client.get(f"{args.base_url}/timeline/overview", headers=headers))
    assert "nodes" in graph_overview
    assert "edges" in graph_overview
    event_detail = assert_ok(client.get(f"{args.base_url}/events/{events['items'][0]['id']}", headers=headers))
    assert "related_events" in event_detail
    story = assert_ok(client.get(f"{args.base_url}/views/story/note/{note_id}", headers=headers))
    assert story["title"]
    search = assert_ok(client.get(f"{args.base_url}/search", headers=headers, params={"q": "启动"}))
    assert search["items"], search

    if args.phase == "phase3":
        print("Phase 3 e2e passed")
        return

    image_asset = assert_ok(
        client.post(
            f"{args.base_url}/assets/upload",
            headers=headers,
            data={
                "title": "项目启动会白板讨论照片",
                "asset_type": "image",
            },
            files={
                "file": (
                    "launch.png",
                    build_test_png(),
                    "image/png",
                )
            },
        )
    )
    image_note_create = assert_ok(client.post(f"{args.base_url}/notes", headers=headers, json={"asset_id": image_asset["id"]}))
    image_job_id = image_note_create["job_id"]
    image_note_id = image_note_create["note_id"]
    image_job_status = None
    for _ in range(max(1, args.job_timeout_seconds // max(1, args.poll_interval_seconds))):
        image_job_status = assert_ok(client.get(f"{args.base_url}/jobs/{image_job_id}", headers=headers))
        if image_job_status["status"] == "completed":
            break
        time.sleep(args.poll_interval_seconds)
    assert image_job_status is not None
    assert image_job_status["status"] == "completed", image_job_status

    image_note = assert_ok(client.get(f"{args.base_url}/notes/{image_note_id}", headers=headers))
    assert image_note["status"] == "ready"

    with SessionLocal() as db:
        normalized_derivative = db.scalar(
            select(AssetDerivative).where(
                and_(
                    AssetDerivative.asset_id == image_asset["id"],
                    AssetDerivative.derivative_type == "normalized_text",
                )
            )
        )
        analysis_derivative = db.scalar(
            select(AssetDerivative).where(
                and_(
                    AssetDerivative.asset_id == image_asset["id"],
                    AssetDerivative.derivative_type == "analysis_json",
                )
            )
        )
        assert normalized_derivative is not None
        assert "识别场景：" in normalized_derivative.content
        assert "识别物件：" in normalized_derivative.content
        assert "文档类型：" in normalized_derivative.content
        assert analysis_derivative is not None
        analysis_payload = json.loads(analysis_derivative.content)
        assert "会议现场" in analysis_payload.get("observed_scene", [])
        assert "白板" in analysis_payload.get("observed_objects", [])
        assert analysis_payload.get("document_type")
    image_asset_detail = assert_ok(client.get(f"{args.base_url}/assets/{image_asset['id']}", headers=headers))
    assert image_asset_detail["derivatives"], image_asset_detail
    assert any(item["derivative_type"] == "normalized_text" for item in image_asset_detail["derivatives"])

    audio_asset = assert_ok(
        client.post(
            f"{args.base_url}/assets/upload",
            headers=headers,
            data={
                "title": "项目启动会议后续待办录音",
                "asset_type": "audio",
            },
            files={
                "file": (
                    "followup.wav",
                    build_test_wav(),
                    "audio/wav",
                )
            },
        )
    )
    audio_note_create = assert_ok(client.post(f"{args.base_url}/notes", headers=headers, json={"asset_id": audio_asset["id"]}))
    audio_job_id = audio_note_create["job_id"]
    audio_job_status = None
    for _ in range(max(1, args.job_timeout_seconds // max(1, args.poll_interval_seconds))):
        audio_job_status = assert_ok(client.get(f"{args.base_url}/jobs/{audio_job_id}", headers=headers))
        if audio_job_status["status"] == "completed":
            break
        time.sleep(args.poll_interval_seconds)
    assert audio_job_status is not None
    assert audio_job_status["status"] == "completed", audio_job_status

    with SessionLocal() as db:
        normalized_derivative = db.scalar(
            select(AssetDerivative).where(
                and_(
                    AssetDerivative.asset_id == audio_asset["id"],
                    AssetDerivative.derivative_type == "normalized_text",
                )
            )
        )
        analysis_derivative = db.scalar(
            select(AssetDerivative).where(
                and_(
                    AssetDerivative.asset_id == audio_asset["id"],
                    AssetDerivative.derivative_type == "analysis_json",
                )
            )
        )
        assert normalized_derivative is not None
        assert "对话类型：" in normalized_derivative.content
        assert "识别议题：" in normalized_derivative.content
        assert analysis_derivative is not None
        analysis_payload = json.loads(analysis_derivative.content)
        assert analysis_payload.get("conversation_type")
        assert analysis_payload.get("observed_topics")
    audio_asset_detail = assert_ok(client.get(f"{args.base_url}/assets/{audio_asset['id']}", headers=headers))
    assert audio_asset_detail["derivatives"], audio_asset_detail
    assert any(item["derivative_type"] == "analysis_json" for item in audio_asset_detail["derivatives"])

    reprocess = assert_ok(client.post(f"{args.base_url}/notes/{note_id}/reprocess", headers=headers))
    replay_job_id = reprocess["job_id"]
    replay_job_status = None
    for _ in range(max(1, args.job_timeout_seconds // max(1, args.poll_interval_seconds))):
        replay_job_status = assert_ok(client.get(f"{args.base_url}/jobs/{replay_job_id}", headers=headers))
        if replay_job_status["status"] == "completed":
            break
        time.sleep(args.poll_interval_seconds)
    assert replay_job_status is not None
    assert replay_job_status["status"] == "completed", replay_job_status

    extraction_runs = assert_ok(client.get(f"{args.base_url}/notes/{note_id}/extraction-runs", headers=headers))
    assert extraction_runs["total"] >= 2, extraction_runs
    applied_runs = [item for item in extraction_runs["items"] if item["is_applied"]]
    review_runs = [item for item in extraction_runs["items"] if item["status"] == "ready_for_review"]
    assert len(applied_runs) == 1, extraction_runs
    assert len(review_runs) == 1, extraction_runs
    current_applied_run_id = applied_runs[0]["id"]
    review_run_id = review_runs[0]["id"]
    extraction_run = assert_ok(client.get(f"{args.base_url}/notes/{note_id}/extraction-runs/{review_run_id}", headers=headers))
    assert extraction_run["summary"]["event_count"] >= 1
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
    assert approved["replay_actions"], approved
    extraction_runs_after_approve = assert_ok(client.get(f"{args.base_url}/notes/{note_id}/extraction-runs", headers=headers))
    applied_run_ids = [item["id"] for item in extraction_runs_after_approve["items"] if item["is_applied"]]
    assert applied_run_ids == [review_run_id], extraction_runs_after_approve
    replay_actions = assert_ok(client.get(f"{args.base_url}/notes/{note_id}/replay-actions", headers=headers))
    assert replay_actions["items"], replay_actions
    assert replay_actions["items"][0]["run_id"] == review_run_id
    assert replay_actions["items"][0]["note"] == "审批通过新的抽取草稿，确认草稿审批链路。"

    second_asset = assert_ok(
        client.post(
            f"{args.base_url}/assets/upload",
            headers=headers,
            data={
                "title": "启动会补充记录",
                "asset_type": "text",
                "original_text": "2026-04-19 张三和李四再次记录项目启动会，补充图谱拆分与导入流程。",
            },
        )
    )
    second_note_create = assert_ok(client.post(f"{args.base_url}/notes", headers=headers, json={"asset_id": second_asset["id"]}))
    second_job_id = second_note_create["job_id"]
    second_note_id = second_note_create["note_id"]

    second_job_status = None
    for _ in range(max(1, args.job_timeout_seconds // max(1, args.poll_interval_seconds))):
        second_job_status = assert_ok(client.get(f"{args.base_url}/jobs/{second_job_id}", headers=headers))
        if second_job_status["status"] == "completed":
            break
        time.sleep(args.poll_interval_seconds)
    assert second_job_status is not None
    assert second_job_status["status"] == "completed", second_job_status

    similar = assert_ok(client.get(f"{args.base_url}/search/similar/{second_note_id}", headers=headers))
    assert similar["items"], similar
    unified = assert_ok(
        client.get(
            f"{args.base_url}/search/unified",
            headers=headers,
            params={"q": "启动", "seed_note_id": second_note_id},
        )
    )
    assert unified["notes"], unified
    assert unified["events"], unified
    assert "entities" in unified
    assert "similar_notes" in unified
    merge_candidates = assert_ok(
        client.get(f"{args.base_url}/search/merge-candidates", headers=headers, params={"object_type": "event"})
    )
    assert merge_candidates["items"], merge_candidates
    print("Full e2e passed")


if __name__ == "__main__":
    main()

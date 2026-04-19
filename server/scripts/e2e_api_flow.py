import argparse
import time

import httpx


def assert_ok(response: httpx.Response) -> dict:
    response.raise_for_status()
    payload = response.json()
    assert payload["code"] == 0, payload
    return payload["data"]


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
    assert extraction_runs["items"][0]["is_applied"] is True
    latest_run_id = extraction_runs["items"][0]["id"]
    previous_run_id = extraction_runs["items"][1]["id"]
    extraction_run = assert_ok(client.get(f"{args.base_url}/notes/{note_id}/extraction-runs/{latest_run_id}", headers=headers))
    assert extraction_run["summary"]["event_count"] >= 1
    extraction_compare = assert_ok(
        client.get(
            f"{args.base_url}/notes/{note_id}/extraction-runs/compare",
            headers=headers,
            params={"base_run_id": previous_run_id, "candidate_run_id": latest_run_id},
        )
    )
    assert "summary" in extraction_compare["diff"]
    assert "entities" in extraction_compare["diff"]
    assert extraction_compare["candidate_run"]["id"] == latest_run_id
    applied = assert_ok(
        client.post(
            f"{args.base_url}/notes/{note_id}/extraction-runs/{previous_run_id}/apply",
            headers=headers,
            json={"note": "恢复到上一版提取结果以确认回滚链路。"},
        )
    )
    assert applied["applied_run"]["id"] == previous_run_id
    assert applied["applied_run"]["is_applied"] is True
    assert applied["replay_actions"], applied
    extraction_runs_after_apply = assert_ok(client.get(f"{args.base_url}/notes/{note_id}/extraction-runs", headers=headers))
    applied_run_ids = [item["id"] for item in extraction_runs_after_apply["items"] if item["is_applied"]]
    assert applied_run_ids == [previous_run_id], extraction_runs_after_apply
    replay_actions = assert_ok(client.get(f"{args.base_url}/notes/{note_id}/replay-actions", headers=headers))
    assert replay_actions["items"], replay_actions
    assert replay_actions["items"][0]["run_id"] == previous_run_id
    assert replay_actions["items"][0]["note"] == "恢复到上一版提取结果以确认回滚链路。"

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

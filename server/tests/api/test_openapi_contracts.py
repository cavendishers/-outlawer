from functools import lru_cache

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


@lru_cache
def _openapi() -> dict:
    return client.get("/openapi.json").json()


def _resolve_schema(schema: dict) -> dict:
    openapi = _openapi()
    current = schema
    while "$ref" in current:
        ref = current["$ref"].split("/")[-1]
        current = openapi["components"]["schemas"][ref]
    return current


def _request_schema(path: str, method: str) -> dict:
    openapi = _openapi()
    operation = openapi["paths"][path][method]
    schema = operation["requestBody"]["content"]["application/json"]["schema"]
    if "anyOf" in schema:
        schema = next(item for item in schema["anyOf"] if "$ref" in item)
    return _resolve_schema(schema)


def _response_envelope_schema(path: str, method: str, status_code: str = "200") -> dict:
    openapi = _openapi()
    operation = openapi["paths"][path][method]
    schema = operation["responses"][status_code]["content"]["application/json"]["schema"]
    return _resolve_schema(schema)


def _response_data_schema(path: str, method: str, status_code: str = "200") -> dict:
    envelope_schema = _response_envelope_schema(path, method, status_code=status_code)
    return _resolve_schema(envelope_schema["properties"]["data"])


def test_note_and_replay_endpoints_publish_explicit_request_models() -> None:
    note_schema = _request_schema("/api/v1/notes", "post")
    replay_schema = _request_schema("/api/v1/notes/{note_id}/extraction-runs/{run_id}/apply", "post")
    approve_schema = _request_schema("/api/v1/notes/{note_id}/extraction-runs/{run_id}/approve", "post")
    reject_schema = _request_schema("/api/v1/notes/{note_id}/extraction-runs/{run_id}/reject", "post")

    assert note_schema["additionalProperties"] is False
    assert set(note_schema["properties"]) == {"asset_id", "title"}
    assert note_schema["required"] == ["asset_id"]

    for schema in (replay_schema, approve_schema, reject_schema):
        assert schema["additionalProperties"] is False
        assert set(schema["properties"]) == {"note"}


def test_curation_write_endpoints_publish_explicit_request_models() -> None:
    entity_update = _request_schema("/api/v1/curation/entities/{entity_id}", "patch")
    entity_alias = _request_schema("/api/v1/curation/entities/{entity_id}/aliases", "post")
    entity_relation_create = _request_schema("/api/v1/curation/entities/{entity_id}/relations", "post")
    entity_relation_update = _request_schema("/api/v1/curation/entities/{entity_id}/relations/{relation_id}", "patch")
    event_update = _request_schema("/api/v1/curation/events/{event_id}", "patch")
    participant_create = _request_schema("/api/v1/curation/events/{event_id}/participants", "post")
    event_relation_create = _request_schema("/api/v1/curation/events/{event_id}/relations", "post")
    event_relation_update = _request_schema("/api/v1/curation/events/{event_id}/relations/{relation_id}", "patch")

    assert entity_update["additionalProperties"] is False
    assert set(entity_update["properties"]) == {
        "entity_type",
        "canonical_name",
        "display_name",
        "description",
        "status",
        "first_seen_at",
        "last_seen_at",
    }
    assert entity_alias["required"] == ["alias"]
    assert entity_relation_create["required"] == ["direction", "related_type", "related_id", "relation_type"]
    assert set(entity_relation_update["properties"]) == {"direction", "related_type", "related_id", "relation_type"}

    assert event_update["additionalProperties"] is False
    assert set(event_update["properties"]) == {
        "title",
        "summary",
        "description",
        "event_type",
        "status",
        "start_time",
        "end_time",
        "time_precision",
        "time_text",
        "timeline_sort_time",
        "location_text",
    }
    assert participant_create["required"] == ["entity_id"]
    assert event_relation_create["required"] == ["direction", "related_type", "related_id", "relation_type"]
    assert set(event_relation_update["properties"]) == {"direction", "related_type", "related_id", "relation_type"}


def test_review_write_endpoints_publish_explicit_request_models() -> None:
    reject_schema = _request_schema("/api/v1/review/merge-candidates/{candidate_id}/reject", "post")
    accept_schema = _request_schema("/api/v1/review/merge-candidates/{candidate_id}/accept", "post")
    alias_schema = _request_schema("/api/v1/review/entities/{entity_id}/aliases", "post")

    assert reject_schema["additionalProperties"] is False
    assert set(reject_schema["properties"]) == {"reason", "note"}
    assert accept_schema["additionalProperties"] is False
    assert set(accept_schema["properties"]) == {"resolution", "survivor_id", "note"}
    assert alias_schema["additionalProperties"] is False
    assert alias_schema["required"] == ["alias"]


def test_core_read_endpoints_publish_explicit_response_models() -> None:
    login_schema = _response_data_schema("/api/v1/auth/login", "post")
    asset_list_schema = _response_data_schema("/api/v1/assets", "get")
    asset_detail_schema = _response_data_schema("/api/v1/assets/{asset_id}", "get")
    job_detail_schema = _response_data_schema("/api/v1/jobs/{job_id}", "get")
    entity_detail_schema = _response_data_schema("/api/v1/entities/{entity_id}", "get")
    event_detail_schema = _response_data_schema("/api/v1/events/{event_id}", "get")
    timeline_overview_schema = _response_data_schema("/api/v1/timeline/overview", "get")
    note_schema = _response_data_schema("/api/v1/notes/{note_id}", "get")
    story_schema = _response_data_schema("/api/v1/views/story/note/{note_id}", "get")

    assert set(login_schema["properties"]) == {"access_token", "token_type", "user"}

    assert set(asset_list_schema["properties"]) >= {"items", "total", "page", "page_size", "total_pages"}
    assert set(asset_detail_schema["properties"]) >= {"id", "title", "derivatives", "notes", "raw_url"}
    assert set(job_detail_schema["properties"]) >= {"payload_json", "result_json", "retry_count", "status"}
    assert set(entity_detail_schema["properties"]) >= {"related_events", "timeline_fragments", "display_name"}
    assert set(event_detail_schema["properties"]) >= {"participants", "related_events", "source_note_title"}
    assert set(timeline_overview_schema["properties"]) == {"stats", "nodes", "edges", "timeline_focus"}
    assert set(note_schema["properties"]) >= {"id", "title", "status", "processed_at"}
    assert set(story_schema["properties"]) == {"id", "target_type", "target_id", "title", "content", "style_type"}


def test_note_processing_endpoints_publish_explicit_response_models() -> None:
    run_list_schema = _response_data_schema("/api/v1/notes/{note_id}/extraction-runs", "get")
    run_compare_schema = _response_data_schema("/api/v1/notes/{note_id}/extraction-runs/compare", "get")
    replay_actions_schema = _response_data_schema("/api/v1/notes/{note_id}/replay-actions", "get")
    apply_schema = _response_data_schema("/api/v1/notes/{note_id}/extraction-runs/{run_id}/apply", "post")
    approve_schema = _response_data_schema("/api/v1/notes/{note_id}/extraction-runs/{run_id}/approve", "post")
    reject_schema = _response_data_schema("/api/v1/notes/{note_id}/extraction-runs/{run_id}/reject", "post")
    reprocess_schema = _response_data_schema("/api/v1/notes/{note_id}/reprocess", "post")

    assert set(run_list_schema["properties"]) == {"items", "total"}
    assert set(run_compare_schema["properties"]) == {"note_id", "base_run", "candidate_run", "diff"}
    assert set(replay_actions_schema["properties"]) == {"items", "total"}
    assert set(apply_schema["properties"]) == {"note", "applied_run", "projection_result", "replay_actions"}
    assert set(approve_schema["properties"]) == {"note", "approved_run", "projection_result", "replay_actions"}
    assert set(reject_schema["properties"]) == {"note", "rejected_run", "replay_actions"}
    assert set(reprocess_schema["properties"]) == {"note_id", "job_id"}

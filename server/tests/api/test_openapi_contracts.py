from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _request_schema(path: str, method: str) -> dict:
    openapi = client.get("/openapi.json").json()
    operation = openapi["paths"][path][method]
    schema = operation["requestBody"]["content"]["application/json"]["schema"]
    if "anyOf" in schema:
        schema = next(item for item in schema["anyOf"] if "$ref" in item)
    if "$ref" in schema:
        ref = schema["$ref"].split("/")[-1]
        return openapi["components"]["schemas"][ref]
    return schema


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

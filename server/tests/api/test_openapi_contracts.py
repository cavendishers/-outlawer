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


def test_image_generation_endpoints_publish_explicit_models() -> None:
    create_schema = _request_schema("/api/v1/image-generations", "post")
    create_response = _response_data_schema("/api/v1/image-generations", "post")
    list_response = _response_data_schema("/api/v1/image-generations", "get")
    detail_response = _response_data_schema("/api/v1/image-generations/{generation_id}", "get")

    assert create_schema["additionalProperties"] is False
    assert create_schema["required"] == ["prompt"]
    assert set(create_schema["properties"]) == {"prompt", "model", "aspect_ratio", "image_size", "reference_asset_ids"}
    assert set(create_response["properties"]) == {"generation_id", "job_id", "status"}
    assert set(list_response["properties"]) >= {"items", "total", "page", "page_size", "total_pages"}
    assert set(detail_response["properties"]) >= {
        "id",
        "job_id",
        "status",
        "prompt",
        "model_name",
        "aspect_ratio",
        "image_size",
        "reference_asset_ids",
        "result_asset_ids",
        "result_assets",
    }


def test_character_card_endpoints_publish_explicit_models() -> None:
    create_schema = _request_schema("/api/v1/character-cards/from-entity/{entity_id}", "post")
    update_schema = _request_schema("/api/v1/character-cards/{card_id}", "patch")
    regenerate_schema = _request_schema("/api/v1/character-cards/{card_id}/regenerate", "post")
    avatar_schema = _request_schema("/api/v1/character-cards/{card_id}/generate-avatar", "post")
    role_image_schema = _request_schema("/api/v1/character-cards/{card_id}/generate-role-image", "post")
    create_response = _response_data_schema("/api/v1/character-cards/from-entity/{entity_id}", "post")
    avatar_response = _response_data_schema("/api/v1/character-cards/{card_id}/generate-avatar", "post")
    role_image_response = _response_data_schema("/api/v1/character-cards/{card_id}/generate-role-image", "post")
    list_response = _response_data_schema("/api/v1/character-cards", "get")
    detail_response = _response_data_schema("/api/v1/character-cards/{card_id}", "get")

    assert create_schema["additionalProperties"] is False
    assert set(create_schema["properties"]) == {
        "mode",
        "include_story_view",
        "include_character_book",
        "style",
        "language",
    }
    assert update_schema["additionalProperties"] is False
    assert set(update_schema["properties"]) == {"title", "status", "spec_json"}
    assert regenerate_schema["additionalProperties"] is False
    assert avatar_schema["additionalProperties"] is False
    assert set(avatar_schema["properties"]) == {"model", "aspect_ratio", "image_size"}
    assert role_image_schema["additionalProperties"] is False
    assert set(role_image_schema["properties"]) == {"model", "aspect_ratio", "image_size"}
    assert set(create_response["properties"]) == {"card"}
    assert set(avatar_response["properties"]) == {"card", "generation_id", "job_id", "status"}
    assert set(role_image_response["properties"]) == {"card", "generation_id", "job_id", "status"}
    assert set(list_response["properties"]) >= {"items", "total", "page", "page_size", "total_pages"}
    assert set(detail_response["properties"]) >= {
        "id",
        "source_entity_id",
        "status",
        "title",
        "card_format",
        "card_version",
        "mode",
        "spec_json",
        "source_snapshot_json",
        "avatar_url",
        "role_image_url",
    }


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
    assert "required" not in participant_create
    assert set(participant_create["properties"]) == {"entity_id", "entity_name", "entity_type", "role", "relation_type"}
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
    assert set(note_schema["properties"]) >= {"id", "title", "status", "processed_at", "active_projection_id"}
    assert set(story_schema["properties"]) == {"id", "target_type", "target_id", "title", "content", "style_type"}


def test_note_processing_endpoints_publish_explicit_response_models() -> None:
    run_list_schema = _response_data_schema("/api/v1/notes/{note_id}/extraction-runs", "get")
    analysis_workflow_schema = _response_data_schema("/api/v1/notes/{note_id}/analysis-workflow", "get")
    run_compare_schema = _response_data_schema("/api/v1/notes/{note_id}/extraction-runs/compare", "get")
    replay_actions_schema = _response_data_schema("/api/v1/notes/{note_id}/replay-actions", "get")
    apply_schema = _response_data_schema("/api/v1/notes/{note_id}/extraction-runs/{run_id}/apply", "post")
    approve_schema = _response_data_schema("/api/v1/notes/{note_id}/extraction-runs/{run_id}/approve", "post")
    reject_schema = _response_data_schema("/api/v1/notes/{note_id}/extraction-runs/{run_id}/reject", "post")
    reprocess_schema = _response_data_schema("/api/v1/notes/{note_id}/reprocess", "post")
    story_regenerate_schema = _response_data_schema("/api/v1/notes/{note_id}/story/regenerate", "post")

    assert set(run_list_schema["properties"]) == {"items", "total"}
    assert set(analysis_workflow_schema["properties"]) == {
        "note",
        "asset",
        "active_run_id",
        "latest_run_id",
        "active_projection_id",
        "stats",
        "steps",
        "jobs",
        "derivatives",
        "runs",
        "projections",
        "evidence_groups",
        "raw_normalized_diff",
        "replay_actions",
    }
    assert set(run_compare_schema["properties"]) == {"note_id", "base_run", "candidate_run", "diff"}
    assert set(replay_actions_schema["properties"]) == {"items", "total"}
    assert set(apply_schema["properties"]) == {"note", "applied_run", "projection_result", "replay_actions"}
    assert set(approve_schema["properties"]) == {"note", "approved_run", "projection_result", "replay_actions"}
    assert set(reject_schema["properties"]) == {"note", "rejected_run", "replay_actions"}
    assert set(reprocess_schema["properties"]) == {"note_id", "job_id"}
    assert set(story_regenerate_schema["properties"]) == {"note_id", "story_view", "run_id"}

    run_item_schema = _resolve_schema(run_list_schema["properties"]["items"]["items"])
    replay_action_item_schema = _resolve_schema(replay_actions_schema["properties"]["items"]["items"])
    workflow_step_schema = _resolve_schema(analysis_workflow_schema["properties"]["steps"]["items"])
    workflow_run_schema = _resolve_schema(analysis_workflow_schema["properties"]["runs"]["items"])
    projection_result_schema = _resolve_schema(apply_schema["properties"]["projection_result"])

    assert set(run_item_schema["properties"]) >= {
        "provider_name",
        "model_name",
        "prompt_version",
        "schema_version",
        "input_hash",
        "parent_run_id",
        "run_kind",
        "projection_status",
    }
    assert set(replay_action_item_schema["properties"]) >= {
        "projection_version_id",
        "previous_projection_version_id",
        "provider_name",
        "model_name",
        "prompt_version",
        "schema_version",
    }
    assert set(workflow_step_schema["properties"]) >= {"step_key", "status", "summary", "evidence", "output_refs"}
    assert set(workflow_run_schema["properties"]) >= {"raw_result_json", "normalized_result_json"}
    evidence_group_schema = _resolve_schema(analysis_workflow_schema["properties"]["evidence_groups"]["items"])
    evidence_sample_schema = _resolve_schema(evidence_group_schema["properties"]["samples"]["items"])
    assert set(evidence_group_schema["properties"]) >= {
        "target_label",
        "target_subtitle",
        "detail_href",
        "curation_href",
        "graph_href",
    }
    assert set(evidence_sample_schema["properties"]) >= {"context_before", "context_after"}
    assert set(projection_result_schema["properties"]) >= {"projection_version_id"}


def test_search_endpoints_publish_explicit_response_models() -> None:
    search_schema = _response_data_schema("/api/v1/search", "get")
    unified_schema = _response_data_schema("/api/v1/search/unified", "get")
    similar_schema = _response_data_schema("/api/v1/search/similar/{note_id}", "get")
    merge_candidates_schema = _response_data_schema("/api/v1/search/merge-candidates", "get")

    assert set(search_schema["properties"]) == {"items"}
    assert set(unified_schema["properties"]) == {
        "query",
        "seed_note_id",
        "seed_note_title",
        "top_hits",
        "notes",
        "entities",
        "events",
        "similar_notes",
        "stats",
    }
    assert set(similar_schema["properties"]) == {"items"}
    assert set(merge_candidates_schema["properties"]) == {"items"}


def test_review_endpoints_publish_explicit_response_models() -> None:
    list_schema = _response_data_schema("/api/v1/review/merge-candidates", "get")
    detail_schema = _response_data_schema("/api/v1/review/merge-candidates/{candidate_id}", "get")
    reject_schema = _response_data_schema("/api/v1/review/merge-candidates/{candidate_id}/reject", "post")
    accept_schema = _response_data_schema("/api/v1/review/merge-candidates/{candidate_id}/accept", "post")
    entity_context_schema = _response_data_schema("/api/v1/review/entities/{entity_id}/context", "get")
    alias_schema = _response_data_schema("/api/v1/review/entities/{entity_id}/aliases", "post")
    event_context_schema = _response_data_schema("/api/v1/review/events/{event_id}/context", "get")

    assert set(list_schema["properties"]) >= {"items", "total", "page", "page_size", "total_pages"}
    assert set(detail_schema["properties"]) >= {
        "id",
        "object_type",
        "status",
        "score",
        "reason",
        "source",
        "candidate",
        "can_accept",
        "can_reject",
    }
    assert set(reject_schema["properties"]) == {"candidate_id", "status"}
    assert set(accept_schema["properties"]) == {"candidate_id", "status", "resolution", "survivor_id", "merged_id"}
    assert set(entity_context_schema["properties"]) == {"entity", "aliases", "stats", "timeline_fragments", "candidates"}
    assert set(alias_schema["properties"]) == {"entity_id", "aliases"}
    assert set(event_context_schema["properties"]) == {"event", "stats", "candidates"}


def test_curation_endpoints_publish_explicit_response_models() -> None:
    entity_context_schema = _response_data_schema("/api/v1/curation/entities/{entity_id}", "get")
    entity_update_schema = _response_data_schema("/api/v1/curation/entities/{entity_id}", "patch")
    entity_alias_add_schema = _response_data_schema("/api/v1/curation/entities/{entity_id}/aliases", "post")
    entity_alias_remove_schema = _response_data_schema("/api/v1/curation/entities/{entity_id}/aliases/{alias_id}", "delete")
    entity_relation_schema = _response_data_schema("/api/v1/curation/entities/{entity_id}/relations", "post")
    entity_relation_remove_schema = _response_data_schema("/api/v1/curation/entities/{entity_id}/relations/{relation_id}", "delete")
    event_context_schema = _response_data_schema("/api/v1/curation/events/{event_id}", "get")
    event_update_schema = _response_data_schema("/api/v1/curation/events/{event_id}", "patch")
    participant_add_schema = _response_data_schema("/api/v1/curation/events/{event_id}/participants", "post")
    participant_remove_schema = _response_data_schema("/api/v1/curation/events/{event_id}/participants/{entity_id}", "delete")
    event_relation_schema = _response_data_schema("/api/v1/curation/events/{event_id}/relations", "post")
    event_relation_remove_schema = _response_data_schema("/api/v1/curation/events/{event_id}/relations/{relation_id}", "delete")

    assert set(entity_context_schema["properties"]) == {"entity", "aliases", "related_events", "relations", "timeline_fragments", "stats"}
    assert set(entity_update_schema["properties"]) >= {"id", "display_name", "entity_type", "status"}
    assert set(entity_alias_add_schema["properties"]) == {"id", "alias", "normalized_alias", "alias_type", "created_at"}
    assert set(entity_alias_remove_schema["properties"]) == {"entity_id", "alias_id", "status"}
    assert set(entity_relation_schema["properties"]) >= {"id", "direction", "relation_type", "peer"}
    assert set(entity_relation_remove_schema["properties"]) == {"relation_id", "status"}
    assert set(event_context_schema["properties"]) == {"event", "participants", "relations", "stats"}
    assert set(event_update_schema["properties"]) >= {"id", "title", "time_precision", "source_note_title"}
    assert set(participant_add_schema["properties"]) == {"event_id", "entity_id", "role", "relation_type"}
    assert set(participant_remove_schema["properties"]) == {"event_id", "entity_id", "status"}
    assert set(event_relation_schema["properties"]) >= {"id", "direction", "relation_type", "peer"}
    assert set(event_relation_remove_schema["properties"]) == {"relation_id", "status"}


def test_graph_workspace_endpoint_publishes_explicit_response_model() -> None:
    graph_workspace_schema = _response_data_schema("/api/v1/graph/workspace", "get")
    graph_node_detail_schema = _response_data_schema("/api/v1/graph/nodes/{node_type}/{node_id}", "get")
    graph_viewpoint_create_schema = _request_schema("/api/v1/graph-viewpoints", "post")
    graph_viewpoint_update_schema = _request_schema("/api/v1/graph-viewpoints/{viewpoint_id}", "patch")
    graph_viewpoint_delete_schema = _response_data_schema("/api/v1/graph-viewpoints/{viewpoint_id}", "delete")
    graph_viewpoint_list_schema = _response_data_schema("/api/v1/graph-viewpoints", "get")
    graph_viewpoint_create_response_schema = _response_data_schema("/api/v1/graph-viewpoints", "post")
    graph_path_schema = _response_data_schema("/api/v1/graph/path", "get")
    conflict_disposition_schema = _request_schema("/api/v1/graph/conflicts/{conflict_id}/disposition", "post")

    assert set(graph_workspace_schema["properties"]) == {
        "scope",
        "title",
        "description",
        "anchor",
        "nodes",
        "edges",
        "timeline_focus",
        "stats",
        "filters",
        "conflicts",
        "recent_actions",
    }
    stats_schema = _resolve_schema(graph_workspace_schema["properties"]["stats"])
    edge_schema = _resolve_schema(graph_workspace_schema["properties"]["edges"]["items"])
    conflict_schema = _resolve_schema(graph_workspace_schema["properties"]["conflicts"]["items"])
    action_log_schema = _resolve_schema(graph_workspace_schema["properties"]["recent_actions"]["items"])
    assert set(stats_schema["properties"]) >= {
        "conflict_count",
        "low_confidence_edge_count",
        "orphan_node_count",
    }
    assert set(graph_node_detail_schema["properties"]) == {
        "node",
        "connected_nodes",
        "connected_edges",
        "timeline_context",
        "anchor_actions",
    }
    assert set(edge_schema["properties"]) >= {
        "id",
        "relation_id",
        "fact_type",
        "source_type",
        "target_type",
        "evidence_count",
        "is_editable",
    }
    assert set(conflict_schema["properties"]) >= {"actions", "disposition", "disposition_note", "is_active"}
    assert "diff_summary" in action_log_schema["properties"]
    assert graph_viewpoint_create_schema["additionalProperties"] is False
    assert set(graph_viewpoint_create_schema["properties"]) == {
        "name",
        "description",
        "scope",
        "anchor_type",
        "anchor_id",
        "filters_json",
        "layout_json",
    }
    assert graph_viewpoint_create_schema["required"] == ["name"]
    assert set(graph_viewpoint_list_schema["properties"]) >= {"items", "total"}
    assert set(graph_viewpoint_create_response_schema["properties"]) >= {
        "id",
        "name",
        "scope",
        "filters_json",
        "layout_json",
        "href",
    }
    assert graph_viewpoint_update_schema["additionalProperties"] is False
    assert set(graph_viewpoint_update_schema["properties"]) == {"name", "description"}
    assert set(graph_viewpoint_delete_schema["properties"]) == {"id", "status"}
    assert set(graph_path_schema["properties"]) == {
        "found",
        "max_depth",
        "total_hops",
        "source",
        "target",
        "nodes",
        "edges",
        "explanation",
    }
    assert conflict_disposition_schema["additionalProperties"] is False
    assert set(conflict_disposition_schema["properties"]) == {
        "disposition",
        "note",
        "conflict_type",
        "title",
        "summary",
        "node_ids",
        "edge_label",
    }


def test_manual_authoring_endpoints_publish_explicit_contracts() -> None:
    entity_create = _request_schema("/api/v1/entities", "post")
    event_create = _request_schema("/api/v1/events", "post")
    graph_create = _request_schema("/api/v1/graph/manual-nodes", "post")
    evidence_create = _request_schema("/api/v1/manual-knowledge/evidence", "post")
    graph_response = _response_data_schema("/api/v1/graph/manual-nodes", "post", status_code="201")

    assert entity_create["additionalProperties"] is False
    assert set(entity_create["required"]) == {"canonical_name"}
    assert event_create["additionalProperties"] is False
    assert set(event_create["required"]) == {"title"}
    assert graph_create["additionalProperties"] is False
    assert set(graph_create["required"]) == {"node_type", "name", "anchor_type", "anchor_id"}
    assert evidence_create["additionalProperties"] is False
    assert set(evidence_create["required"]) >= {"target_type", "target_id"}
    assert set(graph_response["properties"]) == {
        "node_type",
        "node_id",
        "label",
        "connection_type",
        "connection_id",
        "evidence",
        "graph_href",
    }


def test_collection_endpoints_publish_explicit_contracts() -> None:
    create_schema = _request_schema("/api/v1/collections", "post")
    detail_schema = _response_data_schema("/api/v1/collections/{collection_id}", "get")
    item_schema = _request_schema("/api/v1/collections/{collection_id}/items", "post")
    story_schema = _request_schema("/api/v1/collections/{collection_id}/story", "put")
    timeline_schema = _response_data_schema("/api/v1/collections/{collection_id}/timeline", "get")
    export_schema = _response_data_schema("/api/v1/collections/{collection_id}/export", "get")
    candidate_schema = _response_data_schema("/api/v1/collections/{collection_id}/candidates", "get")
    order_schema = _request_schema("/api/v1/collections/{collection_id}/items/order", "put")
    bulk_remove_schema = _request_schema("/api/v1/collections/{collection_id}/items/bulk-remove", "post")
    evidence_list_schema = _response_data_schema("/api/v1/manual-knowledge/evidence", "get")

    assert create_schema["additionalProperties"] is False
    assert create_schema["required"] == ["title"]
    assert set(detail_schema["properties"]) >= {"id", "title", "items", "story", "item_count"}
    assert item_schema["additionalProperties"] is False
    assert set(item_schema["required"]) == {"item_type", "item_id"}
    assert story_schema["additionalProperties"] is False
    assert set(timeline_schema["properties"]) == {"collection_id", "items"}
    assert set(export_schema["properties"]) == {"format", "filename", "mime_type", "content"}
    assert set(candidate_schema["properties"]) >= {"items", "total", "page", "page_size"}
    assert order_schema["additionalProperties"] is False and order_schema["required"] == ["item_ids"]
    assert bulk_remove_schema["additionalProperties"] is False and bulk_remove_schema["required"] == ["item_ids"]
    assert set(evidence_list_schema["properties"]) == {"items", "total"}


def test_operations_overview_endpoint_publishes_explicit_response_model() -> None:
    operations_schema = _response_data_schema("/api/v1/operations/overview", "get")

    assert set(operations_schema["properties"]) == {
        "jobs",
        "assets",
        "review",
        "extraction",
        "activity",
        "graph_quality",
    }

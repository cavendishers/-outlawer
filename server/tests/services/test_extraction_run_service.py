from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.domains.retrieval.note_query import (
    get_note_analysis_workflow,
    resolve_evidence_target_labels,
    resolve_relation_evidence_contexts,
)
from app.models.ai_job import AIJob
from app.models.asset_derivative import AssetDerivative
from app.models.entity import Entity, Relation
from app.models.event import Event
from app.models.extraction import ExtractionEvidence, ExtractionRun, ProjectionVersion
from app.models.note import Note
from app.models.raw_asset import RawAsset
from app.models.review import ReviewAction
from app.models.style_view import StyleView
from app.models.user import User
from app.domains.replay.service import (
    RUN_STATUS_READY_FOR_REVIEW,
    RUN_STATUS_REJECTED,
    compare_extraction_payloads,
    resolve_applied_run_id,
    serialize_replay_action,
    serialize_extraction_run,
    summarize_run_payload,
)


def test_compare_extraction_payloads_detects_summary_entity_and_event_changes() -> None:
    base_payload = {
        "summary": {
            "title": "项目启动会议",
            "short_summary": "张三和李四讨论图谱导入。",
            "canonical_text": "2026-04-18 张三和李四在会议室A召开项目启动会。",
            "category": "knowledge",
            "tags": ["启动会"],
        },
        "entities": [
            {
                "entity_type": "person",
                "canonical_name": "张三",
                "aliases": [],
                "description": "参与者",
                "confidence": 0.75,
            }
        ],
        "events": [
            {
                "title": "项目启动会议",
                "event_type": "meeting",
                "summary": "讨论图谱导入。",
                "time": {"time_text": "2026-04-18", "timeline_sort_time": "2026-04-18T00:00:00+00:00"},
                "participants": [{"entity_temp_id": "ent_1"}],
                "locations": [{"name": "会议室A"}],
                "confidence": 0.7,
            }
        ],
        "relations": [
            {
                "source_ref": {"type": "entity", "temp_id": "ent_1"},
                "relation_type": "participates_in",
                "target_ref": {"type": "event", "temp_id": "evt_1"},
                "confidence": 0.75,
            }
        ],
        "similarity_hints": [],
        "style_payload": {
            "title": "命运卷宗：项目启动会议",
            "character_cards": [{"display_name": "张三", "epithet": "事件见证者"}],
            "event_narrative": [{"headline": "序章", "body": "张三留下回响。"}],
        },
    }
    candidate_payload = {
        **base_payload,
        "summary": {
            **base_payload["summary"],
            "title": "项目启动会：图谱导入",
            "tags": ["启动会", "图谱"],
        },
        "entities": [
            *base_payload["entities"],
            {
                "entity_type": "person",
                "canonical_name": "李四",
                "aliases": [],
                "description": "参与者",
                "confidence": 0.78,
            },
        ],
        "events": [
            {
                **base_payload["events"][0],
                "summary": "讨论图谱导入与拆分计划。",
                "participants": [{"entity_temp_id": "ent_1"}, {"entity_temp_id": "ent_2"}],
            }
        ],
    }

    diff = compare_extraction_payloads(base_payload, candidate_payload)

    assert diff["changed"] is True
    assert diff["summary"]["changed"] is True
    assert [item["field"] for item in diff["summary"]["fields"] if item["changed"]] == ["title", "tags"]
    assert diff["entities"]["added"][0]["name"] == "李四"
    assert diff["entities"]["unchanged_count"] == 1
    assert diff["events"]["changed_items"][0]["candidate"]["participant_count"] == 2
    assert diff["relations"]["changed"] is False


def test_compare_extraction_payloads_reports_unchanged_payloads() -> None:
    payload = {
        "summary": {"title": "启动会", "short_summary": "摘要", "canonical_text": "正文", "category": "knowledge", "tags": []},
        "entities": [],
        "events": [],
        "relations": [],
        "similarity_hints": [],
        "style_payload": {"title": "命运卷宗", "character_cards": [], "event_narrative": []},
    }

    diff = compare_extraction_payloads(payload, payload)

    assert diff["changed"] is False
    assert diff["summary"]["changed"] is False
    assert diff["entities"]["base_count"] == 0


def test_summarize_run_payload_counts_core_sections() -> None:
    summary = summarize_run_payload(
        {
            "summary": {"title": "启动会", "category": "knowledge"},
            "entities": [{}, {}],
            "events": [{}],
            "relations": [{}, {}, {}],
            "similarity_hints": [{}],
        }
    )

    assert summary == {
        "title": "启动会",
        "category": "knowledge",
        "entity_count": 2,
        "event_count": 1,
        "relation_count": 3,
        "similarity_hint_count": 1,
    }


def test_resolve_applied_run_id_prefers_explicit_applied_status() -> None:
    now = datetime.now(UTC)
    superseded_run = ExtractionRun(
        id="run-old",
        user_id="user-1",
        note_id="note-1",
        status="superseded",
        extractor_name="heuristic",
        extractor_version="v1",
        created_at=now - timedelta(minutes=5),
        updated_at=now - timedelta(minutes=5),
    )
    applied_run = ExtractionRun(
        id="run-new",
        user_id="user-1",
        note_id="note-1",
        status="applied",
        extractor_name="openrouter",
        extractor_version="v2",
        created_at=now,
        updated_at=now,
    )

    applied_run_id = resolve_applied_run_id([superseded_run, applied_run])
    serialized = serialize_extraction_run(applied_run, applied_run_id=applied_run_id)

    assert applied_run_id == "run-new"
    assert serialized["is_applied"] is True
    assert serialized["projection_status"] == "applied"


def test_resolve_applied_run_id_falls_back_to_latest_successful_run() -> None:
    now = datetime.now(UTC)
    older_run = ExtractionRun(
        id="run-1",
        user_id="user-1",
        note_id="note-1",
        status="completed",
        extractor_name="heuristic",
        extractor_version="v1",
        created_at=now - timedelta(minutes=10),
        updated_at=now - timedelta(minutes=10),
    )
    newer_run = ExtractionRun(
        id="run-2",
        user_id="user-1",
        note_id="note-1",
        status="completed",
        extractor_name="heuristic",
        extractor_version="v1",
        created_at=now,
        updated_at=now,
    )

    applied_run_id = resolve_applied_run_id([older_run, newer_run])

    assert applied_run_id == "run-2"


def test_resolve_applied_run_id_ignores_review_and_rejected_runs() -> None:
    now = datetime.now(UTC)
    applied_run = ExtractionRun(
        id="run-applied",
        user_id="user-1",
        note_id="note-1",
        status="applied",
        extractor_name="heuristic",
        extractor_version="v1",
        created_at=now - timedelta(minutes=10),
        updated_at=now - timedelta(minutes=10),
    )
    review_run = ExtractionRun(
        id="run-review",
        user_id="user-1",
        note_id="note-1",
        status=RUN_STATUS_READY_FOR_REVIEW,
        extractor_name="openrouter",
        extractor_version="v2",
        created_at=now,
        updated_at=now,
    )
    rejected_run = ExtractionRun(
        id="run-rejected",
        user_id="user-1",
        note_id="note-1",
        status=RUN_STATUS_REJECTED,
        extractor_name="openrouter",
        extractor_version="v2",
        created_at=now - timedelta(minutes=1),
        updated_at=now - timedelta(minutes=1),
    )

    applied_run_id = resolve_applied_run_id([review_run, rejected_run, applied_run])

    assert applied_run_id == "run-applied"


def test_serialize_replay_action_preserves_note_and_run_metadata() -> None:
    now = datetime.now(UTC)
    action = ReviewAction(
        id="action-1",
        user_id="user-1",
        target_type="note",
        target_id="note-1",
        action_type="apply_extraction_run",
        status_before="applied",
        status_after="applied",
        payload_json={
            "run_id": "run-2",
            "previous_run_id": "run-1",
            "extractor_name": "openrouter",
            "extractor_version": "v2",
            "note": "回滚到更稳定的实体识别版本。",
        },
        created_at=now,
        updated_at=now,
    )

    serialized = serialize_replay_action(action)

    assert serialized["run_id"] == "run-2"
    assert serialized["previous_run_id"] == "run-1"
    assert serialized["extractor_name"] == "openrouter"
    assert serialized["note"] == "回滚到更稳定的实体识别版本。"


def test_serialize_extraction_run_includes_versioning_metadata() -> None:
    now = datetime.now(UTC)
    run = ExtractionRun(
        id="run-meta",
        user_id="user-1",
        note_id="note-1",
        status="applied",
        extractor_name="openrouter",
        extractor_version="google/gemma-4-31b-it:free",
        provider_name="openrouter",
        model_name="google/gemma-4-31b-it:free",
        prompt_version="text-openrouter-v1",
        schema_version="ai-extraction-format-v1",
        input_hash="abc123",
        parent_run_id="run-parent",
        run_kind="reprocess",
        projection_status="applied",
        created_at=now,
        updated_at=now,
        normalized_result_json={"summary": {"title": "启动会", "category": "knowledge"}},
    )

    serialized = serialize_extraction_run(run, applied_run_id="run-meta")

    assert serialized["provider_name"] == "openrouter"
    assert serialized["model_name"] == "google/gemma-4-31b-it:free"
    assert serialized["prompt_version"] == "text-openrouter-v1"
    assert serialized["schema_version"] == "ai-extraction-format-v1"
    assert serialized["input_hash"] == "abc123"
    assert serialized["parent_run_id"] == "run-parent"
    assert serialized["run_kind"] == "reprocess"
    assert serialized["projection_status"] == "applied"


def test_serialize_replay_action_includes_projection_version_metadata() -> None:
    now = datetime.now(UTC)
    action = ReviewAction(
        id="action-2",
        user_id="user-1",
        target_type="note",
        target_id="note-1",
        action_type="approve_extraction_run",
        status_before="ready_for_review",
        status_after="applied",
        payload_json={
            "run_id": "run-2",
            "previous_run_id": "run-1",
            "projection_version_id": "pv-2",
            "previous_projection_version_id": "pv-1",
            "extractor_name": "openrouter",
            "extractor_version": "google/gemma-4-31b-it:free",
            "provider_name": "openrouter",
            "model_name": "google/gemma-4-31b-it:free",
            "prompt_version": "text-openrouter-v1",
            "schema_version": "ai-extraction-format-v1",
            "note": "批准新版本。",
        },
        created_at=now,
        updated_at=now,
    )

    serialized = serialize_replay_action(action)

    assert serialized["projection_version_id"] == "pv-2"
    assert serialized["previous_projection_version_id"] == "pv-1"
    assert serialized["provider_name"] == "openrouter"
    assert serialized["model_name"] == "google/gemma-4-31b-it:free"
    assert serialized["prompt_version"] == "text-openrouter-v1"
    assert serialized["schema_version"] == "ai-extraction-format-v1"


def test_get_note_analysis_workflow_builds_traceable_pipeline() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    tables = [
        User.__table__,
        RawAsset.__table__,
        AssetDerivative.__table__,
        Note.__table__,
        Entity.__table__,
        ExtractionRun.__table__,
        ProjectionVersion.__table__,
        ExtractionEvidence.__table__,
        StyleView.__table__,
        AIJob.__table__,
        ReviewAction.__table__,
    ]
    Base.metadata.create_all(engine, tables=tables)
    Session = sessionmaker(bind=engine)
    now = datetime.now(UTC)
    payload = {
        "summary": {"title": "启动会", "category": "meeting"},
        "entities": [{"name": "张三"}],
        "events": [{"title": "启动会"}],
        "relations": [{"relation_type": "participates_in"}],
        "similarity_hints": [],
    }

    with Session() as db:
        db.add(User(id="user-1", username="admin", password_hash="hash", display_name="Admin"))
        db.add(
            RawAsset(
                id="asset-1",
                user_id="user-1",
                asset_type="text",
                title="启动会原文",
                original_text="2026-04-18 张三参加启动会。",
                status="uploaded",
                created_at=now,
                updated_at=now,
            )
        )
        db.add(
            AssetDerivative(
                id="derivative-1",
                asset_id="asset-1",
                derivative_type="normalized_text",
                content="2026-04-18 张三参加启动会。",
                meta_json={"parser": "text"},
                created_at=now,
                updated_at=now,
            )
        )
        db.add(
            Note(
                id="note-1",
                user_id="user-1",
                asset_id="asset-1",
                title="启动会",
                status="ready",
                active_projection_id=None,
                canonical_text="2026-04-18 张三参加启动会。",
                created_at=now,
                updated_at=now,
            )
        )
        db.add(
            AIJob(
                id="job-1",
                user_id="user-1",
                job_type="knowledge_pipeline",
                target_type="note",
                target_id="note-1",
                status="completed",
                payload_json={"asset_id": "asset-1"},
                result_json={"run_id": "run-1"},
                created_at=now,
                updated_at=now,
                finished_at=now,
            )
        )
        db.add(
            ExtractionRun(
                id="run-1",
                user_id="user-1",
                note_id="note-1",
                source_asset_id="asset-1",
                raw_result_json=payload,
                normalized_result_json=payload,
                status="applied",
                extractor_name="deepseek",
                extractor_version="v1",
                provider_name="deepseek",
                model_name="deepseek-v4-pro",
                prompt_version="text-llm-v1",
                schema_version="ai-extraction-format-v1",
                input_hash="hash-1",
                projection_status="applied",
                created_at=now,
                updated_at=now,
            )
        )
        db.add(
            Entity(
                id="entity-1",
                user_id="user-1",
                entity_type="person",
                canonical_name="张三",
                display_name="张三",
                alias_json=[],
                normalized_name="张三",
                status="active",
                created_at=now,
                updated_at=now,
            )
        )
        db.add(
            ReviewAction(
                id="action-1",
                user_id="user-1",
                target_type="note",
                target_id="note-1",
                action_type="auto_apply_extraction_run",
                status_after="applied",
                payload_json={
                    "run_id": "run-1",
                    "extractor_name": "deepseek",
                    "extractor_version": "v1",
                    "provider_name": "deepseek",
                    "model_name": "deepseek-v4-pro",
                    "schema_version": "ai-extraction-format-v1",
                    "note": "自动应用。",
                },
                created_at=now,
                updated_at=now,
            )
        )
        db.add(
            ExtractionEvidence(
                id="evidence-1",
                user_id="user-1",
                source_note_id="note-1",
                source_asset_id="asset-1",
                target_type="entity",
                target_id="entity-1",
                field_name="canonical_name",
                evidence_text="张三参加启动会",
                evidence_offset_start=11,
                evidence_offset_end=18,
                extractor_name="deepseek",
                extractor_version="v1",
                confidence_score=0.82,
                created_at=now,
                updated_at=now,
            )
        )
        db.commit()

        workflow = get_note_analysis_workflow(db, user_id="user-1", note_id="note-1")

    assert workflow["note"]["id"] == "note-1"
    assert workflow["asset"]["id"] == "asset-1"
    assert workflow["stats"]["job_count"] == 1
    assert workflow["stats"]["derivative_count"] == 1
    assert workflow["stats"]["run_count"] == 1
    assert workflow["stats"]["replay_action_count"] == 1
    assert workflow["stats"]["evidence_count"] == 1
    assert workflow["evidence_groups"][0]["target_type"] == "entity"
    assert workflow["evidence_groups"][0]["target_label"] == "张三"
    assert workflow["evidence_groups"][0]["detail_href"] == "/story/entity/entity-1"
    assert workflow["evidence_groups"][0]["curation_href"] == "/curation/entities/entity-1"
    assert workflow["evidence_groups"][0]["graph_href"] == "/graph?entity_id=entity-1"
    assert workflow["evidence_groups"][0]["evidence_count"] == 1
    assert workflow["evidence_groups"][0]["average_confidence"] == 0.82
    assert workflow["evidence_groups"][0]["samples"][0]["evidence_text"] == "张三参加启动会"
    assert workflow["evidence_groups"][0]["samples"][0]["context_before"] == "2026-04-18 "
    assert workflow["evidence_groups"][0]["samples"][0]["context_after"] == "。"
    assert workflow["raw_normalized_diff"]["changed"] is False
    assert [step["step_key"] for step in workflow["steps"]] == [
        "raw_asset",
        "text_preparation",
        "knowledge_extraction",
        "projection",
        "review_governance",
        "story_rendering",
    ]
    assert workflow["runs"][0]["raw_result_json"]["summary"]["title"] == "启动会"
    assert workflow["steps"][2]["model_name"] == "deepseek-v4-pro"


def test_relation_evidence_resolves_first_class_relation_id() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[User.__table__, Entity.__table__, Event.__table__, Relation.__table__],
    )
    Session = sessionmaker(bind=engine)
    with Session() as db:
        db.add(User(id="user-rel", username="relation-user", password_hash="hash", display_name="Relation User"))
        db.add(
            Entity(
                id="entity-rel",
                user_id="user-rel",
                entity_type="person",
                canonical_name="张三",
                display_name="张三",
                alias_json=[],
                normalized_name="张三",
                status="active",
            )
        )
        db.add(
            Event(
                id="event-rel",
                user_id="user-rel",
                title="启动会",
                status="active",
                time_precision="day",
            )
        )
        db.add(
            Relation(
                id="relation-rel",
                user_id="user-rel",
                source_type="entity",
                source_id="entity-rel",
                relation_type="supports",
                target_type="event",
                target_id="event-rel",
                evidence_count=1,
                meta_json={"source": "llm_relation"},
            )
        )
        db.commit()
        evidence = ExtractionEvidence(
            user_id="user-rel",
            target_type="relation",
            target_id="relation-rel",
            field_name="supports",
        )

        labels = resolve_evidence_target_labels(db, [evidence])
        contexts = resolve_relation_evidence_contexts(db, [evidence])

    assert labels[("relation", "relation-rel")] == "张三 -supports-> 启动会"
    assert contexts[("relation", "relation-rel")] == {
        "relation_id": "relation-rel",
        "relation_type": "supports",
        "owner_type": "entity",
        "owner_id": "entity-rel",
        "curation_href": "/curation/entities/entity-rel",
        "graph_href": "/graph?entity_id=entity-rel&active_node_id=entity-rel",
    }

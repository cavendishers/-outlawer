from __future__ import annotations

from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.serializers import serialize_note
from app.core.pagination import PageParams, paginate_query
from app.models.ai_job import AIJob
from app.models.asset_derivative import AssetDerivative
from app.models.entity import Entity, Relation
from app.models.event import Event
from app.models.extraction import ExtractionEvidence, ProjectionVersion
from app.domains.replay.service import (
    compare_extraction_payloads,
    compare_extraction_runs,
    get_extraction_run,
    list_extraction_runs,
    list_note_replay_actions,
    resolve_applied_run_id,
    serialize_extraction_run,
    serialize_replay_action,
)
from app.models.note import Note
from app.models.raw_asset import RawAsset
from app.models.style_view import StyleView


def get_owned_note(db: Session, *, user_id: str, note_id: str) -> Note:
    note = db.get(Note, note_id)
    if note is None or note.user_id != user_id:
        raise ValueError("Note not found")
    return note


def list_notes(db: Session, *, user_id: str, params: PageParams) -> tuple[list[dict[str, Any]], int]:
    query = select(Note).where(Note.user_id == user_id).order_by(Note.created_at.desc())
    notes, total = paginate_query(db, query, params)
    return [serialize_note(note) for note in notes], total


def get_note_detail(db: Session, *, user_id: str, note_id: str) -> dict[str, Any]:
    note = get_owned_note(db, user_id=user_id, note_id=note_id)
    return serialize_note(note)


def list_note_extraction_run_items(db: Session, *, user_id: str, note_id: str) -> dict[str, Any]:
    note = get_owned_note(db, user_id=user_id, note_id=note_id)
    runs = list_extraction_runs(db, user_id=user_id, note_id=note.id)
    applied_run_id = resolve_applied_run_id(runs)
    return {
        "items": [serialize_extraction_run(run, applied_run_id=applied_run_id) for run in runs],
        "total": len(runs),
    }


def compare_note_extraction_runs(
    db: Session,
    *,
    user_id: str,
    note_id: str,
    base_run_id: str,
    candidate_run_id: str,
) -> dict[str, Any]:
    note = get_owned_note(db, user_id=user_id, note_id=note_id)
    base_run = get_extraction_run(db, user_id=user_id, note_id=note.id, run_id=base_run_id)
    candidate_run = get_extraction_run(db, user_id=user_id, note_id=note.id, run_id=candidate_run_id)
    if not base_run or not candidate_run:
        raise ValueError("Extraction run not found")
    applied_run_id = resolve_applied_run_id(list_extraction_runs(db, user_id=user_id, note_id=note.id))
    return compare_extraction_runs(base_run, candidate_run, applied_run_id=applied_run_id)


def get_note_extraction_run_detail(db: Session, *, user_id: str, note_id: str, run_id: str) -> dict[str, Any]:
    note = get_owned_note(db, user_id=user_id, note_id=note_id)
    run = get_extraction_run(db, user_id=user_id, note_id=note.id, run_id=run_id)
    if not run:
        raise ValueError("Extraction run not found")
    applied_run_id = resolve_applied_run_id(list_extraction_runs(db, user_id=user_id, note_id=note.id))
    return serialize_extraction_run(run, applied_run_id=applied_run_id)


def get_note_analysis_workflow(db: Session, *, user_id: str, note_id: str) -> dict[str, Any]:
    note = get_owned_note(db, user_id=user_id, note_id=note_id)
    asset = db.get(RawAsset, note.asset_id) if note.asset_id else None
    derivatives = (
        list(
            db.scalars(
                select(AssetDerivative)
                .where(AssetDerivative.asset_id == asset.id)
                .order_by(AssetDerivative.created_at.asc())
            ).all()
        )
        if asset
        else []
    )
    jobs = list(
        db.scalars(
            select(AIJob)
            .where(
                AIJob.user_id == user_id,
                AIJob.target_type == "note",
                AIJob.target_id == note.id,
            )
            .order_by(AIJob.created_at.asc())
        ).all()
    )
    runs = list(reversed(list_extraction_runs(db, user_id=user_id, note_id=note.id)))
    applied_run_id = resolve_applied_run_id(runs)
    projections = list(
        db.scalars(
            select(ProjectionVersion)
            .where(ProjectionVersion.user_id == user_id, ProjectionVersion.note_id == note.id)
            .order_by(ProjectionVersion.created_at.asc())
        ).all()
    )
    story_views = list(
        db.scalars(
            select(StyleView)
            .where(
                StyleView.user_id == user_id,
                StyleView.target_type == "note",
                StyleView.target_id == note.id,
            )
            .order_by(StyleView.updated_at.desc())
        ).all()
    )
    replay_actions = list_note_replay_actions(db, user_id=user_id, note_id=note.id, limit=50)
    evidence_count = int(
        db.scalar(
            select(func.count())
            .select_from(ExtractionEvidence)
            .where(ExtractionEvidence.user_id == user_id, ExtractionEvidence.source_note_id == note.id)
        )
        or 0
    )
    evidence_items = list(
        db.scalars(
            select(ExtractionEvidence)
            .where(ExtractionEvidence.user_id == user_id, ExtractionEvidence.source_note_id == note.id)
            .order_by(ExtractionEvidence.created_at.desc())
        ).all()
    )
    evidence_samples = [
        item.evidence_text
        for item in evidence_items[:5]
    ]
    latest_run = runs[-1] if runs else None
    active_run = next((run for run in runs if run.id == applied_run_id), latest_run)
    raw_normalized_diff = (
        compare_extraction_payloads(active_run.raw_result_json or {}, active_run.normalized_result_json or {})
        if active_run
        else empty_extraction_diff()
    )

    return {
        "note": serialize_note(note),
        "asset": serialize_analysis_asset(asset) if asset else None,
        "active_run_id": applied_run_id,
        "latest_run_id": latest_run.id if latest_run else None,
        "active_projection_id": note.active_projection_id,
        "stats": {
            "job_count": len(jobs),
            "derivative_count": len(derivatives),
            "run_count": len(runs),
            "projection_count": len(projections),
            "replay_action_count": len(replay_actions),
            "evidence_count": evidence_count,
        },
        "steps": build_analysis_steps(
            note=note,
            asset=asset,
            derivatives=derivatives,
            jobs=jobs,
            active_run=active_run,
            projections=projections,
            story_views=story_views,
            replay_actions=replay_actions,
            evidence_samples=evidence_samples,
        ),
        "jobs": [serialize_analysis_job(job) for job in jobs],
        "derivatives": [serialize_analysis_derivative(derivative) for derivative in derivatives],
        "runs": [serialize_analysis_run(run, applied_run_id=applied_run_id) for run in runs],
        "projections": [serialize_analysis_projection(projection) for projection in projections],
        "evidence_groups": build_evidence_groups(db, evidence_items, source_text=get_evidence_context_source(asset, derivatives)),
        "raw_normalized_diff": raw_normalized_diff,
        "replay_actions": [serialize_replay_action(action) for action in replay_actions],
    }


def list_note_replay_action_items(db: Session, *, user_id: str, note_id: str) -> dict[str, Any]:
    note = get_owned_note(db, user_id=user_id, note_id=note_id)
    actions = list_note_replay_actions(db, user_id=user_id, note_id=note.id)
    return {"items": [serialize_replay_action(action) for action in actions], "total": len(actions)}


def serialize_analysis_asset(asset: RawAsset) -> dict[str, Any]:
    return {
        "id": asset.id,
        "asset_type": asset.asset_type,
        "title": asset.title,
        "status": asset.status,
        "mime_type": asset.mime_type,
        "file_size": asset.file_size,
        "original_text_preview": truncate_text(asset.original_text),
        "created_at": serialize_dt(asset.created_at),
    }


def serialize_analysis_derivative(derivative: AssetDerivative) -> dict[str, Any]:
    return {
        "id": derivative.id,
        "derivative_type": derivative.derivative_type,
        "version": derivative.version,
        "content_preview": truncate_text(derivative.content, limit=800) or "",
        "meta_json": derivative.meta_json or {},
        "created_at": serialize_dt(derivative.created_at),
        "updated_at": serialize_dt(derivative.updated_at),
    }


def serialize_analysis_job(job: AIJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "job_type": job.job_type,
        "status": job.status,
        "target_type": job.target_type,
        "target_id": job.target_id,
        "error_message": job.error_message,
        "retry_count": job.retry_count,
        "payload_json": job.payload_json or {},
        "result_json": job.result_json or {},
        "created_at": serialize_dt(job.created_at),
        "finished_at": serialize_dt(job.finished_at),
    }


def serialize_analysis_run(run, *, applied_run_id: str | None) -> dict[str, Any]:
    serialized = serialize_extraction_run(run, applied_run_id=applied_run_id)
    serialized["raw_result_json"] = run.raw_result_json or {}
    serialized["normalized_result_json"] = run.normalized_result_json or {}
    return serialized


def serialize_analysis_projection(projection: ProjectionVersion) -> dict[str, Any]:
    return {
        "id": projection.id,
        "extraction_run_id": projection.extraction_run_id,
        "source_asset_id": projection.source_asset_id,
        "previous_projection_id": projection.previous_projection_id,
        "action_type": projection.action_type,
        "summary_json": projection.summary_json or {},
        "created_at": serialize_dt(projection.created_at),
        "updated_at": serialize_dt(projection.updated_at),
    }


def build_evidence_groups(
    db: Session,
    evidence_items: list[ExtractionEvidence],
    *,
    source_text: str,
) -> list[dict[str, Any]]:
    target_labels = resolve_evidence_target_labels(db, evidence_items)
    relation_contexts = resolve_relation_evidence_contexts(db, evidence_items)
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    for item in evidence_items:
        key = (item.target_type, item.target_id)
        target_label = target_labels.get(key) or fallback_target_label(item)
        if key not in groups:
            relation_context = relation_contexts.get(key, {})
            groups[key] = {
                "target_type": item.target_type,
                "target_id": item.target_id,
                "target_label": target_label,
                "target_subtitle": target_subtitle_for_evidence(item, target_label),
                "detail_href": detail_href_for_evidence(item),
                "curation_href": relation_context.get("curation_href") or curation_href_for_evidence(item),
                "graph_href": relation_context.get("graph_href") or graph_href_for_evidence(item),
                "relation_id": relation_context.get("relation_id"),
                "relation_type": relation_context.get("relation_type"),
                "relation_owner_type": relation_context.get("owner_type"),
                "relation_owner_id": relation_context.get("owner_id"),
                "field_names": [],
                "evidence_count": 0,
                "average_confidence": None,
                "samples": [],
                "_confidence_sum": 0.0,
                "_confidence_count": 0,
            }
        group = groups[key]
        field_name = item.field_name or "unknown"
        if field_name not in group["field_names"]:
            group["field_names"].append(field_name)
        group["evidence_count"] += 1
        if item.confidence_score is not None:
            group["_confidence_sum"] += item.confidence_score
            group["_confidence_count"] += 1
        if len(group["samples"]) < 3:
            group["samples"].append(serialize_analysis_evidence(item, source_text=source_text))

    for group in groups.values():
        group["average_confidence"] = (
            round(group["_confidence_sum"] / group["_confidence_count"], 4)
            if group["_confidence_count"]
            else None
        )
        del group["_confidence_sum"]
        del group["_confidence_count"]
    return sorted(groups.values(), key=lambda item: (-item["evidence_count"], item["target_type"], item["target_id"]))


def serialize_analysis_evidence(item: ExtractionEvidence, *, source_text: str) -> dict[str, Any]:
    context = build_evidence_context(
        source_text,
        start=item.evidence_offset_start,
        end=item.evidence_offset_end,
        evidence_text=item.evidence_text,
    )
    return {
        "id": item.id,
        "target_type": item.target_type,
        "target_id": item.target_id,
        "field_name": item.field_name,
        "evidence_text": truncate_text(item.evidence_text, limit=420) or "",
        "evidence_offset_start": item.evidence_offset_start,
        "evidence_offset_end": item.evidence_offset_end,
        "extractor_name": item.extractor_name,
        "extractor_version": item.extractor_version,
        "confidence_score": item.confidence_score,
        "context_before": context["before"],
        "context_after": context["after"],
        "created_at": serialize_dt(item.created_at),
    }


def resolve_evidence_target_labels(
    db: Session,
    evidence_items: list[ExtractionEvidence],
) -> dict[tuple[str, str], str]:
    entity_ids = {item.target_id for item in evidence_items if item.target_type == "entity"}
    event_ids = {item.target_id for item in evidence_items if item.target_type == "event"}
    relation_reference_ids = {item.target_id for item in evidence_items if item.target_type == "relation"}
    evidence_user_ids = {item.user_id for item in evidence_items if item.user_id}
    labels: dict[tuple[str, str], str] = {}

    if entity_ids:
        for entity in db.scalars(select(Entity).where(Entity.id.in_(entity_ids))).all():
            labels[("entity", entity.id)] = entity.display_name or entity.canonical_name

    if event_ids:
        for event in db.scalars(select(Event).where(Event.id.in_(event_ids))).all():
            labels[("event", event.id)] = event.title

    if relation_reference_ids:
        relations = list(
            db.scalars(
                select(Relation).where(
                    Relation.user_id.in_(evidence_user_ids),
                    or_(
                        Relation.id.in_(relation_reference_ids),
                        Relation.source_id.in_(relation_reference_ids),
                    )
                )
            ).all()
        )
        related_entity_ids = {
            relation.source_id
            for relation in relations
            if relation.source_type == "entity"
        } | {
            relation.target_id
            for relation in relations
            if relation.target_type == "entity"
        }
        related_event_ids = {
            relation.source_id
            for relation in relations
            if relation.source_type == "event"
        } | {
            relation.target_id
            for relation in relations
            if relation.target_type == "event"
        }
        node_labels: dict[tuple[str, str], str] = {}
        if related_entity_ids:
            for entity in db.scalars(select(Entity).where(Entity.id.in_(related_entity_ids))).all():
                node_labels[("entity", entity.id)] = entity.display_name or entity.canonical_name
        if related_event_ids:
            for event in db.scalars(select(Event).where(Event.id.in_(related_event_ids))).all():
                node_labels[("event", event.id)] = event.title
        for relation in relations:
            source_label = node_labels.get((relation.source_type, relation.source_id), relation.source_id)
            target_label = node_labels.get((relation.target_type, relation.target_id), relation.target_id)
            labels[("relation", relation.id)] = f"{source_label} -{relation.relation_type}-> {target_label}"
            # Compatibility for evidence written before relation ids became
            # first-class targets. Ambiguous legacy rows keep the first label.
            labels.setdefault(("relation", relation.source_id), f"{source_label} -{relation.relation_type}-> {target_label}")

    return labels


def resolve_relation_evidence_contexts(
    db: Session,
    evidence_items: list[ExtractionEvidence],
) -> dict[tuple[str, str], dict[str, str]]:
    reference_ids = {item.target_id for item in evidence_items if item.target_type == "relation"}
    user_ids = {item.user_id for item in evidence_items if item.user_id}
    if not reference_ids:
        return {}
    relations = db.scalars(
        select(Relation).where(
            Relation.user_id.in_(user_ids),
            or_(Relation.id.in_(reference_ids), Relation.source_id.in_(reference_ids))
        )
    ).all()
    contexts: dict[tuple[str, str], dict[str, str]] = {}
    legacy_candidates: dict[str, list[tuple[Relation, dict[str, str]]]] = {}
    for relation in relations:
        if relation.source_type in {"event", "entity"}:
            owner_type, owner_id = relation.source_type, relation.source_id
        elif relation.target_type in {"event", "entity"}:
            owner_type, owner_id = relation.target_type, relation.target_id
        else:
            continue
        context = {
            "relation_id": relation.id,
            "relation_type": relation.relation_type,
            "owner_type": owner_type,
            "owner_id": owner_id,
            "curation_href": f"/curation/{'events' if owner_type == 'event' else 'entities'}/{owner_id}",
            "graph_href": f"/graph?{owner_type}_id={owner_id}&active_node_id={owner_id}",
        }
        contexts[("relation", relation.id)] = context
        legacy_candidates.setdefault(relation.source_id, []).append((relation, context))
    legacy_field_names: dict[str, set[str]] = {}
    for item in evidence_items:
        if item.target_type == "relation" and ("relation", item.target_id) not in contexts:
            legacy_field_names.setdefault(item.target_id, set()).add(item.field_name or "")
    for source_id, candidates in legacy_candidates.items():
        expected_types = legacy_field_names.get(source_id, set())
        matched = [item for item in candidates if not expected_types or item[0].relation_type in expected_types]
        if len(matched) == 1:
            contexts[("relation", source_id)] = matched[0][1]
    return contexts


def fallback_target_label(item: ExtractionEvidence) -> str:
    if item.target_type == "relation":
        return f"关系：{item.field_name or item.target_id}"
    return item.target_id


def target_subtitle_for_evidence(item: ExtractionEvidence, target_label: str) -> str:
    return f"{format_target_type(item.target_type)} / {item.field_name or 'unknown'} / {target_label}"


def detail_href_for_evidence(item: ExtractionEvidence) -> str | None:
    if item.target_type == "entity":
        return f"/story/entity/{item.target_id}"
    if item.target_type == "event":
        return f"/events/{item.target_id}"
    return None


def curation_href_for_evidence(item: ExtractionEvidence) -> str | None:
    if item.target_type == "entity":
        return f"/curation/entities/{item.target_id}"
    if item.target_type == "event":
        return f"/curation/events/{item.target_id}"
    return None


def graph_href_for_evidence(item: ExtractionEvidence) -> str | None:
    if item.target_type == "entity":
        return f"/graph?entity_id={item.target_id}"
    if item.target_type == "event":
        return f"/graph?event_id={item.target_id}"
    return "/graph" if item.target_type == "relation" else None


def format_target_type(value: str) -> str:
    if value == "entity":
        return "人物/实体"
    if value == "event":
        return "事件"
    if value == "relation":
        return "关系"
    return value


def get_evidence_context_source(asset: RawAsset | None, derivatives: list[AssetDerivative]) -> str:
    if asset and asset.original_text:
        return asset.original_text
    normalized = next((item for item in derivatives if item.derivative_type == "normalized_text"), None)
    return normalized.content if normalized else ""


def build_evidence_context(
    source_text: str,
    *,
    start: int | None,
    end: int | None,
    evidence_text: str,
    radius: int = 80,
) -> dict[str, str]:
    if not source_text:
        return {"before": "", "after": ""}
    resolved_start = start
    resolved_end = end
    if resolved_start is None or resolved_end is None:
        index = source_text.find(evidence_text) if evidence_text else -1
        if index >= 0:
            resolved_start = index
            resolved_end = index + len(evidence_text)
    if resolved_start is None or resolved_end is None:
        return {"before": "", "after": ""}
    safe_start = max(0, min(resolved_start, len(source_text)))
    safe_end = max(safe_start, min(resolved_end, len(source_text)))
    return {
        "before": source_text[max(0, safe_start - radius):safe_start],
        "after": source_text[safe_end:min(len(source_text), safe_end + radius)],
    }


def empty_extraction_diff() -> dict[str, Any]:
    empty_collection = {
        "changed": False,
        "added": [],
        "removed": [],
        "changed_items": [],
        "unchanged_count": 0,
        "base_count": 0,
        "candidate_count": 0,
    }
    empty_section = {"changed": False, "fields": []}
    return {
        "changed": False,
        "summary": empty_section,
        "entities": empty_collection,
        "events": empty_collection,
        "relations": empty_collection,
        "similarity_hints": empty_collection,
        "style_payload": empty_section,
    }


def build_analysis_steps(
    *,
    note: Note,
    asset: RawAsset | None,
    derivatives: list[AssetDerivative],
    jobs: list[AIJob],
    active_run,
    projections: list[ProjectionVersion],
    story_views: list[StyleView],
    replay_actions,
    evidence_samples: list[str],
) -> list[dict[str, Any]]:
    latest_job = jobs[-1] if jobs else None
    normalized_derivatives = [item for item in derivatives if item.derivative_type == "normalized_text"]
    analysis_derivatives = [item for item in derivatives if item.derivative_type == "analysis_json"]
    normalized_result = active_run.normalized_result_json if active_run else {}
    summary = normalized_result.get("summary", {}) if isinstance(normalized_result, dict) else {}

    return [
        {
            "step_key": "raw_asset",
            "title": "原始材料入库",
            "status": asset.status if asset else "missing",
            "started_at": serialize_dt(asset.created_at) if asset else None,
            "finished_at": serialize_dt(asset.updated_at) if asset else None,
            "duration_ms": None,
            "provider_name": None,
            "model_name": None,
            "summary": f"{asset.title} / {asset.asset_type}" if asset else "当前卷宗没有绑定原始材料。",
            "evidence": [truncate_text(asset.original_text, limit=240)] if asset and asset.original_text else [],
            "output_refs": [asset.id] if asset else [],
        },
        {
            "step_key": "text_preparation",
            "title": "文本准备与多模态解析",
            "status": "completed" if normalized_derivatives or asset and asset.original_text else "pending",
            "started_at": serialize_dt((normalized_derivatives[0] if normalized_derivatives else asset).created_at) if (normalized_derivatives or asset) else None,
            "finished_at": serialize_dt((normalized_derivatives[-1] if normalized_derivatives else asset).updated_at) if (normalized_derivatives or asset) else None,
            "duration_ms": None,
            "provider_name": analysis_derivatives[-1].meta_json.get("provider_name") if analysis_derivatives else None,
            "model_name": analysis_derivatives[-1].meta_json.get("model_name") if analysis_derivatives else None,
            "summary": f"已生成 {len(derivatives)} 个衍生结果，其中规范化文本 {len(normalized_derivatives)} 个。",
            "evidence": [truncate_text(item.content, limit=240) or "" for item in normalized_derivatives[:2]],
            "output_refs": [item.id for item in derivatives],
        },
        {
            "step_key": "knowledge_extraction",
            "title": "LLM 抽取与结构化分析",
            "status": active_run.status if active_run else (latest_job.status if latest_job else "pending"),
            "started_at": serialize_dt(active_run.created_at) if active_run else serialize_dt(latest_job.created_at) if latest_job else None,
            "finished_at": serialize_dt(active_run.updated_at) if active_run else serialize_dt(latest_job.finished_at) if latest_job else None,
            "duration_ms": duration_ms(active_run.created_at, active_run.updated_at) if active_run else duration_ms(latest_job.created_at, latest_job.finished_at) if latest_job else None,
            "provider_name": active_run.provider_name if active_run else None,
            "model_name": active_run.model_name if active_run else None,
            "summary": build_extraction_step_summary(summary, normalized_result),
            "evidence": evidence_samples,
            "output_refs": [active_run.id] if active_run else [],
        },
        {
            "step_key": "projection",
            "title": "规范化投影入库",
            "status": "applied" if note.active_projection_id or active_run and active_run.projection_status == "applied" else "not_applied",
            "started_at": serialize_dt(projections[-1].created_at) if projections else None,
            "finished_at": serialize_dt(note.processed_at or note.updated_at),
            "duration_ms": None,
            "provider_name": active_run.provider_name if active_run else None,
            "model_name": active_run.model_name if active_run else None,
            "summary": f"当前投影版本 {note.active_projection_id or '未生成'}，历史投影 {len(projections)} 次。",
            "evidence": [],
            "output_refs": [projection.id for projection in projections[-3:]],
        },
        {
            "step_key": "review_governance",
            "title": "人工审核与重放审计",
            "status": "reviewed" if replay_actions else "not_reviewed",
            "started_at": serialize_dt(replay_actions[-1].created_at) if replay_actions else None,
            "finished_at": serialize_dt(replay_actions[0].created_at) if replay_actions else None,
            "duration_ms": None,
            "provider_name": None,
            "model_name": None,
            "summary": f"已记录 {len(replay_actions)} 条审批、回滚或自动应用日志。",
            "evidence": [
                action.payload_json.get("note")
                for action in replay_actions
                if (action.payload_json or {}).get("note")
            ][:3],
            "output_refs": [action.id for action in replay_actions[:5]],
        },
        {
            "step_key": "story_rendering",
            "title": "中二风故事视图",
            "status": "completed" if story_views else "not_generated",
            "started_at": serialize_dt(story_views[-1].created_at) if story_views else None,
            "finished_at": serialize_dt(story_views[0].updated_at) if story_views else None,
            "duration_ms": None,
            "provider_name": active_run.provider_name if active_run else None,
            "model_name": active_run.model_name if active_run else None,
            "summary": f"当前已有 {len(story_views)} 个 note 级故事视图，可从已应用抽取运行重新生成。",
            "evidence": [story_views[0].title] if story_views else [],
            "output_refs": [story.id for story in story_views],
        },
    ]


def build_extraction_step_summary(summary: dict[str, Any], payload: dict[str, Any]) -> str:
    title = summary.get("title") or "未命名结果"
    return (
        f"{title}：实体 {len(payload.get('entities', []))} 个，"
        f"事件 {len(payload.get('events', []))} 个，关系 {len(payload.get('relations', []))} 条。"
    )


def duration_ms(start, end) -> int | None:
    if not start or not end:
        return None
    return max(0, int((end - start).total_seconds() * 1000))


def truncate_text(value: str | None, *, limit: int = 320) -> str | None:
    if not value:
        return None
    return value if len(value) <= limit else f"{value[:limit]}..."


def serialize_dt(value) -> str | None:
    return value.isoformat() if value else None

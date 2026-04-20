from datetime import UTC, datetime
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.note import Note
from app.models.raw_asset import RawAsset
from app.models.extraction import ExtractionRun, ProjectionVersion
from app.models.review import ReviewAction
from app.services.projection_service import ProjectionResult, persist_extraction_projection
from app.utils.text import normalize_name

RUN_STATUS_APPLIED = "applied"
RUN_STATUS_SUPERSEDED = "superseded"
RUN_STATUS_COMPLETED = "completed"
RUN_STATUS_READY_FOR_REVIEW = "ready_for_review"
RUN_STATUS_REJECTED = "rejected"
RUN_STATUS_FAILED = "failed"
MIN_DATETIME = datetime.min.replace(tzinfo=UTC)
REPLAY_ACTION_TYPES = {
    "apply_extraction_run",
    "auto_apply_extraction_run",
    "approve_extraction_run",
    "reject_extraction_run",
}
PROJECTION_STATUS_APPLIED = "applied"
PROJECTION_STATUS_SUPERSEDED = "superseded"
PROJECTION_STATUS_PENDING_REVIEW = "pending_review"
PROJECTION_STATUS_REJECTED = "rejected"
PROJECTION_STATUS_FAILED = "failed"
PROJECTION_STATUS_NOT_APPLIED = "not_applied"
APPLIED_FALLBACK_STATUSES = {RUN_STATUS_APPLIED, RUN_STATUS_SUPERSEDED, RUN_STATUS_COMPLETED}
ACTIVE_LINEAGE_STATUSES = {RUN_STATUS_APPLIED, RUN_STATUS_SUPERSEDED, RUN_STATUS_COMPLETED}


def serialize_extraction_run(run: ExtractionRun, *, applied_run_id: str | None = None) -> dict[str, Any]:
    projection_status = normalized_projection_status(run)
    return {
        "id": run.id,
        "note_id": run.note_id,
        "source_asset_id": run.source_asset_id,
        "status": run.status,
        "is_applied": is_applied_run(run, applied_run_id=applied_run_id),
        "extractor_name": run.extractor_name,
        "extractor_version": run.extractor_version,
        "provider_name": run.provider_name,
        "model_name": run.model_name,
        "prompt_version": run.prompt_version,
        "schema_version": run.schema_version,
        "input_hash": run.input_hash,
        "parent_run_id": run.parent_run_id,
        "run_kind": run.run_kind,
        "projection_status": projection_status,
        "created_at": serialize_datetime(run.created_at),
        "updated_at": serialize_datetime(run.updated_at),
        "summary": summarize_run_payload(run.normalized_result_json or {}),
    }


def list_extraction_runs(db: Session, *, user_id: str, note_id: str) -> list[ExtractionRun]:
    return list(
        db.scalars(
            select(ExtractionRun)
            .where(ExtractionRun.user_id == user_id, ExtractionRun.note_id == note_id)
            .order_by(ExtractionRun.created_at.desc())
        ).all()
    )


def list_note_replay_actions(db: Session, *, user_id: str, note_id: str, limit: int = 20) -> list[ReviewAction]:
    return list(
        db.scalars(
            select(ReviewAction)
            .where(
                ReviewAction.user_id == user_id,
                ReviewAction.target_type == "note",
                ReviewAction.target_id == note_id,
                ReviewAction.action_type.in_(sorted(REPLAY_ACTION_TYPES)),
            )
            .order_by(ReviewAction.created_at.desc())
            .limit(limit)
        ).all()
    )


def get_extraction_run(db: Session, *, user_id: str, note_id: str, run_id: str) -> ExtractionRun | None:
    return db.scalar(
        select(ExtractionRun).where(
            ExtractionRun.user_id == user_id,
            ExtractionRun.note_id == note_id,
            ExtractionRun.id == run_id,
        )
    )


def compare_extraction_runs(
    base_run: ExtractionRun,
    candidate_run: ExtractionRun,
    *,
    applied_run_id: str | None = None,
) -> dict[str, Any]:
    resolved_applied_run_id = applied_run_id or resolve_applied_run_id([base_run, candidate_run])
    diff = compare_extraction_payloads(
        base_run.normalized_result_json or {},
        candidate_run.normalized_result_json or {},
    )
    return {
        "note_id": base_run.note_id,
        "base_run": serialize_extraction_run(base_run, applied_run_id=resolved_applied_run_id),
        "candidate_run": serialize_extraction_run(candidate_run, applied_run_id=resolved_applied_run_id),
        "diff": diff,
    }


def resolve_applied_run_id(runs: list[ExtractionRun]) -> str | None:
    projection_applied_runs = [run for run in runs if normalized_projection_status(run) == PROJECTION_STATUS_APPLIED]
    if projection_applied_runs:
        projection_applied_runs.sort(key=lambda item: item.created_at or MIN_DATETIME, reverse=True)
        return projection_applied_runs[0].id

    applied_runs = [run for run in runs if run.status == RUN_STATUS_APPLIED]
    if applied_runs:
        applied_runs.sort(key=lambda item: item.created_at or MIN_DATETIME, reverse=True)
        return applied_runs[0].id

    successful_runs = [run for run in runs if run.status in APPLIED_FALLBACK_STATUSES]
    if not successful_runs:
        return None
    successful_runs.sort(key=lambda item: item.created_at or MIN_DATETIME, reverse=True)
    return successful_runs[0].id


def is_applied_run(run: ExtractionRun, *, applied_run_id: str | None) -> bool:
    if applied_run_id:
        return run.id == applied_run_id
    return run.status == RUN_STATUS_APPLIED


def mark_extraction_run_applied(db: Session, *, user_id: str, note_id: str, run_id: str) -> None:
    runs = list_extraction_runs(db, user_id=user_id, note_id=note_id)
    for run in runs:
        if run.id == run_id:
            run.status = RUN_STATUS_APPLIED
            run.projection_status = PROJECTION_STATUS_APPLIED
        elif run.status in ACTIVE_LINEAGE_STATUSES:
            run.status = RUN_STATUS_SUPERSEDED
            run.projection_status = PROJECTION_STATUS_SUPERSEDED
        db.add(run)


def apply_extraction_run_projection(
    db: Session,
    *,
    note: Note,
    asset: RawAsset,
    run: ExtractionRun,
    text: str,
    action_type: str = "apply_extraction_run",
    operator_note: str | None = None,
    status_before: str | None = None,
) -> ProjectionResult:
    previous_applied_run_id = resolve_applied_run_id(list_extraction_runs(db, user_id=note.user_id, note_id=note.id))
    previous_projection_id = note.active_projection_id
    payload = run.normalized_result_json or {}
    projection_result = persist_extraction_projection(
        db,
        note=note,
        asset=asset,
        payload=payload,
        text=text,
    )
    mark_extraction_run_applied(db, user_id=note.user_id, note_id=note.id, run_id=run.id)
    projection_version = create_projection_version(
        db,
        note=note,
        asset=asset,
        run=run,
        action_type=action_type,
        previous_projection_id=previous_projection_id,
        projection_result=projection_result,
    )
    note.active_projection_id = projection_version.id
    log_replay_action(
        db,
        user_id=note.user_id,
        note_id=note.id,
        run=run,
        action_type=action_type,
        previous_run_id=previous_applied_run_id,
        projection_version_id=projection_version.id,
        previous_projection_version_id=previous_projection_id,
        operator_note=operator_note,
        status_before=status_before,
    )
    db.flush()
    return projection_result


def approve_reviewable_extraction_run(
    db: Session,
    *,
    note: Note,
    asset: RawAsset,
    run: ExtractionRun,
    text: str,
    operator_note: str | None = None,
) -> ProjectionResult:
    if run.status != RUN_STATUS_READY_FOR_REVIEW:
        raise ValueError("Extraction run is not awaiting review")
    return apply_extraction_run_projection(
        db,
        note=note,
        asset=asset,
        run=run,
        text=text,
        action_type="approve_extraction_run",
        operator_note=operator_note,
        status_before=RUN_STATUS_READY_FOR_REVIEW,
    )


def reject_reviewable_extraction_run(
    db: Session,
    *,
    user_id: str,
    note_id: str,
    run: ExtractionRun,
    operator_note: str | None = None,
) -> ExtractionRun:
    if run.status != RUN_STATUS_READY_FOR_REVIEW:
        raise ValueError("Extraction run is not awaiting review")
    run.status = RUN_STATUS_REJECTED
    run.projection_status = PROJECTION_STATUS_REJECTED
    db.add(run)
    log_replay_action(
        db,
        user_id=user_id,
        note_id=note_id,
        run=run,
        action_type="reject_extraction_run",
        previous_run_id=resolve_applied_run_id(list_extraction_runs(db, user_id=user_id, note_id=note_id)),
        projection_version_id=None,
        previous_projection_version_id=None,
        operator_note=operator_note,
        status_before=RUN_STATUS_READY_FOR_REVIEW,
        status_after=RUN_STATUS_REJECTED,
    )
    db.flush()
    return run


def log_replay_action(
    db: Session,
    *,
    user_id: str,
    note_id: str,
    run: ExtractionRun,
    action_type: str,
    previous_run_id: str | None,
    projection_version_id: str | None,
    previous_projection_version_id: str | None,
    operator_note: str | None = None,
    status_before: str | None = None,
    status_after: str | None = None,
) -> ReviewAction:
    action = ReviewAction(
        user_id=user_id,
        target_type="note",
        target_id=note_id,
        action_type=action_type,
        status_before=status_before if status_before is not None else (RUN_STATUS_APPLIED if previous_run_id else None),
        status_after=status_after or RUN_STATUS_APPLIED,
        payload_json={
            "run_id": run.id,
            "previous_run_id": previous_run_id,
            "projection_version_id": projection_version_id,
            "previous_projection_version_id": previous_projection_version_id,
            "extractor_name": run.extractor_name,
            "extractor_version": run.extractor_version,
            "provider_name": run.provider_name,
            "model_name": run.model_name,
            "prompt_version": run.prompt_version,
            "schema_version": run.schema_version,
            "note": operator_note,
        },
    )
    db.add(action)
    db.flush()
    return action


def serialize_replay_action(action: ReviewAction) -> dict[str, Any]:
    payload = action.payload_json or {}
    return {
        "id": action.id,
        "action_type": action.action_type,
        "created_at": serialize_datetime(action.created_at),
        "status_before": action.status_before,
        "status_after": action.status_after,
        "run_id": safe_string(payload.get("run_id")),
        "previous_run_id": safe_string(payload.get("previous_run_id")) or None,
        "projection_version_id": safe_string(payload.get("projection_version_id")) or None,
        "previous_projection_version_id": safe_string(payload.get("previous_projection_version_id")) or None,
        "extractor_name": safe_string(payload.get("extractor_name")),
        "extractor_version": safe_string(payload.get("extractor_version")),
        "provider_name": safe_string(payload.get("provider_name")) or None,
        "model_name": safe_string(payload.get("model_name")) or None,
        "prompt_version": safe_string(payload.get("prompt_version")) or None,
        "schema_version": safe_string(payload.get("schema_version")) or None,
        "note": safe_string(payload.get("note")) or None,
    }


def normalized_projection_status(run: ExtractionRun) -> str:
    if run.projection_status:
        return run.projection_status
    if run.status == RUN_STATUS_APPLIED:
        return PROJECTION_STATUS_APPLIED
    if run.status == RUN_STATUS_SUPERSEDED:
        return PROJECTION_STATUS_SUPERSEDED
    if run.status == RUN_STATUS_READY_FOR_REVIEW:
        return PROJECTION_STATUS_PENDING_REVIEW
    if run.status == RUN_STATUS_REJECTED:
        return PROJECTION_STATUS_REJECTED
    if run.status == RUN_STATUS_FAILED:
        return PROJECTION_STATUS_FAILED
    return PROJECTION_STATUS_NOT_APPLIED


def create_projection_version(
    db: Session,
    *,
    note: Note,
    asset: RawAsset,
    run: ExtractionRun,
    action_type: str,
    previous_projection_id: str | None,
    projection_result: ProjectionResult,
) -> ProjectionVersion:
    version = ProjectionVersion(
        user_id=note.user_id,
        note_id=note.id,
        extraction_run_id=run.id,
        source_asset_id=asset.id,
        previous_projection_id=previous_projection_id,
        action_type=action_type,
        summary_json={
            "event_id": projection_result.event_id,
            "extractor_name": projection_result.extractor_name,
            "extractor_version": projection_result.extractor_version,
            "entity_count": projection_result.entity_count,
            "relation_count": projection_result.relation_count,
            "similarity_hint_count": projection_result.similarity_hint_count,
        },
    )
    db.add(version)
    db.flush()
    return version


def compare_extraction_payloads(base_payload: dict[str, Any], candidate_payload: dict[str, Any]) -> dict[str, Any]:
    summary = diff_summary(base_payload.get("summary"), candidate_payload.get("summary"))
    entities = diff_collection(
        normalize_entities(base_payload.get("entities")),
        normalize_entities(candidate_payload.get("entities")),
        key_fn=lambda item: item["key"],
    )
    events = diff_collection(
        normalize_events(base_payload.get("events")),
        normalize_events(candidate_payload.get("events")),
        key_fn=lambda item: item["key"],
    )
    relations = diff_collection(
        normalize_relations(base_payload.get("relations")),
        normalize_relations(candidate_payload.get("relations")),
        key_fn=lambda item: item["key"],
    )
    similarity_hints = diff_collection(
        normalize_similarity_hints(base_payload.get("similarity_hints")),
        normalize_similarity_hints(candidate_payload.get("similarity_hints")),
        key_fn=lambda item: item["key"],
    )
    style = diff_style(base_payload.get("style_payload"), candidate_payload.get("style_payload"))
    changed = any(
        section["changed"]
        for section in [summary, entities, events, relations, similarity_hints, style]
    )
    return {
        "changed": changed,
        "summary": summary,
        "entities": entities,
        "events": events,
        "relations": relations,
        "similarity_hints": similarity_hints,
        "style_payload": style,
    }


def summarize_run_payload(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    return {
        "title": safe_string(summary.get("title")) if isinstance(summary, dict) else "",
        "category": safe_string(summary.get("category")) if isinstance(summary, dict) else "",
        "entity_count": len(payload.get("entities")) if isinstance(payload.get("entities"), list) else 0,
        "event_count": len(payload.get("events")) if isinstance(payload.get("events"), list) else 0,
        "relation_count": len(payload.get("relations")) if isinstance(payload.get("relations"), list) else 0,
        "similarity_hint_count": len(payload.get("similarity_hints")) if isinstance(payload.get("similarity_hints"), list) else 0,
    }


def diff_summary(base_value: object, candidate_value: object) -> dict[str, Any]:
    base = base_value if isinstance(base_value, dict) else {}
    candidate = candidate_value if isinstance(candidate_value, dict) else {}
    fields = []
    for field in ["title", "short_summary", "canonical_text", "category", "tags"]:
        base_field = comparable_value(base.get(field))
        candidate_field = comparable_value(candidate.get(field))
        fields.append(
            {
                "field": field,
                "base": base_field,
                "candidate": candidate_field,
                "changed": base_field != candidate_field,
            }
        )
    return {
        "changed": any(item["changed"] for item in fields),
        "fields": fields,
    }


def diff_style(base_value: object, candidate_value: object) -> dict[str, Any]:
    base = normalize_style_payload(base_value)
    candidate = normalize_style_payload(candidate_value)
    fields = []
    for field in ["title", "character_cards", "event_narrative"]:
        base_field = comparable_value(base.get(field))
        candidate_field = comparable_value(candidate.get(field))
        fields.append(
            {
                "field": field,
                "base": base_field,
                "candidate": candidate_field,
                "changed": base_field != candidate_field,
            }
        )
    return {
        "changed": any(item["changed"] for item in fields),
        "fields": fields,
    }


def diff_collection(
    base_items: list[dict[str, Any]],
    candidate_items: list[dict[str, Any]],
    *,
    key_fn: Callable[[dict[str, Any]], str],
) -> dict[str, Any]:
    base_by_key = {key_fn(item): item for item in base_items}
    candidate_by_key = {key_fn(item): item for item in candidate_items}
    added_keys = sorted(candidate_by_key.keys() - base_by_key.keys())
    removed_keys = sorted(base_by_key.keys() - candidate_by_key.keys())
    shared_keys = sorted(base_by_key.keys() & candidate_by_key.keys())

    changed = []
    unchanged_count = 0
    for key in shared_keys:
        if base_by_key[key] == candidate_by_key[key]:
            unchanged_count += 1
            continue
        changed.append({"key": key, "base": base_by_key[key], "candidate": candidate_by_key[key]})

    return {
        "changed": bool(added_keys or removed_keys or changed),
        "added": [candidate_by_key[key] for key in added_keys],
        "removed": [base_by_key[key] for key in removed_keys],
        "changed_items": changed,
        "unchanged_count": unchanged_count,
        "base_count": len(base_items),
        "candidate_count": len(candidate_items),
    }


def normalize_entities(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    items = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = safe_string(item.get("canonical_name") or item.get("name"))
        entity_type = safe_string(item.get("entity_type"))
        if not name:
            continue
        items.append(
            {
                "key": f"{entity_type}:{normalize_name(name)}",
                "name": name,
                "entity_type": entity_type,
                "aliases": normalize_string_list(item.get("aliases")),
                "description": safe_string(item.get("description")),
                "confidence": comparable_value(item.get("confidence")),
            }
        )
    return sorted(items, key=lambda item: item["key"])


def normalize_events(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    items = []
    for item in value:
        if not isinstance(item, dict):
            continue
        title = safe_string(item.get("title"))
        time_value = item.get("time") if isinstance(item.get("time"), dict) else {}
        sort_time = safe_string(time_value.get("timeline_sort_time")) if isinstance(time_value, dict) else ""
        if not title:
            continue
        items.append(
            {
                "key": f"{normalize_name(title)}:{sort_time}",
                "title": title,
                "event_type": safe_string(item.get("event_type")),
                "summary": safe_string(item.get("summary")),
                "time_text": safe_string(time_value.get("time_text")) if isinstance(time_value, dict) else "",
                "timeline_sort_time": sort_time,
                "participant_count": len(item.get("participants")) if isinstance(item.get("participants"), list) else 0,
                "location_names": normalize_location_names(item.get("locations")),
                "confidence": comparable_value(item.get("confidence")),
            }
        )
    return sorted(items, key=lambda item: item["key"])


def normalize_relations(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    items = []
    for item in value:
        if not isinstance(item, dict):
            continue
        source_ref = item.get("source_ref") if isinstance(item.get("source_ref"), dict) else {}
        target_ref = item.get("target_ref") if isinstance(item.get("target_ref"), dict) else {}
        relation_type = safe_string(item.get("relation_type"))
        source = normalize_reference(source_ref)
        target = normalize_reference(target_ref)
        if not relation_type or not source or not target:
            continue
        items.append(
            {
                "key": f"{source}->{relation_type}->{target}",
                "source": source,
                "relation_type": relation_type,
                "target": target,
                "confidence": comparable_value(item.get("confidence")),
            }
        )
    return sorted(items, key=lambda item: item["key"])


def normalize_similarity_hints(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    items = []
    for item in value:
        if not isinstance(item, dict):
            continue
        target_type = safe_string(item.get("target_type"))
        target_id = safe_string(item.get("target_id"))
        reason = safe_string(item.get("reason"))
        if not target_type or not target_id:
            continue
        items.append(
            {
                "key": f"{target_type}:{target_id}:{normalize_name(reason)}",
                "target_type": target_type,
                "target_id": target_id,
                "reason": reason,
                "confidence": comparable_value(item.get("confidence")),
            }
        )
    return sorted(items, key=lambda item: item["key"])


def normalize_style_payload(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        "title": safe_string(value.get("title")),
        "character_cards": [
            {
                "entity_name": safe_string(item.get("entity_name") or item.get("display_name")),
                "epithet": safe_string(item.get("epithet")),
            }
            for item in value.get("character_cards", [])
            if isinstance(item, dict)
        ]
        if isinstance(value.get("character_cards"), list)
        else [],
        "event_narrative": [
            {
                "headline": safe_string(item.get("headline")),
                "body": safe_string(item.get("body")),
            }
            for item in value.get("event_narrative", [])
            if isinstance(item, dict)
        ]
        if isinstance(value.get("event_narrative"), list)
        else [],
    }


def normalize_reference(value: object) -> str:
    if not isinstance(value, dict):
        return ""
    reference_type = safe_string(value.get("type"))
    reference_id = safe_string(value.get("id") or value.get("temp_id"))
    if not reference_type or not reference_id:
        return ""
    return f"{reference_type}:{reference_id}"


def normalize_location_names(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    names = []
    for item in value:
        if isinstance(item, dict):
            name = safe_string(item.get("name"))
        else:
            name = safe_string(item)
        if name and name not in names:
            names.append(name)
    return names


def normalize_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    items = []
    for item in value:
        text = safe_string(item)
        if text and text not in items:
            items.append(text)
    return items


def comparable_value(value: object) -> Any:
    if isinstance(value, str):
        return truncate_text(value.strip())
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [comparable_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): comparable_value(item) for key, item in sorted(value.items())}
    return str(value)


def safe_string(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def truncate_text(value: str, limit: int = 500) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit]}..."


def serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None

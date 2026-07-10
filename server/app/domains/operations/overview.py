from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.serializers import isoformat, serialize_job
from app.models.ai_job import AIJob
from app.models.entity import Entity, EventEntity, Relation
from app.models.event import Event
from app.models.extraction import ExtractionRun, MergeCandidate
from app.models.graph_viewpoint import GraphViewpoint
from app.models.note import Note
from app.models.raw_asset import RawAsset
from app.models.review import ReviewAction
from app.domains.governance.review import build_object_summary


def get_operations_overview(db: Session, *, user_id: str) -> dict[str, Any]:
    job_status_counts = _count_by_status(db, AIJob, AIJob.status, user_id=user_id)
    asset_type_counts = _count_by_status(db, RawAsset, RawAsset.asset_type, user_id=user_id)
    failed_jobs = db.scalars(
        select(AIJob)
        .where(AIJob.user_id == user_id, AIJob.status == "failed")
        .order_by(AIJob.created_at.desc())
        .limit(5)
    ).all()

    pending_candidates = db.scalars(
        select(MergeCandidate)
        .where(MergeCandidate.user_id == user_id, MergeCandidate.status == "pending")
        .order_by(MergeCandidate.score.desc(), MergeCandidate.created_at.desc())
        .limit(5)
    ).all()
    pending_entities = int(
        db.scalar(
            select(func.count())
            .select_from(MergeCandidate)
            .where(
                MergeCandidate.user_id == user_id,
                MergeCandidate.status == "pending",
                MergeCandidate.object_type == "entity",
            )
        )
        or 0
    )
    pending_events = int(
        db.scalar(
            select(func.count())
            .select_from(MergeCandidate)
            .where(
                MergeCandidate.user_id == user_id,
                MergeCandidate.status == "pending",
                MergeCandidate.object_type == "event",
            )
        )
        or 0
    )

    reviewable_runs = db.execute(
        select(ExtractionRun, Note)
        .join(Note, Note.id == ExtractionRun.note_id)
        .where(
            ExtractionRun.user_id == user_id,
            ExtractionRun.status == "ready_for_review",
            Note.user_id == user_id,
        )
        .order_by(ExtractionRun.created_at.desc())
        .limit(5)
    ).all()
    ready_for_review_count = int(
        db.scalar(
            select(func.count())
            .select_from(ExtractionRun)
            .where(ExtractionRun.user_id == user_id, ExtractionRun.status == "ready_for_review")
        )
        or 0
    )
    processing_notes_count = int(
        db.scalar(
            select(func.count())
            .select_from(Note)
            .where(Note.user_id == user_id, Note.status == "processing")
        )
        or 0
    )

    recent_actions = db.scalars(
        select(ReviewAction)
        .where(ReviewAction.user_id == user_id)
        .order_by(ReviewAction.created_at.desc())
        .limit(8)
    ).all()
    recent_graph_actions = db.scalars(
        select(ReviewAction)
        .where(
            ReviewAction.user_id == user_id,
            ReviewAction.action_type.in_(
                [
                    "update_entity",
                    "update_event",
                    "upsert_event_participant",
                    "remove_event_participant",
                    "add_relation",
                    "upsert_relation",
                    "update_relation",
                    "remove_relation",
                    "set_conflict_disposition",
                ]
            ),
        )
        .order_by(ReviewAction.created_at.desc())
        .limit(8)
    ).all()

    return {
        "jobs": {
            "total": sum(job_status_counts.values()),
            "pending": job_status_counts.get("pending", 0),
            "running": job_status_counts.get("running", 0),
            "failed": job_status_counts.get("failed", 0),
            "completed": job_status_counts.get("completed", 0),
            "by_status": [
                {"status": status, "count": count}
                for status, count in sorted(job_status_counts.items(), key=lambda item: (-item[1], item[0]))
            ],
            "recent_failed_jobs": [serialize_job(job) for job in failed_jobs],
        },
        "assets": {
            "total": sum(asset_type_counts.values()),
            "uploaded": int(
                db.scalar(
                    select(func.count())
                    .select_from(RawAsset)
                    .where(RawAsset.user_id == user_id, RawAsset.status == "uploaded")
                )
                or 0
            ),
            "by_type": [
                {"status": asset_type, "count": count}
                for asset_type, count in sorted(asset_type_counts.items(), key=lambda item: (-item[1], item[0]))
            ],
        },
        "review": {
            "pending_total": pending_entities + pending_events,
            "pending_entities": pending_entities,
            "pending_events": pending_events,
            "recent_candidates": [_serialize_merge_candidate_signal(db, candidate) for candidate in pending_candidates],
        },
        "extraction": {
            "ready_for_review": ready_for_review_count,
            "processing_notes": processing_notes_count,
            "recent_reviewable_runs": [
                {
                    "run_id": run.id,
                    "note_id": note.id,
                    "note_title": note.title,
                    "status": run.status,
                    "extractor_name": run.extractor_name,
                    "extractor_version": run.extractor_version,
                    "created_at": isoformat(run.created_at),
                    "href": f"/notes/{note.id}",
                }
                for run, note in reviewable_runs
            ],
        },
        "activity": {
            "recent_actions": [_serialize_activity_item(action) for action in recent_actions],
        },
        "graph_quality": {
            "viewpoint_count": int(db.scalar(select(func.count()).select_from(GraphViewpoint).where(GraphViewpoint.user_id == user_id)) or 0),
            "low_confidence_relation_count": int(
                db.scalar(
                    select(func.count())
                    .select_from(Relation)
                    .where(Relation.user_id == user_id, Relation.confidence_score.is_not(None), Relation.confidence_score < 0.55)
                )
                or 0
            ),
            "orphan_entity_count": count_orphan_entities(db, user_id=user_id),
            "orphan_event_count": count_orphan_events(db, user_id=user_id),
            "recent_graph_actions": [_serialize_activity_item(action) for action in recent_graph_actions],
        },
    }


def _count_by_status(db: Session, model: type[Any], column: Any, *, user_id: str) -> dict[str, int]:
    rows = db.execute(
        select(column, func.count())
        .select_from(model)
        .where(model.user_id == user_id)
        .group_by(column)
    ).all()
    return {str(status): int(count) for status, count in rows if status}


def _serialize_merge_candidate_signal(db: Session, candidate: MergeCandidate) -> dict[str, Any]:
    source = build_object_summary(db, candidate.object_type, candidate.source_id, user_id=candidate.user_id)
    peer = build_object_summary(db, candidate.object_type, candidate.candidate_id, user_id=candidate.user_id)
    return {
        "id": candidate.id,
        "object_type": candidate.object_type,
        "status": candidate.status,
        "score": float(candidate.score),
        "source_label": source["label"] if source else None,
        "candidate_label": peer["label"] if peer else None,
        "href": source["href"] if source else "/review",
    }


def _serialize_activity_item(action: ReviewAction) -> dict[str, Any]:
    href, href_label = _resolve_action_href(action)
    return {
        "id": action.id,
        "target_type": action.target_type,
        "target_id": action.target_id,
        "action_type": action.action_type,
        "status_before": action.status_before,
        "status_after": action.status_after,
        "created_at": isoformat(action.created_at),
        "href": href,
        "href_label": href_label,
        "summary": _summarize_action(action),
    }


def _resolve_action_href(action: ReviewAction) -> tuple[str, str]:
    if action.target_type == "merge_candidate":
        return "/review", "打开审核队列"
    if action.target_type == "entity":
        if action.action_type == "confirm_alias":
            return f"/review/entities/{action.target_id}", "打开人物审核"
        return f"/curation/entities/{action.target_id}", "打开人物校对"
    if action.target_type == "event":
        return f"/curation/events/{action.target_id}", "打开事件校对"
    if action.target_type == "note":
        return f"/notes/{action.target_id}", "打开卷宗"
    return "/operations", "返回运维台"


def _summarize_action(action: ReviewAction) -> str:
    action_label = action.action_type.replace("_", " ")
    if action.target_type == "merge_candidate":
        return f"merge candidate {action.target_id} 执行了 {action_label}"
    return f"{action.target_type} {action.target_id} 执行了 {action_label}"


def count_orphan_entities(db: Session, *, user_id: str) -> int:
    linked_entity_ids = {
        row[0]
        for row in db.execute(
            select(EventEntity.entity_id).join(Event, Event.id == EventEntity.event_id).where(Event.user_id == user_id)
        ).all()
    }
    relation_entity_ids = {
        row[0]
        for row in db.execute(
            select(Relation.source_id).where(Relation.user_id == user_id, Relation.source_type == "entity")
        ).all()
    } | {
        row[0]
        for row in db.execute(
            select(Relation.target_id).where(Relation.user_id == user_id, Relation.target_type == "entity")
        ).all()
    }
    connected_ids = linked_entity_ids | relation_entity_ids
    query = select(func.count()).select_from(Entity).where(Entity.user_id == user_id)
    if connected_ids:
        query = query.where(Entity.id.not_in(connected_ids))
    return int(db.scalar(query) or 0)


def count_orphan_events(db: Session, *, user_id: str) -> int:
    participant_event_ids = {
        row[0]
        for row in db.execute(
            select(EventEntity.event_id).join(Event, Event.id == EventEntity.event_id).where(Event.user_id == user_id)
        ).all()
    }
    relation_event_ids = {
        row[0]
        for row in db.execute(
            select(Relation.source_id).where(Relation.user_id == user_id, Relation.source_type == "event")
        ).all()
    } | {
        row[0]
        for row in db.execute(
            select(Relation.target_id).where(Relation.user_id == user_id, Relation.target_type == "event")
        ).all()
    }
    connected_ids = participant_event_ids | relation_event_ids
    query = select(func.count()).select_from(Event).where(Event.user_id == user_id)
    if connected_ids:
        query = query.where(Event.id.not_in(connected_ids))
    return int(db.scalar(query) or 0)

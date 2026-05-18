from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.serializers import serialize_note
from app.core.pagination import PageParams, paginate_query
from app.models.ai_job import AIJob
from app.models.asset_derivative import AssetDerivative
from app.models.extraction import ExtractionEvidence, ProjectionVersion
from app.domains.replay.service import (
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
    replay_actions = list_note_replay_actions(db, user_id=user_id, note_id=note.id, limit=50)
    evidence_count = int(
        db.scalar(
            select(func.count())
            .select_from(ExtractionEvidence)
            .where(ExtractionEvidence.user_id == user_id, ExtractionEvidence.source_note_id == note.id)
        )
        or 0
    )
    evidence_samples = [
        item.evidence_text
        for item in db.scalars(
            select(ExtractionEvidence)
            .where(ExtractionEvidence.user_id == user_id, ExtractionEvidence.source_note_id == note.id)
            .order_by(ExtractionEvidence.created_at.desc())
            .limit(5)
        ).all()
    ]
    latest_run = runs[-1] if runs else None
    active_run = next((run for run in runs if run.id == applied_run_id), latest_run)

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
            replay_actions=replay_actions,
            evidence_samples=evidence_samples,
        ),
        "jobs": [serialize_analysis_job(job) for job in jobs],
        "derivatives": [serialize_analysis_derivative(derivative) for derivative in derivatives],
        "runs": [serialize_analysis_run(run, applied_run_id=applied_run_id) for run in runs],
        "projections": [serialize_analysis_projection(projection) for projection in projections],
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


def build_analysis_steps(
    *,
    note: Note,
    asset: RawAsset | None,
    derivatives: list[AssetDerivative],
    jobs: list[AIJob],
    active_run,
    projections: list[ProjectionVersion],
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

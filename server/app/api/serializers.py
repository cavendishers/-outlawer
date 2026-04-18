from datetime import datetime

from app.models.ai_job import AIJob
from app.models.entity import Entity
from app.models.event import Event, TimelineItem
from app.models.note import Note
from app.models.raw_asset import RawAsset


def isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def serialize_asset(asset: RawAsset, *, raw_url: str | None = None) -> dict:
    return {
        "id": asset.id,
        "asset_type": asset.asset_type,
        "title": asset.title,
        "status": asset.status,
        "mime_type": asset.mime_type,
        "object_key": asset.object_key,
        "original_text": asset.original_text,
        "raw_url": raw_url,
    }


def serialize_note(note: Note) -> dict:
    return {
        "id": note.id,
        "title": note.title,
        "summary": note.summary,
        "canonical_text": note.canonical_text,
        "category": note.category,
        "status": note.status,
        "asset_id": note.asset_id,
        "primary_time": isoformat(note.primary_time),
        "processed_at": isoformat(note.processed_at),
        "created_at": isoformat(note.created_at),
        "updated_at": isoformat(note.updated_at),
    }


def serialize_job(job: AIJob, *, include_result: bool = False) -> dict:
    payload = {
        "id": job.id,
        "job_type": job.job_type,
        "status": job.status,
        "target_type": job.target_type,
        "target_id": job.target_id,
        "error_message": job.error_message,
        "retry_count": job.retry_count,
        "created_at": isoformat(job.created_at),
        "finished_at": isoformat(job.finished_at),
    }
    if include_result:
        payload["result_json"] = job.result_json
    return payload


def serialize_entity(entity: Entity) -> dict:
    return {
        "id": entity.id,
        "entity_type": entity.entity_type,
        "canonical_name": entity.canonical_name,
        "display_name": entity.display_name,
        "description": entity.description,
        "aliases": entity.alias_json,
        "confidence_score": entity.confidence_score,
        "first_seen_at": isoformat(entity.first_seen_at),
        "last_seen_at": isoformat(entity.last_seen_at),
        "created_at": isoformat(entity.created_at),
        "updated_at": isoformat(entity.updated_at),
    }


def serialize_event(event: Event) -> dict:
    return {
        "id": event.id,
        "title": event.title,
        "summary": event.summary,
        "description": event.description,
        "event_type": event.event_type,
        "status": event.status,
        "start_time": isoformat(event.start_time),
        "end_time": isoformat(event.end_time),
        "time_precision": event.time_precision,
        "time_text": event.time_text,
        "timeline_sort_time": isoformat(event.timeline_sort_time),
        "location_text": event.location_text,
        "source_note_id": event.source_note_id,
        "confidence_score": event.confidence_score,
        "created_at": isoformat(event.created_at),
        "updated_at": isoformat(event.updated_at),
    }


def serialize_timeline_item(item: TimelineItem) -> dict:
    return {
        "id": item.id,
        "event_id": item.event_id,
        "note_id": item.note_id,
        "title": item.title,
        "summary": item.summary,
        "display_time": item.display_time,
        "sort_time": isoformat(item.sort_time),
        "time_precision": item.time_precision,
    }

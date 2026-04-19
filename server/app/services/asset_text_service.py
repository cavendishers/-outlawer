import json

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.minio import download_bytes
from app.models.asset_derivative import AssetDerivative
from app.models.raw_asset import RawAsset
from app.services.local_media_service import build_local_media_derivative
from app.services.openrouter_service import (
    openrouter_enabled,
    request_openrouter_multimodal_derivative,
)


def get_asset_text(asset: RawAsset, db: Session) -> str:
    if asset.original_text:
        return asset.original_text
    derivative = db.scalar(
        select(AssetDerivative).where(
            and_(
                AssetDerivative.asset_id == asset.id,
                AssetDerivative.derivative_type == "normalized_text",
            )
        )
    )
    if derivative:
        return derivative.content
    generated = generate_asset_text_derivative(asset, db)
    if generated:
        return generated
    return asset.title


def generate_asset_text_derivative(asset: RawAsset, db: Session) -> str:
    if asset.asset_type == "text" or not asset.object_key:
        return ""

    media_bytes = download_bytes(asset.object_key)
    mime_type = asset.mime_type or infer_asset_mime_type(asset.asset_type)

    parsed_text = ""
    derivative_payload: dict[str, object] | None = None
    derivative_meta: dict[str, object] = {
        "asset_type": asset.asset_type,
        "mime_type": mime_type,
        "file_size": asset.file_size,
        "parser": "metadata_fallback",
    }

    local_payload = build_local_media_derivative(asset.asset_type, asset.title, mime_type, media_bytes)
    if local_payload:
        derivative_payload = local_payload
        parsed_text = build_multimodal_canonical_text(asset, derivative_payload)
        derivative_meta = {
            **derivative_meta,
            "parser": str(local_payload.get("parser_name") or "local_media_parser"),
            "short_summary": local_payload.get("short_summary"),
            "observed_time": local_payload.get("observed_time"),
            "confidence": local_payload.get("confidence"),
            "source_attribution": local_payload.get("source_attribution"),
        }

    if openrouter_enabled():
        try:
            openrouter_payload = request_openrouter_multimodal_derivative(
                asset_type=asset.asset_type,
                title=asset.title,
                mime_type=mime_type,
                content=media_bytes,
            )
            derivative_payload = merge_multimodal_payloads(derivative_payload, openrouter_payload)
            parsed_text = build_multimodal_canonical_text(asset, derivative_payload)
            derivative_meta = {
                **derivative_meta,
                "parser": "local_plus_openrouter_multimodal" if local_payload else "openrouter_multimodal",
                "short_summary": derivative_payload.get("short_summary"),
                "observed_people": derivative_payload.get("observed_people"),
                "observed_events": derivative_payload.get("observed_events"),
                "observed_time": derivative_payload.get("observed_time"),
                "observed_location": derivative_payload.get("observed_location"),
                "confidence": derivative_payload.get("confidence"),
                "parsing_notes": derivative_payload.get("parsing_notes"),
                "source_attribution": derivative_payload.get("source_attribution"),
            }
        except Exception as exc:  # noqa: BLE001
            derivative_meta = {
                **derivative_meta,
                "parser_error": str(exc),
            }

    if derivative_payload:
        upsert_asset_derivative(
            db,
            asset_id=asset.id,
            derivative_type="analysis_json",
            content=json.dumps(derivative_payload, ensure_ascii=False),
            meta_json={"asset_type": asset.asset_type, "mime_type": mime_type, "parser": derivative_meta["parser"]},
        )

    if not parsed_text:
        parsed_text = build_multimodal_fallback_text(asset)

    upsert_asset_derivative(
        db,
        asset_id=asset.id,
        derivative_type="normalized_text",
        content=parsed_text,
        meta_json=derivative_meta,
    )
    asset.status = "derived"
    db.add(asset)
    db.flush()
    return parsed_text


def upsert_asset_derivative(
    db: Session,
    *,
    asset_id: str,
    derivative_type: str,
    content: str,
    meta_json: dict[str, object],
) -> AssetDerivative:
    derivative = db.scalar(
        select(AssetDerivative).where(
            and_(
                AssetDerivative.asset_id == asset_id,
                AssetDerivative.derivative_type == derivative_type,
            )
        )
    )
    if derivative:
        derivative.content = content
        derivative.meta_json = meta_json
        db.add(derivative)
        db.flush()
        return derivative

    derivative = AssetDerivative(
        asset_id=asset_id,
        derivative_type=derivative_type,
        content=content,
        meta_json=meta_json,
        version="v1",
    )
    db.add(derivative)
    db.flush()
    return derivative


def build_multimodal_canonical_text(asset: RawAsset, payload: dict[str, object]) -> str:
    sections = [
        f"素材标题：{asset.title}",
        f"素材类型：{asset.asset_type}",
    ]

    canonical_text = safe_multimodal_string(payload.get("canonical_text"))
    if canonical_text:
        sections.append("规范化内容：")
        sections.append(canonical_text)

    short_summary = safe_multimodal_string(payload.get("short_summary"))
    if short_summary:
        sections.append(f"摘要：{short_summary}")

    observed_people = normalize_multimodal_list(payload.get("observed_people"))
    if observed_people:
        sections.append(f"识别人物：{', '.join(observed_people)}")

    observed_events = normalize_multimodal_list(payload.get("observed_events"))
    if observed_events:
        sections.append(f"识别事件：{', '.join(observed_events)}")

    observed_time = normalize_multimodal_list(payload.get("observed_time"))
    if observed_time:
        sections.append(f"识别时间：{', '.join(observed_time)}")

    observed_location = normalize_multimodal_list(payload.get("observed_location"))
    if observed_location:
        sections.append(f"识别地点：{', '.join(observed_location)}")

    parsing_notes = safe_multimodal_string(payload.get("parsing_notes"))
    if parsing_notes:
        sections.append(f"解析说明：{parsing_notes}")

    confidence = payload.get("confidence")
    if isinstance(confidence, (int, float)):
        sections.append(f"解析置信度：{round(float(confidence), 2)}")

    source_attribution = normalize_source_attribution(payload.get("source_attribution"))
    if source_attribution:
        sections.append("来源片段：")
        for item in source_attribution[:8]:
            prefix = item["label"]
            if item["timecode"]:
                prefix = f"{prefix}@{item['timecode']}"
            sections.append(f"- {prefix}: {item['text']}")

    return "\n".join(section for section in sections if section).strip()


def build_multimodal_fallback_text(asset: RawAsset) -> str:
    return (
        f"素材标题：{asset.title}\n"
        f"素材类型：{asset.asset_type}\n"
        f"文件类型：{asset.mime_type or 'unknown'}\n"
        f"文件大小：{asset.file_size or 0} bytes\n"
        "当前未能完成多模态内容识别，已保留原始文件，等待后续重新解析。"
    )


def normalize_multimodal_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def safe_multimodal_string(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def merge_multimodal_payloads(
    local_payload: dict[str, object] | None,
    ai_payload: dict[str, object] | None,
) -> dict[str, object]:
    if local_payload is None:
        return dict(ai_payload or {})
    if ai_payload is None:
        return dict(local_payload)

    merged_source = normalize_source_attribution(local_payload.get("source_attribution")) + normalize_source_attribution(
        ai_payload.get("source_attribution")
    )
    deduped_source: list[dict[str, str | float | None]] = []
    seen_keys: set[tuple[str, str, str | None]] = set()
    for item in merged_source:
        key = (item["source_type"], item["text"], item["timecode"])
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped_source.append(item)

    return {
        "canonical_text": choose_richer_multimodal_text(
            safe_multimodal_string(ai_payload.get("canonical_text")),
            safe_multimodal_string(local_payload.get("canonical_text")),
        ),
        "short_summary": choose_richer_multimodal_text(
            safe_multimodal_string(ai_payload.get("short_summary")),
            safe_multimodal_string(local_payload.get("short_summary")),
        ),
        "observed_people": merge_multimodal_lists(local_payload.get("observed_people"), ai_payload.get("observed_people")),
        "observed_events": merge_multimodal_lists(local_payload.get("observed_events"), ai_payload.get("observed_events")),
        "observed_time": merge_multimodal_lists(local_payload.get("observed_time"), ai_payload.get("observed_time")),
        "observed_location": merge_multimodal_lists(local_payload.get("observed_location"), ai_payload.get("observed_location")),
        "confidence": max_multimodal_confidence(local_payload.get("confidence"), ai_payload.get("confidence")),
        "parsing_notes": "；".join(
            item
            for item in [
                safe_multimodal_string(local_payload.get("parsing_notes")),
                safe_multimodal_string(ai_payload.get("parsing_notes")),
            ]
            if item
        ),
        "parser_name": "local_plus_openrouter_multimodal",
        "source_attribution": deduped_source,
    }


def choose_richer_multimodal_text(primary: str, fallback: str) -> str:
    return primary if len(primary) >= len(fallback) else fallback


def merge_multimodal_lists(left: object, right: object) -> list[str]:
    items: list[str] = []
    for candidate in [*normalize_multimodal_list(left), *normalize_multimodal_list(right)]:
        if candidate not in items:
            items.append(candidate)
    return items


def max_multimodal_confidence(left: object, right: object) -> float | None:
    values = [float(item) for item in [left, right] if isinstance(item, (int, float))]
    return max(values) if values else None


def normalize_source_attribution(value: object) -> list[dict[str, str | float | None]]:
    if not isinstance(value, list):
        return []
    items: list[dict[str, str | float | None]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        text = safe_multimodal_string(item.get("text"))
        source_type = safe_multimodal_string(item.get("source_type"))
        label = safe_multimodal_string(item.get("label")) or source_type
        timecode = safe_multimodal_string(item.get("timecode")) or None
        confidence = item.get("confidence")
        if not text or not source_type:
            continue
        items.append(
            {
                "source_type": source_type,
                "label": label,
                "timecode": timecode,
                "text": text,
                "confidence": float(confidence) if isinstance(confidence, (int, float)) else None,
            }
        )
    return items


def infer_asset_mime_type(asset_type: str) -> str:
    if asset_type == "image":
        return "image/png"
    if asset_type == "audio":
        return "audio/mpeg"
    if asset_type == "video":
        return "video/mp4"
    return "application/octet-stream"

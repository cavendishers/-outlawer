import base64
import json
import logging
import re
from typing import Any

import httpx

from app.core.config import get_settings


logger = logging.getLogger("outlawer.openrouter")

OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"


def openrouter_enabled() -> bool:
    settings = get_settings()
    return bool(settings.openrouter_api_key)


def request_openrouter_extraction(note_id: str, asset_id: str | None, text: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise RuntimeError("OpenRouter API key is not configured")

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    }
    if settings.openrouter_site_url:
        headers["HTTP-Referer"] = settings.openrouter_site_url
    if settings.openrouter_app_name:
        headers["X-OpenRouter-Title"] = settings.openrouter_app_name

    model_candidates = get_model_candidates()
    request_batches = chunk_model_candidates(model_candidates, chunk_size=3)
    if not request_batches:
        request_batches = [[]]

    last_exception: Exception | None = None
    with httpx.Client(timeout=settings.openrouter_timeout_seconds, trust_env=False) as client:
        for batch in request_batches:
            body: dict[str, Any] = {
                "messages": build_messages(note_id, asset_id, text),
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
                "max_tokens": settings.openrouter_max_tokens,
            }
            if batch:
                body["models"] = batch
            elif settings.openrouter_model:
                body["model"] = settings.openrouter_model

            try:
                response = client.post(OPENROUTER_CHAT_COMPLETIONS_URL, headers=headers, json=body)
                response.raise_for_status()
                payload = response.json()
                content = extract_message_content(payload)
                logger.info(
                    "openrouter_extraction_completed note_id=%s model=%s batch=%s",
                    note_id,
                    payload.get("model") or (batch[0] if batch else settings.openrouter_model) or "account-default",
                    ",".join(batch) if batch else "account-default",
                )
                return json.loads(content)
            except Exception as exc:  # noqa: BLE001
                last_exception = exc
                logger.warning(
                    "openrouter_extraction_batch_failed note_id=%s batch=%s error=%s",
                    note_id,
                    ",".join(batch) if batch else "account-default",
                    exc,
                )
                continue

    if last_exception is not None:
        raise last_exception
    raise RuntimeError("OpenRouter extraction failed without an explicit error")


def request_openrouter_multimodal_derivative(
    *,
    asset_type: str,
    title: str,
    mime_type: str,
    content: bytes,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise RuntimeError("OpenRouter API key is not configured")
    if len(content) > settings.openrouter_multimodal_max_bytes:
        raise ValueError(
            f"Media file is too large for direct multimodal parsing: {len(content)} bytes"
        )

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    }
    if settings.openrouter_site_url:
        headers["HTTP-Referer"] = settings.openrouter_site_url
    if settings.openrouter_app_name:
        headers["X-OpenRouter-Title"] = settings.openrouter_app_name

    body: dict[str, Any] = {
        "model": settings.openrouter_multimodal_model,
        "messages": build_multimodal_messages(asset_type, title, mime_type, content),
        "temperature": 0.1,
        "max_tokens": settings.openrouter_max_tokens,
    }

    with httpx.Client(timeout=settings.openrouter_timeout_seconds, trust_env=False) as client:
        response = client.post(OPENROUTER_CHAT_COMPLETIONS_URL, headers=headers, json=body)
        response.raise_for_status()
        payload = response.json()
        content_text = extract_message_content(payload)
        logger.info(
            "openrouter_multimodal_derivative_completed asset_type=%s model=%s",
            asset_type,
            payload.get("model") or settings.openrouter_multimodal_model,
        )
        return extract_json_object(content_text)


def get_model_candidates() -> list[str]:
    settings = get_settings()
    candidates: list[str] = []
    if settings.openrouter_model:
        candidates.append(settings.openrouter_model)
    candidates.extend(
        candidate.strip()
        for candidate in settings.openrouter_models.split(",")
        if candidate.strip()
    )

    deduped_candidates: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        deduped_candidates.append(candidate)
    return deduped_candidates


def chunk_model_candidates(candidates: list[str], chunk_size: int = 3) -> list[list[str]]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    return [candidates[index : index + chunk_size] for index in range(0, len(candidates), chunk_size)]


def build_messages(note_id: str, asset_id: str | None, text: str) -> list[dict[str, Any]]:
    return [
        {
            "role": "system",
            "content": (
                "You extract structured knowledge from notes. "
                "Return valid JSON only. Do not wrap in markdown fences. "
                "The response must be an object with keys: summary, entities, events, similarity_hints, style_payload. "
                "Use Chinese when the source text is Chinese. "
                "Keep facts conservative and do not invent unsupported details."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "task": "Extract structured knowledge for an online knowledge base",
                    "context": {
                        "note_id": note_id,
                        "asset_id": asset_id,
                        "content_type": "text",
                        "language_hint": "zh-CN",
                    },
                    "requirements": {
                        "summary": {
                            "title": "string",
                            "short_summary": "string",
                            "canonical_text": "string",
                            "category": "string",
                            "tags": ["string"],
                        },
                        "entities": [
                            {
                                "temp_id": "string",
                                "entity_type": "person | org | place | concept",
                                "name": "string",
                                "canonical_name": "string",
                                "aliases": ["string"],
                                "description": "string | null",
                                "confidence": "number",
                                "evidence": [{"text": "string", "start": "number | null", "end": "number | null"}],
                            }
                        ],
                        "events": [
                            {
                                "temp_id": "string",
                                "title": "string",
                                "event_type": "string",
                                "summary": "string",
                                "description": "string",
                                "time": {
                                    "time_text": "string | null",
                                    "start_time": "ISO-8601 string | null",
                                    "end_time": "ISO-8601 string | null",
                                    "time_precision": "exact | day | month | year | range | unknown",
                                    "timeline_sort_time": "ISO-8601 string",
                                },
                                "participants": [
                                    {
                                        "entity_temp_id": "string | null",
                                        "entity_name": "string | null",
                                        "role": "string | null",
                                        "relation_type": "string",
                                    }
                                ],
                                "locations": [{"name": "string", "entity_temp_id": "string | null"}],
                                "confidence": "number",
                                "evidence": [{"text": "string", "start": "number | null", "end": "number | null"}],
                            }
                        ],
                        "similarity_hints": [
                            {
                                "target_type": "note | event | entity",
                                "target_id": "string",
                                "reason": "string",
                                "confidence": "number",
                            }
                        ],
                        "style_payload": {
                            "theme": "chunibyo",
                            "title": "string",
                            "character_cards": [
                                {
                                    "entity_temp_id": "string | null",
                                    "entity_name": "string | null",
                                    "display_name": "string",
                                    "epithet": "string",
                                    "aura": "string",
                                }
                            ],
                            "event_narrative": [
                                {
                                    "event_temp_id": "string | null",
                                    "headline": "string",
                                    "body": "string",
                                }
                            ],
                        },
                    },
                    "source_text": text,
                },
                ensure_ascii=False,
            ),
        },
    ]


def build_multimodal_messages(
    asset_type: str,
    title: str,
    mime_type: str,
    content: bytes,
) -> list[dict[str, Any]]:
    instruction = (
        "Analyze this uploaded source material for an AI knowledge base. "
        "Return valid JSON only. Do not wrap in markdown fences. "
        "Use Chinese by default. Preserve observed facts and avoid unsupported speculation. "
        "The JSON object must contain: canonical_text, short_summary, observed_people, "
        "observed_events, observed_time, observed_location, observed_scene, observed_objects, "
        "observed_actions, document_type, image_layout, confidence, parsing_notes, "
        "source_attribution, video_scene_segments. "
        "For images, include OCR text when visible plus scene, objects, likely activity, and document or photo type. For audio, include transcript when speech exists. "
        "For video, include visible scene description, spoken transcript if available, and key moments. "
        "Use evidence_type=direct_observation only for text that is directly visible or transcribed. "
        "Use evidence_type=model_inference for inferred descriptions or context. "
        "Use evidence_type=mixed only when one item combines direct observation and inference."
    )
    return [
        {
            "role": "system",
            "content": (
                "You convert multimodal source material into normalized text for a knowledge graph pipeline. "
                "Return JSON only."
            ),
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "task": "Create normalized text and observations from uploaded media",
                            "asset": {
                                "title": title,
                                "asset_type": asset_type,
                                "mime_type": mime_type,
                            },
                            "requirements": instruction,
                            "response_schema": {
                                "canonical_text": "string",
                                "short_summary": "string",
                                "observed_people": ["string"],
                                "observed_events": ["string"],
                                "observed_time": ["string"],
                                "observed_location": ["string"],
                                "observed_scene": ["string"],
                                "observed_objects": ["string"],
                                "observed_actions": ["string"],
                                "document_type": "string | null",
                                "image_layout": "string | null",
                                "confidence": "number between 0 and 1",
                                "parsing_notes": "string",
                                "source_attribution": [
                                    {
                                        "source_type": "image_ocr | image_visual_observation | image_scene_inference | audio_transcript | video_frame_ocr | video_audio_transcript | video_scene_inference",
                                        "label": "string",
                                        "timecode": "HH:MM:SS string or null",
                                        "text": "observed or inferred snippet",
                                        "confidence": "number between 0 and 1",
                                        "evidence_type": "direct_observation | model_inference | mixed",
                                    }
                                ],
                                "video_scene_segments": [
                                    {
                                        "segment_index": "integer",
                                        "start_timecode": "HH:MM:SS string or null",
                                        "end_timecode": "HH:MM:SS string or null",
                                        "label": "string",
                                        "observed_text": "direct OCR/transcript evidence only",
                                        "inferred_context": "model inferred context only",
                                        "description": "short scene description",
                                        "confidence": "number between 0 and 1",
                                        "evidence_type": "direct_observation | model_inference | mixed",
                                    }
                                ],
                            },
                        },
                        ensure_ascii=False,
                    ),
                },
                build_media_content_item(asset_type, mime_type, content),
            ],
        },
    ]


def build_media_content_item(asset_type: str, mime_type: str, content: bytes) -> dict[str, Any]:
    encoded = base64.b64encode(content).decode("ascii")
    data_url = f"data:{mime_type};base64,{encoded}"
    if asset_type == "image":
        return {"type": "image_url", "image_url": {"url": data_url}}
    if asset_type == "audio":
        return {
            "type": "input_audio",
            "input_audio": {
                "data": encoded,
                "format": infer_audio_format(mime_type),
            },
        }
    if asset_type == "video":
        return {"type": "video_url", "video_url": {"url": data_url}}
    raise ValueError(f"Unsupported multimodal asset type: {asset_type}")


def infer_audio_format(mime_type: str) -> str:
    subtype = mime_type.split("/")[-1].lower().split(";")[0]
    if subtype in {"mpeg", "mp3"}:
        return "mp3"
    if subtype in {"wav", "wave", "x-wav"}:
        return "wav"
    if subtype in {"m4a", "mp4", "aac", "ogg", "webm", "flac"}:
        return subtype
    return "mp3"


def extract_json_object(content: str) -> dict[str, Any]:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if not match:
        raise ValueError("OpenRouter response did not contain a JSON object")
    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("OpenRouter JSON response was not an object")
    return parsed


def extract_message_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        raise ValueError("OpenRouter response did not include choices")

    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                text_parts.append(item["text"])
        if text_parts:
            return "".join(text_parts)
    raise ValueError("OpenRouter response content was not a JSON string")

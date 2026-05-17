import base64
import json
import logging
import re
from typing import Any

from openai import OpenAI

from app.core.config import get_settings
from app.domains.extraction.openrouter import extract_json_object, infer_audio_format


logger = logging.getLogger("outlawer.bailian")


def bailian_multimodal_enabled(asset_type: str) -> bool:
    settings = get_settings()
    if not settings.bailian_api_key:
        return False
    if asset_type in {"image", "video"}:
        return settings.vision_provider.lower() == "bailian"
    if asset_type == "audio":
        return settings.audio_transcription_provider.lower() == "bailian"
    return False


def request_bailian_multimodal_derivative(
    *,
    asset_type: str,
    title: str,
    mime_type: str,
    content: bytes,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.bailian_api_key:
        raise RuntimeError("Bailian API key is not configured")
    if len(content) > settings.bailian_multimodal_max_bytes:
        raise ValueError(
            f"Media file is too large for Bailian multimodal parsing: {len(content)} bytes"
        )

    client = OpenAI(
        api_key=settings.bailian_api_key,
        base_url=settings.bailian_base_url,
        timeout=settings.bailian_timeout_seconds,
    )
    model = choose_bailian_model(asset_type)
    messages = build_bailian_multimodal_messages(
        asset_type=asset_type,
        title=title,
        mime_type=mime_type,
        content=content,
    )
    extra_body = build_bailian_extra_body(asset_type)

    if asset_type == "audio" and settings.bailian_audio_stream:
        response_text = request_streaming_text(
            client=client,
            model=model,
            messages=messages,
            extra_body=extra_body,
        )
    else:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.1,
            extra_body=extra_body or None,
        )
        response_text = extract_openai_message_text(response)

    payload = extract_json_object(response_text)
    payload["parser_name"] = f"bailian_{asset_type}_model"
    payload["provider_name"] = "bailian"
    payload["model_name"] = model
    logger.info("bailian_multimodal_derivative_completed asset_type=%s model=%s", asset_type, model)
    return payload


def request_streaming_text(
    *,
    client: OpenAI,
    model: str,
    messages: list[dict[str, Any]],
    extra_body: dict[str, Any],
) -> str:
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.1,
        stream=True,
        extra_body=extra_body,
    )
    chunks: list[str] = []
    for chunk in stream:
        choices = getattr(chunk, "choices", None) or []
        if not choices:
            continue
        delta = getattr(choices[0], "delta", None)
        content = getattr(delta, "content", None)
        if isinstance(content, str):
            chunks.append(content)
        elif isinstance(content, list):
            chunks.extend(
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and isinstance(item.get("text"), str)
            )
    response_text = "".join(chunks).strip()
    if not response_text:
        raise ValueError("Bailian streaming response did not contain text content")
    return response_text


def choose_bailian_model(asset_type: str) -> str:
    settings = get_settings()
    if asset_type == "audio":
        return settings.bailian_audio_model
    if asset_type == "video":
        return settings.bailian_video_model
    if asset_type == "image":
        return settings.bailian_vision_model
    raise ValueError(f"Unsupported Bailian multimodal asset type: {asset_type}")


def build_bailian_extra_body(asset_type: str) -> dict[str, Any]:
    settings = get_settings()
    if asset_type == "audio":
        return {"modalities": ["text"]}
    if asset_type == "video":
        return {"vl_high_resolution_images": True, "fps": settings.bailian_video_fps}
    return {"vl_high_resolution_images": True}


def build_bailian_multimodal_messages(
    *,
    asset_type: str,
    title: str,
    mime_type: str,
    content: bytes,
) -> list[dict[str, Any]]:
    return [
        {
            "role": "system",
            "content": (
                "你负责把图片、音频或视频转成知识库可用的结构化观察结果。"
                "只返回 JSON，不要使用 Markdown 代码块。"
            ),
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "task": "解析多模态素材，生成知识图谱前置文本",
                            "asset": {
                                "title": title,
                                "asset_type": asset_type,
                                "mime_type": mime_type,
                            },
                            "requirements": (
                                "用中文输出。必须保守区分直接观察和模型推断。"
                                "图片需要识别可见文字、人物、场景、物件、动作。"
                                "音频需要转写可听内容，提取说话人提示、议题、决策、跟进项。"
                                "视频需要识别关键画面、可见文字、可听内容和关键片段。"
                                "JSON 字段必须包含 canonical_text, short_summary, observed_people, "
                                "observed_events, observed_time, observed_location, observed_scene, "
                                "observed_objects, observed_actions, document_type, image_layout, "
                                "speaker_hints, observed_topics, observed_decisions, observed_follow_ups, "
                                "conversation_type, audio_segments, confidence, parsing_notes, "
                                "source_attribution, video_scene_segments。"
                            ),
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
                                "speaker_hints": ["string"],
                                "observed_topics": ["string"],
                                "observed_decisions": ["string"],
                                "observed_follow_ups": ["string"],
                                "conversation_type": "string | null",
                                "audio_segments": [
                                    {
                                        "segment_index": "integer",
                                        "label": "string",
                                        "start_timecode": "HH:MM:SS string or null",
                                        "end_timecode": "HH:MM:SS string or null",
                                        "speaker_hint": "string | null",
                                        "transcript": "string",
                                        "confidence": "number between 0 and 1",
                                        "evidence_type": "direct_observation | model_inference | mixed",
                                    }
                                ],
                                "confidence": "number between 0 and 1",
                                "parsing_notes": "string",
                                "source_attribution": [
                                    {
                                        "source_type": (
                                            "image_ocr | image_visual_observation | image_scene_inference | "
                                            "audio_transcript | audio_segment_transcript | video_frame_ocr | "
                                            "video_audio_transcript | video_scene_inference"
                                        ),
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
                build_bailian_media_content_item(asset_type, mime_type, content),
            ],
        },
    ]


def build_bailian_media_content_item(asset_type: str, mime_type: str, content: bytes) -> dict[str, Any]:
    encoded = base64.b64encode(content).decode("ascii")
    data_url = f"data:{mime_type};base64,{encoded}"
    if asset_type == "image":
        return {"type": "image_url", "image_url": {"url": data_url}}
    if asset_type == "video":
        return {"type": "video_url", "video_url": {"url": data_url}}
    if asset_type == "audio":
        return {
            "type": "input_audio",
            "input_audio": {
                "data": data_url,
                "format": infer_audio_format(mime_type),
            },
        }
    raise ValueError(f"Unsupported Bailian multimodal asset type: {asset_type}")


def extract_openai_message_text(response: Any) -> str:
    choices = getattr(response, "choices", None)
    if not choices:
        raise ValueError("Bailian response did not include choices")
    message = getattr(choices[0], "message", None)
    content = getattr(message, "content", None)
    if isinstance(content, str) and content.strip():
        return content
    if isinstance(content, list):
        text = "".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and isinstance(item.get("text"), str)
        ).strip()
        if text:
            return text
    raise ValueError("Bailian response did not contain message text")


def extract_json_from_text(content: str) -> dict[str, Any]:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    parsed = json.loads(stripped)
    if not isinstance(parsed, dict):
        raise ValueError("Bailian JSON response was not an object")
    return parsed

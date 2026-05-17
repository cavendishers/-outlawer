from __future__ import annotations

import json
import logging
from typing import Any

from app.core.config import get_settings


logger = logging.getLogger("outlawer.chat_provider")


class ChatModelProvider:
    def extract_structured_knowledge(self, note_id: str, asset_id: str | None, text: str) -> dict[str, Any]:
        raise NotImplementedError


class DeepSeekChatModelProvider(ChatModelProvider):
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.chat_api_key
        self.base_url = (base_url or settings.chat_base_url).rstrip("/")
        self.model = model or settings.chat_model
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else settings.chat_timeout_seconds

    def extract_structured_knowledge(self, note_id: str, asset_id: str | None, text: str) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("CHAT_API_KEY is not configured")
        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:  # pragma: no cover - runtime dependency guard
            raise RuntimeError("openai package is not installed") from exc

        client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout_seconds,
        )
        response = client.chat.completions.create(
            model=self.model,
            messages=_build_messages(note_id, asset_id, text),
            temperature=0.2,
            max_tokens=2200,
            response_format={"type": "json_object"},
            extra_body={"thinking": {"type": "disabled"}},
        )
        content = _extract_response_text(response)
        logger.info("deepseek_extraction_completed note_id=%s model=%s", note_id, self.model)
        return _extract_json_object(content)


def build_chat_model_provider() -> ChatModelProvider:
    settings = get_settings()
    provider_name = settings.chat_provider.strip().lower()
    if provider_name == "deepseek":
        return DeepSeekChatModelProvider()
    raise ValueError(f"Unsupported chat provider: {settings.chat_provider}")


def chat_provider_enabled() -> bool:
    settings = get_settings()
    provider_name = settings.chat_provider.strip().lower()
    if provider_name != "deepseek":
        return False
    return bool(settings.chat_api_key)


def _build_messages(note_id: str, asset_id: str | None, text: str) -> list[dict[str, Any]]:
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


def _extract_response_text(response: Any) -> str:
    choices = getattr(response, "choices", None)
    if isinstance(choices, list) and choices:
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if isinstance(content, str) and content.strip():
            return content
    raise ValueError("OpenAI chat completion did not contain message content")


def _extract_json_object(content: str) -> dict[str, Any]:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = stripped.removeprefix("```json").removeprefix("```").strip()
        if stripped.endswith("```"):
            stripped = stripped[:-3].strip()
    parsed = json.loads(stripped)
    if not isinstance(parsed, dict):
        raise ValueError("Chat provider response was not a JSON object")
    return parsed

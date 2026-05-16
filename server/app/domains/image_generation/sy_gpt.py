from __future__ import annotations

import base64
import json
import re
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import get_settings

GPT_IMAGE_BASE_MODEL = "gpt-image-2"
ASPECT_RATIO_TO_SUFFIX = {
    "16:9": "landscape",
    "9:16": "portrait",
    "1:1": "square",
    "4:3": "four-three",
    "3:4": "three-four",
}
SUFFIX_TO_ASPECT_RATIO = {value: key for key, value in ASPECT_RATIO_TO_SUFFIX.items()}


@dataclass(frozen=True)
class ResolvedImageModel:
    request_model: str
    aspect_ratio: str
    image_size: str


@dataclass(frozen=True)
class ImageGenerationResult:
    image_urls: list[str]
    upstream_task_id: str
    raw_response: dict[str, Any]


class SyGPTImageClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float | None = None,
        poll_interval_seconds: float | None = None,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.sy_gpt_base_url).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.sy_gpt_api_key
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else settings.sy_gpt_timeout_seconds
        self.poll_interval_seconds = (
            poll_interval_seconds if poll_interval_seconds is not None else settings.sy_gpt_poll_interval_seconds
        )

    def generate(
        self,
        *,
        prompt: str,
        model: str | None,
        aspect_ratio: str | None,
        image_size: str | None,
        reference_images: list[dict[str, str]],
    ) -> ImageGenerationResult:
        if not self.api_key:
            raise ValueError("SY_GPT_API_KEY is not configured")

        resolved = resolve_model_config(model, aspect_ratio, image_size)
        request_body = build_generation_request(prompt=prompt, resolved=resolved, reference_images=reference_images)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-Async": "true",
        }
        with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds, headers=headers) as client:
            create_response = client.post("/v1/chat/completions", json=request_body)
            create_response.raise_for_status()
            create_data = normalize_response_body(create_response)
            task_id = extract_task_id(create_data)
            if not task_id:
                raise ValueError("No task id in response")
            raw_response = {"create": create_data, "task": None}
            deadline = time.monotonic() + self.timeout_seconds
            while time.monotonic() < deadline:
                task_response = client.get(f"/v1/tasks/{task_id}")
                task_response.raise_for_status()
                task_data = resolve_task_payload(normalize_response_body(task_response))
                raw_response["task"] = task_data
                status = map_task_status(str(task_data.get("status") or ""))
                if status == "completed":
                    image_urls = extract_images(task_data)
                    if not image_urls:
                        raise ValueError("No images in response")
                    return ImageGenerationResult(image_urls=image_urls, upstream_task_id=task_id, raw_response=raw_response)
                if status in {"failed", "cancelled"}:
                    raise ValueError(extract_task_error(task_data) or f"Generation {status}")
                time.sleep(self.poll_interval_seconds)

        raise TimeoutError("Image generation timed out")


def resolve_model_config(
    requested_model: str | None,
    aspect_ratio: str | None,
    image_size: str | None,
) -> ResolvedImageModel:
    model_name = (requested_model or GPT_IMAGE_BASE_MODEL).strip().lower()
    if not model_name.startswith(GPT_IMAGE_BASE_MODEL):
        raise ValueError(f"Invalid model for sy_gpt: {requested_model}. Only gpt-image-2 models are supported")

    normalized_aspect = normalize_aspect_ratio(aspect_ratio)
    normalized_size = normalize_image_size(image_size)
    if model_name == GPT_IMAGE_BASE_MODEL:
        return ResolvedImageModel(
            request_model=GPT_IMAGE_BASE_MODEL,
            aspect_ratio=normalized_aspect,
            image_size=normalized_size,
        )

    match = re.match(r"^gpt-image-2-(landscape|portrait|square|four-three|three-four)(?:-(2k|4k))?$", model_name)
    if not match:
        raise ValueError(f"Invalid model for sy_gpt: {requested_model}. Unsupported gpt-image-2 variant")
    aspect_suffix, resolution_suffix = match.groups()
    if resolution_suffix == "4k":
        raise ValueError(f"Invalid model for sy_gpt: {requested_model}. GPT Image 2 does not support 4K")

    variant_size = "2K" if resolution_suffix == "2k" else "1K"
    return ResolvedImageModel(
        request_model=f"{GPT_IMAGE_BASE_MODEL}-{aspect_suffix}{'-2k' if variant_size == '2K' else ''}",
        aspect_ratio=SUFFIX_TO_ASPECT_RATIO[aspect_suffix],
        image_size=variant_size,
    )


def normalize_aspect_ratio(aspect_ratio: str | None) -> str:
    return aspect_ratio if aspect_ratio in ASPECT_RATIO_TO_SUFFIX else "9:16"


def normalize_image_size(image_size: str | None) -> str:
    return "2K" if str(image_size or "").strip().lower() == "2k" else "1K"


def build_generation_request(
    *,
    prompt: str,
    resolved: ResolvedImageModel,
    reference_images: list[dict[str, str]],
) -> dict[str, Any]:
    content: list[dict[str, Any]] = [
        {"type": "image_url", "image_url": {"url": to_data_url(image["base64"], image["mime_type"])}}
        for image in reference_images
    ]
    content.append({"type": "text", "text": prompt})
    return {
        "model": resolved.request_model,
        "async": True,
        "messages": [{"role": "user", "content": content if reference_images else prompt}],
        "generationConfig": {
            "imageConfig": {
                "aspectRatio": resolved.aspect_ratio,
                "imageSize": resolved.image_size,
            },
        },
    }


def to_data_url(value: str, mime_type: str) -> str:
    trimmed = value.strip()
    if trimmed.startswith("data:image/"):
        return trimmed
    return f"data:{mime_type or 'image/png'};base64,{trimmed}"


def normalize_response_body(response: httpx.Response) -> Any:
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        return response.json()
    text = response.text.strip()
    if not text:
        raise ValueError("Empty response body")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Upstream returned non-JSON response") from exc


def extract_task_id(data: Any) -> str | None:
    if not isinstance(data, dict):
        return None
    nested = data.get("data")
    nested_id = nested.get("id") or nested.get("task_id") if isinstance(nested, dict) else None
    return data.get("id") or data.get("task_id") or nested_id


def resolve_task_payload(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    if data.get("status"):
        return data
    nested = data.get("data")
    if isinstance(nested, dict) and nested.get("status"):
        return nested
    return nested if isinstance(nested, dict) else data


def map_task_status(status: str) -> str:
    normalized = status.lower()
    if normalized in {"queued", "pending"}:
        return "pending"
    if normalized in {"processing", "running"}:
        return "processing"
    if normalized in {"completed", "succeeded", "success"}:
        return "completed"
    if normalized == "failed":
        return "failed"
    if normalized in {"cancelled", "canceled"}:
        return "cancelled"
    return "processing"


def extract_task_error(data: dict[str, Any]) -> str | None:
    error = data.get("error")
    if not error:
        return None
    if isinstance(error, str):
        return error
    if isinstance(error, dict) and isinstance(error.get("message"), str):
        return error["message"]
    return json.dumps(error, ensure_ascii=False)


def extract_images(data: Any) -> list[str]:
    images = unique_images(
        [
            *extract_images_from_urls(data.get("urls") if isinstance(data, dict) else None),
            *extract_images_from_nested_result(data),
            *extract_images_from_choices(data),
            *extract_images_from_output(data),
            *extract_images_from_data_field(data.get("data") if isinstance(data, dict) else None),
            *extract_inline_images(data),
        ]
    )
    return images


def extract_images_from_nested_result(data: Any) -> list[str]:
    if isinstance(data, dict) and data.get("result"):
        return extract_images(data["result"])
    return []


def extract_images_from_urls(urls: Any) -> list[str]:
    if not urls:
        return []
    candidates = urls if isinstance(urls, list) else [urls]
    return unique_images([image for candidate in candidates for image in normalize_image_candidate(candidate, "image/png")])


def extract_images_from_choices(data: Any) -> list[str]:
    choices = data.get("choices") if isinstance(data, dict) else []
    if not isinstance(choices, list):
        return []
    images: list[str] = []
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
        delta = choice.get("delta") if isinstance(choice.get("delta"), dict) else {}
        images.extend(extract_images_from_any_content(message.get("content")))
        images.extend(extract_images_from_any_content(delta.get("content")))
    return unique_images(images)


def extract_images_from_output(data: Any) -> list[str]:
    output = data.get("output") if isinstance(data, dict) else []
    if not isinstance(output, list):
        return []
    return unique_images([image for item in output for image in extract_images_from_any_content(item.get("content"))])


def extract_images_from_any_content(content: Any) -> list[str]:
    if isinstance(content, str):
        return extract_image_urls_from_text(content)
    if not isinstance(content, list):
        return []
    return unique_images([image for item in content for image in extract_known_image_fields(item)])


def extract_images_from_data_field(data_field: Any) -> list[str]:
    if not data_field:
        return []
    items = data_field if isinstance(data_field, list) else [data_field]
    return unique_images([image for item in items for image in extract_known_image_fields(item)])


def extract_known_image_fields(item: Any) -> list[str]:
    if not isinstance(item, dict):
        return []
    mime_type = item.get("mime_type") or item.get("mimeType") or "image/png"
    candidates = [item.get("image_url"), item.get("url"), item.get("b64_json"), item.get("base64"), item.get("image")]
    return unique_images([image for candidate in candidates for image in normalize_image_candidate(candidate, mime_type)])


def normalize_image_candidate(candidate: Any, mime_type: str) -> list[str]:
    if not candidate:
        return []
    if isinstance(candidate, list):
        return unique_images([image for item in candidate for image in normalize_image_candidate(item, mime_type)])
    if isinstance(candidate, dict):
        nested_mime = candidate.get("mime_type") or candidate.get("mimeType") or mime_type
        return unique_images(
            [
                image
                for value in (
                    candidate.get("url"),
                    candidate.get("image_url"),
                    candidate.get("b64_json"),
                    candidate.get("base64"),
                    candidate.get("data"),
                )
                for image in normalize_image_candidate(value, nested_mime)
            ]
        )
    if not isinstance(candidate, str):
        return []
    trimmed = candidate.strip()
    if not trimmed:
        return []
    if trimmed.startswith("data:image/") or re.match(r"^https?://", trimmed, re.IGNORECASE):
        return [trimmed]
    if looks_like_base64(trimmed):
        return [f"data:{mime_type or 'image/png'};base64,{trimmed}"]
    return []


def extract_inline_images(data: Any, seen: set[int] | None = None, depth: int = 0) -> list[str]:
    if seen is None:
        seen = set()
    if not isinstance(data, (dict, list)) or id(data) in seen or depth > 5:
        return []
    seen.add(id(data))
    direct: list[str] = []
    if isinstance(data, dict):
        inline_data = data.get("inlineData") or data.get("inline_data")
        if isinstance(inline_data, dict) and inline_data.get("data"):
            direct.extend(normalize_image_candidate(inline_data["data"], inline_data.get("mimeType") or inline_data.get("mime_type") or "image/png"))
        direct.extend(normalize_image_candidate(data.get("b64_json"), data.get("mime_type") or data.get("mimeType") or "image/png"))
        direct.extend(normalize_image_candidate(data.get("base64"), data.get("mime_type") or data.get("mimeType") or "image/png"))
        direct.extend(normalize_image_candidate(data.get("image_base64"), data.get("mime_type") or data.get("mimeType") or "image/png"))
        children = data.values()
    else:
        children = data
    return unique_images([*direct, *[image for child in children for image in extract_inline_images(child, seen, depth + 1)]])


def extract_image_urls_from_text(text: str) -> list[str]:
    images: list[str] = []
    for match in re.finditer(r"!\[[^\]]*]\(([^)]+)\)", text):
        images.extend(normalize_image_candidate(match.group(1), "image/png"))
    for match in re.finditer(r"https?://[^\s)]+", text, re.IGNORECASE):
        candidate = match.group(0)
        if not candidate.endswith((")", ".")):
            images.extend(normalize_image_candidate(candidate, "image/png"))
    for line in text.splitlines():
        trimmed = line.strip()
        if not trimmed.startswith("data:"):
            continue
        payload = trimmed[5:].strip()
        if not payload or payload == "[DONE]":
            continue
        try:
            images.extend(extract_images(json.loads(payload)))
        except json.JSONDecodeError:
            continue
    return unique_images(images)


def looks_like_base64(value: str) -> bool:
    return len(value) > 64 and re.match(r"^[A-Za-z0-9+/=\s]+$", value) is not None


def decode_data_url(value: str) -> tuple[bytes, str] | None:
    match = re.match(r"^data:(image/[^;]+);base64,(.+)$", value, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    mime_type, payload = match.groups()
    return base64.b64decode(payload), mime_type


def unique_images(images: list[str]) -> list[str]:
    return list(dict.fromkeys([image for image in images if image]))

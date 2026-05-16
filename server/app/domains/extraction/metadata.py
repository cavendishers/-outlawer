from __future__ import annotations

import hashlib
from typing import Any


EXTRACTION_SCHEMA_VERSION = "ai-extraction-format-v1"
PROMPT_VERSION_BY_EXTRACTOR = {
    "openrouter": "text-openrouter-v1",
    "deepseek": "text-deepseek-v1",
    "heuristic_pipeline": "text-heuristic-v1",
}


def resolve_extraction_run_metadata(
    payload: dict[str, Any],
    *,
    text: str,
    parent_run_id: str | None,
    run_kind: str,
) -> dict[str, str | None]:
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    extractor_name = _safe_string(source.get("extractor_name"), "heuristic_pipeline")
    extractor_version = _safe_string(source.get("extractor_version"), "v1")
    if extractor_name == "deepseek":
        provider_name = "deepseek"
        model_name = extractor_version
    elif extractor_name == "openrouter":
        provider_name = "openrouter"
        model_name = extractor_version
    else:
        provider_name = "local"
        model_name = extractor_name
    prompt_version = PROMPT_VERSION_BY_EXTRACTOR.get(extractor_name, "text-heuristic-v1")
    input_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {
        "provider_name": provider_name,
        "model_name": model_name,
        "prompt_version": prompt_version,
        "schema_version": EXTRACTION_SCHEMA_VERSION,
        "input_hash": input_hash,
        "parent_run_id": parent_run_id,
        "run_kind": run_kind,
    }


def _safe_string(value: Any, fallback: str) -> str:
    candidate = str(value or "").strip()
    return candidate or fallback

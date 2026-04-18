from math import ceil
from typing import Any


def ok(data: Any) -> dict[str, Any]:
    return {
        "code": 0,
        "message": "ok",
        "data": data,
    }


def paginated(
    *,
    items: list[Any],
    total: int,
    page: int,
    page_size: int,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": ceil(total / page_size) if page_size else 0,
    }
    if extra:
        payload.update(extra)
    return ok(payload)

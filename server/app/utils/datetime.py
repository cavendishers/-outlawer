import re
from datetime import UTC, datetime


def extract_time(text: str) -> tuple[datetime | None, str | None, str]:
    patterns = [
        (r"(\d{4}-\d{2}-\d{2})", "%Y-%m-%d", "day"),
        (r"(\d{4}/\d{2}/\d{2})", "%Y/%m/%d", "day"),
        (r"(\d{4}年\d{1,2}月\d{1,2}日)", "%Y年%m月%d日", "day"),
    ]
    for pattern, fmt, precision in patterns:
        match = re.search(pattern, text)
        if match:
            return datetime.strptime(match.group(1), fmt).replace(tzinfo=UTC), match.group(1), precision
    return datetime.now(UTC), None, "unknown"

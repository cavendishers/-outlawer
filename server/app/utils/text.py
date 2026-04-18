import re
from collections import Counter


STOPWORDS = {
    "我们",
    "他们",
    "进行",
    "项目",
    "会议",
    "启动",
    "计划",
    "讨论",
    "记录",
    "内容",
    "时间",
    "事件",
}


def normalize_name(value: str) -> str:
    cleaned = re.sub(r"\s+", "", value.strip().lower())
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]", "", cleaned)


def summarize_text(text: str, limit: int = 120) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "…"


def extract_tags(text: str, limit: int = 5) -> list[str]:
    words = re.findall(r"[A-Za-z]{3,}|[\u4e00-\u9fff]{2,4}", text)
    ranked = Counter(word for word in words if word not in STOPWORDS)
    return [word for word, _ in ranked.most_common(limit)]


def text_to_vector(text: str, size: int = 8) -> list[float]:
    vector = [0.0] * size
    if not text:
        return vector
    for index, char in enumerate(text):
        slot = index % size
        vector[slot] += (ord(char) % 97) / 97
    length = max(len(text), 1)
    return [round(value / length, 6) for value in vector]

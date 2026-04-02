import re
from collections import Counter
from typing import Any, Dict, List


STOPWORDS = {
    "the",
    "and",
    "for",
    "this",
    "that",
    "with",
    "you",
    "are",
    "was",
    "have",
    "from",
    "一个",
    "用于",
    "这个",
    "以及",
    "进行",
    "可以",
}


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def split_tokens(text: str, *, min_token_length: int) -> List[str]:
    raw_tokens = re.findall(r"[\u4e00-\u9fffA-Za-z0-9_]+", text.lower())
    return [
        token
        for token in raw_tokens
        if len(token) >= min_token_length and token not in STOPWORDS and not token.isdigit()
    ]


def analyze_text(
    text: str,
    *,
    max_keywords: int,
    min_token_length: int,
    warn_length: int,
) -> Dict[str, Any]:
    normalized = normalize_text(text)
    if not normalized:
        raise ValueError("text 不能为空")

    lines = [line for line in text.splitlines() if line.strip()]
    words = [token for token in re.split(r"\s+", normalized) if token]
    sentences = [item for item in re.split(r"[。！？!?\.]+", normalized) if item.strip()]
    tokens = split_tokens(normalized, min_token_length=min_token_length)
    keyword_counts = Counter(tokens).most_common(max_keywords)

    return {
        "normalized_text": normalized,
        "char_count": len(normalized),
        "word_count": len(words),
        "line_count": len(lines) if lines else (1 if normalized else 0),
        "sentence_count": len(sentences),
        "keywords": [{"term": term, "count": count} for term, count in keyword_counts],
        "flags": {
            "is_empty": False,
            "is_long_text": len(normalized) > warn_length,
        },
    }


from __future__ import annotations

import re
from collections.abc import Iterable


_RE_WHITESPACE = re.compile(r"\s+")
_RE_CJK = re.compile(r"[\u4e00-\u9fff]")
_RE_CJK_WORD = re.compile(r"[\u4e00-\u9fff]{2,4}")
_RE_LATIN_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_-]{1,}")


def normalize_whitespace(s: str) -> str:
    return _RE_WHITESPACE.sub(" ", s).strip()


def is_cjk_heavy(language: str, text: str) -> bool:
    lang = (language or "").lower()
    if "zh" in lang:
        return True
    # heuristic fallback
    cjk = len(_RE_CJK.findall(text))
    return cjk >= max(10, len(text) // 20)


def split_sentences(text: str, *, language: str) -> list[str]:
    t = normalize_whitespace(text)
    if not t:
        return []

    if is_cjk_heavy(language, t):
        parts = re.split(r"[。！？!?]+", t)
    else:
        parts = re.split(r"(?<=[.!?])\s+", t)
    return [p.strip() for p in parts if p.strip()]


def extract_cjk_keywords(text: str, *, max_keywords: int) -> list[str]:
    # Prefer 2-4 char CJK chunks.
    candidates = _RE_CJK_WORD.findall(text)
    if not candidates:
        return []
    freq: dict[str, int] = {}
    for w in candidates:
        freq[w] = freq.get(w, 0) + 1
    # Deterministic: (-freq, w)
    ranked = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
    return [w for w, _ in ranked[:max_keywords]]


_EN_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "in",
    "on",
    "for",
    "with",
    "as",
    "at",
    "by",
    "from",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "it",
    "this",
    "that",
    "these",
    "those",
    "we",
    "you",
    "they",
    "i",
    "he",
    "she",
    "them",
    "us",
    "our",
    "your",
    "their",
    "not",
    "can",
    "could",
    "should",
    "would",
    "may",
    "might",
    "will",
    "just",
    "also",
    "than",
    "then",
    "there",
    "here",
    "about",
    "into",
    "over",
    "under",
}


def extract_latin_keywords(text: str, *, max_keywords: int) -> list[str]:
    candidates = [w.lower() for w in _RE_LATIN_WORD.findall(text)]
    freq: dict[str, int] = {}
    for w in candidates:
        if w in _EN_STOPWORDS:
            continue
        if len(w) <= 2:
            continue
        freq[w] = freq.get(w, 0) + 1
    ranked = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
    return [w for w, _ in ranked[:max_keywords]]


def unique_preserve_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for it in items:
        if it in seen:
            continue
        seen.add(it)
        out.append(it)
    return out


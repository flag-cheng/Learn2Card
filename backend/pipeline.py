from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from hashlib import md5
from pathlib import Path
from typing import Any, Iterable


MAX_INPUT_CHARS = 200_000
EMBED_DIM = 64


class ProcessingError(ValueError):
    """User-facing error for invalid inputs or unprocessable text."""


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def split_paragraphs(text: str) -> list[str]:
    """
    Split by headings (#...), blank lines, and list items.

    - Headings start a new paragraph.
    - Blank line flushes current paragraph.
    - List item becomes its own paragraph.
    """
    text = _normalize_newlines(text)
    lines = text.split("\n")
    paras: list[str] = []
    buf: list[str] = []

    list_item_re = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")

    def flush() -> None:
        nonlocal buf
        s = "\n".join(buf).strip()
        if s:
            paras.append(s)
        buf = []

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            flush()
            continue

        if line.lstrip().startswith("#"):
            flush()
            buf.append(line.strip())
            continue

        if list_item_re.match(line):
            flush()
            paras.append(line.strip())
            continue

        buf.append(line)

    flush()
    return paras


def _compact_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def summarize(paragraph_text: str, limit: int = 60) -> str:
    """
    One-sentence summary, capped by character length.
    Deterministic heuristic: take first sentence-like chunk or first line.
    """
    s = _compact_spaces(paragraph_text.replace("\n", " "))
    if not s:
        return ""

    # Try split by sentence punctuation.
    for sep in ("。", "！", "？", ".", "!", "?"):
        if sep in s:
            head = s.split(sep, 1)[0].strip()
            if head:
                s = head
                break

    if len(s) <= limit:
        return s
    return s[:limit].rstrip()


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
    "is",
    "are",
    "be",
    "as",
    "by",
    "at",
    "from",
}


def extract_keywords(paragraph_text: str, max_keywords: int = 5) -> list[str]:
    """
    Extract 1–5 keywords deterministically via simple frequency.

    - Prefer CJK sequences (len>=2), then Latin words.
    - Tie-breaker: lexicographic to keep deterministic.
    """
    s = _compact_spaces(paragraph_text.replace("\n", " "))
    if not s:
        return ["重點"]

    cjk = re.findall(r"[\u4e00-\u9fff]{2,}", s)
    latin = re.findall(r"[A-Za-z][A-Za-z0-9_-]{1,}", s)
    tokens: list[str] = []
    tokens.extend(cjk)
    tokens.extend([w.lower() for w in latin if w.lower() not in _EN_STOPWORDS])

    freq: dict[str, int] = {}
    for t in tokens:
        freq[t] = freq.get(t, 0) + 1

    sorted_tokens = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))
    picked = [t for t, _ in sorted_tokens[:max_keywords]]

    if not picked:
        # Fallback: use fragments from summary.
        summ = summarize(s, limit=60)
        frag = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_-]{2,}", summ)
        picked = []
        for f in frag:
            if f not in picked:
                picked.append(f)
            if len(picked) >= max_keywords:
                break

    if not picked:
        picked = ["重點"]
    return picked[:max(1, min(max_keywords, 5))]


def _tokenize_for_embed(text: str) -> list[str]:
    s = _compact_spaces(text.replace("\n", " "))
    cjk = re.findall(r"[\u4e00-\u9fff]{2,}", s)
    latin = re.findall(r"[A-Za-z][A-Za-z0-9_-]{1,}", s)
    tokens = cjk + [w.lower() for w in latin]
    if tokens:
        return tokens
    # Fallback: take some 2-grams for CJK single-char texts.
    only_cjk = re.findall(r"[\u4e00-\u9fff]", s)
    if len(only_cjk) >= 2:
        return ["".join(only_cjk[i : i + 2]) for i in range(min(len(only_cjk) - 1, 20))]
    return [s[:8]] if s else []


def embed_text(text: str, dim: int = EMBED_DIM) -> list[float]:
    """
    Deterministic hashing embedding. No external dependencies.
    """
    vec = [0.0] * dim
    tokens = _tokenize_for_embed(text)
    if not tokens:
        vec[0] = 1.0
        return vec

    for tok in tokens:
        h = md5(tok.encode("utf-8")).digest()
        idx = int.from_bytes(h[:2], "big") % dim
        sign = 1.0 if (h[2] % 2 == 0) else -1.0
        mag = 1.0 + (h[3] / 255.0)
        vec[idx] += sign * mag

    return _l2_normalize(vec)


def _l2_normalize(v: list[float]) -> list[float]:
    n2 = sum(x * x for x in v)
    if n2 <= 0.0:
        return v
    n = math.sqrt(n2)
    return [x / n for x in v]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


@dataclass
class Paragraph:
    id: str
    text: str
    summary: str
    keywords: list[str]
    sourceIndex: int
    embedding: list[float]


@dataclass
class TopicCluster:
    memberIds: list[str]
    centroid: list[float]
    minSourceIndex: int


def cluster_paragraphs(
    paragraphs: list[Paragraph],
    *,
    topic_threshold: float = 0.75,
    max_topics: int = 5,
) -> list[TopicCluster]:
    if not paragraphs:
        return []

    clusters: list[TopicCluster] = []

    for p in paragraphs:
        if not clusters:
            clusters.append(
                TopicCluster(
                    memberIds=[p.id],
                    centroid=p.embedding[:],
                    minSourceIndex=p.sourceIndex,
                )
            )
            continue

        sims = [(i, cosine(p.embedding, c.centroid)) for i, c in enumerate(clusters)]
        best_i, best_sim = max(sims, key=lambda x: (x[1], -x[0]))

        if best_sim >= topic_threshold:
            _assign_to_cluster(clusters[best_i], p)
        else:
            if len(clusters) < max_topics:
                clusters.append(
                    TopicCluster(
                        memberIds=[p.id],
                        centroid=p.embedding[:],
                        minSourceIndex=p.sourceIndex,
                    )
                )
            else:
                _assign_to_cluster(clusters[best_i], p)

    # Deterministic sort by earliest source index.
    clusters.sort(key=lambda c: c.minSourceIndex)
    return clusters


def _assign_to_cluster(cluster: TopicCluster, p: Paragraph) -> None:
    n = len(cluster.memberIds)
    cluster.memberIds.append(p.id)
    # Update centroid incrementally then normalize.
    cluster.centroid = _l2_normalize(
        [(cluster.centroid[i] * n + p.embedding[i]) / (n + 1) for i in range(len(cluster.centroid))]
    )
    cluster.minSourceIndex = min(cluster.minSourceIndex, p.sourceIndex)


def _topic_title(paragraphs_by_id: dict[str, Paragraph], member_ids: list[str]) -> str:
    freq: dict[str, int] = {}
    for pid in member_ids:
        for kw in paragraphs_by_id[pid].keywords:
            freq[kw] = freq.get(kw, 0) + 1
    if freq:
        return sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    # Fallback to first member summary.
    first = paragraphs_by_id[member_ids[0]].summary
    return first[:20] if first else "未命名主題"


def _dedupe_preserve_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def build_deck(
    *,
    text: str,
    topic_threshold: float = 0.75,
    max_topics: int = 5,
    max_bullets: int = 5,
) -> dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        raise ProcessingError("輸入為空：請提供非空的純文字字串。")
    if len(raw) > MAX_INPUT_CHARS:
        raise ProcessingError(f"輸入過長：目前上限為 {MAX_INPUT_CHARS} 字元，實際為 {len(raw)}。")

    para_texts = split_paragraphs(raw)
    if not para_texts:
        raise ProcessingError("無法切分出任何段落：請確認輸入文字內容。")

    paragraphs: list[Paragraph] = []
    for i, ptxt in enumerate(para_texts):
        pid = f"p{i+1}"
        summ = summarize(ptxt, limit=60)
        kws = extract_keywords(ptxt, max_keywords=5)
        emb = embed_text(f"{summ} {' '.join(kws)}")
        paragraphs.append(
            Paragraph(
                id=pid,
                text=ptxt,
                summary=summ,
                keywords=kws,
                sourceIndex=i,
                embedding=emb,
            )
        )

    if topic_threshold < 0.0 or topic_threshold > 1.0:
        raise ProcessingError("topic_threshold 超出範圍：必須介於 0.0–1.0。")
    if max_topics < 1:
        raise ProcessingError("max_topics 超出範圍：最小為 1。")
    if max_bullets < 1 or max_bullets > 5:
        raise ProcessingError("max_bullets 超出範圍：必須介於 1–5。")

    clusters = cluster_paragraphs(
        paragraphs,
        topic_threshold=topic_threshold,
        max_topics=max_topics,
    )
    if not clusters:
        clusters = [TopicCluster(memberIds=[paragraphs[0].id], centroid=paragraphs[0].embedding[:], minSourceIndex=0)]

    paragraphs_by_id = {p.id: p for p in paragraphs}

    topics: list[dict[str, Any]] = []
    # Prepare topics with stable order and re-number after final sort.
    for c in clusters:
        member_ids = sorted(c.memberIds, key=lambda pid: paragraphs_by_id[pid].sourceIndex)
        topics.append(
            {
                "id": "",  # filled later
                "title": _topic_title(paragraphs_by_id, member_ids),
                "memberIds": member_ids,
                "_minSourceIndex": c.minSourceIndex,
            }
        )

    topics.sort(key=lambda t: t["_minSourceIndex"])
    for idx, t in enumerate(topics, start=1):
        new = f"t{idx}"
        t["id"] = new
        t.pop("_minSourceIndex", None)

    # Cards follow the sorted topic order.
    cards: list[dict[str, Any]] = []
    card_counter = 1
    for t in topics:
        member_ids: list[str] = t["memberIds"]
        chunks: list[list[str]]
        if len(member_ids) > 8:
            mid = len(member_ids) // 2
            if mid == 0:
                mid = 1
            chunks = [member_ids[:mid], member_ids[mid:]]
        else:
            chunks = [member_ids]

        for chunk_i, chunk in enumerate(chunks):
            bullets = _dedupe_preserve_order([paragraphs_by_id[pid].summary for pid in chunk if paragraphs_by_id[pid].summary])
            bullets = bullets[:max_bullets]
            if not bullets:
                bullets = [t["title"]]

            title = t["title"]
            if len(chunks) == 2:
                title = f"{title}（上）" if chunk_i == 0 else f"{title}（下）"

            cards.append(
                {
                    "id": f"c{card_counter}",
                    "topicId": t["id"],
                    "title": title,
                    "bullets": bullets,
                }
            )
            card_counter += 1

    deck = {
        "paragraphs": [
            {
                "id": p.id,
                "text": p.text,
                "summary": p.summary,
                "keywords": p.keywords[:5] if p.keywords else ["重點"],
                "sourceIndex": p.sourceIndex,
            }
            for p in paragraphs
        ],
        "topics": [{"id": t["id"], "title": t["title"], "memberIds": t["memberIds"]} for t in topics],
        "cards": cards,
        "stats": {
            "paragraphCount": len(paragraphs),
            "topicCount": len(topics),
            "cardCount": len(cards),
        },
    }
    return deck


def write_deck_json(deck: dict[str, Any], *, repo_root: Path) -> Path:
    """
    Write to frontend/public/deck.json (UTF-8, no BOM), creating directories as needed.
    """
    out_dir = repo_root / "frontend" / "public"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "deck.json"

    payload = json.dumps(deck, ensure_ascii=False, indent=2, sort_keys=True)
    out_path.write_text(payload + "\n", encoding="utf-8")
    return out_path


from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class Paragraph(BaseModel):
    id: str
    text: str
    summary: str
    keywords: list[str]
    sourceIndex: int


class Topic(BaseModel):
    id: str
    title: str
    memberIds: list[str]


class Card(BaseModel):
    id: str
    topicId: str
    title: str
    bullets: list[str]


class DeckStats(BaseModel):
    paragraphCount: int
    topicCount: int
    cardCount: int


class Deck(BaseModel):
    paragraphs: list[Paragraph]
    topics: list[Topic]
    cards: list[Card]
    stats: DeckStats


class AgentAOptions(BaseModel):
    language: Literal["zh", "en", "auto"] = "auto"
    topicThreshold: float = Field(default=0.75, ge=0.0, le=1.0)
    maxTopics: int = Field(default=5, ge=1)
    maxBulletsPerCard: int = Field(default=5, ge=1, le=5)
    minBulletsPerCardTarget: int = Field(default=3, ge=1, le=5)
    embeddingDim: int = Field(default=256, ge=32, le=4096)
    maxInputChars: int = Field(default=200_000, ge=1)


_RE_HEADING = re.compile(r"^(#{1,6})\s+(.*)\s*$")
_RE_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|(\d+)[.)])\s+(.+)\s*$")
_RE_WORD = re.compile(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+")
_RE_SENTENCE_SPLIT = re.compile(r"(?<=[。！？!?；;])\s+")


def _stable_hash_int(text: str) -> int:
    # Deterministic across runs (unlike Python's built-in hash()).
    return int.from_bytes(hashlib.md5(text.encode("utf-8")).digest()[:8], "big", signed=False)


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Keep newlines (used for paragraph splitting), but normalize excessive spaces.
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _split_paragraphs(raw_text: str) -> list[str]:
    """
    Markdown/純文字段落切分（規則固定、deterministic）：
    - Heading 會成為獨立段落（保留階層痕跡）
    - 空行切段
    - 清單項目各自成段
    - 不做「合併短段落」等聰明修正（符合 PRD 限制）
    """
    text = _normalize_text(raw_text)
    if not text:
        return []

    lines = text.split("\n")
    paragraphs: list[str] = []
    buf: list[str] = []
    in_code_fence = False

    def flush_buf() -> None:
        nonlocal buf
        if not buf:
            return
        block = "\n".join(buf).strip()
        buf = []
        if not block:
            return

        # If the block is a list block, split each item into a paragraph.
        # Otherwise, keep as-is.
        split_items: list[str] = []
        for line in block.split("\n"):
            m = _RE_LIST_ITEM.match(line)
            if m and not in_code_fence:
                split_items.append(m.group(2).strip())
            else:
                split_items = []
                break

        if split_items:
            paragraphs.extend(split_items)
        else:
            paragraphs.append(block)

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            # Keep fence markers with the code block.
            in_code_fence = not in_code_fence
            buf.append(line)
            continue

        if not in_code_fence:
            # Heading: flush previous paragraph; heading becomes its own paragraph.
            if _RE_HEADING.match(stripped):
                flush_buf()
                paragraphs.append(stripped)
                continue

            # Empty line splits paragraphs.
            if stripped == "":
                flush_buf()
                continue

        buf.append(line)

    flush_buf()
    return paragraphs


def _sentences(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    parts = _RE_SENTENCE_SPLIT.split(text)
    return [p.strip() for p in parts if p.strip()]


def _make_summary(text: str, *, max_len: int = 60) -> str:
    # Deterministic "one-sentence" summary: prefer first sentence; fallback to trimmed prefix.
    sents = _sentences(text)
    base = sents[0] if sents else text.strip()
    base = re.sub(r"\s+", " ", base).strip()
    if len(base) <= max_len:
        return base
    return base[: max_len - 1].rstrip() + "…"


def _tokenize_for_keywords(text: str) -> list[str]:
    tokens: list[str] = []
    for m in _RE_WORD.finditer(text):
        t = m.group(0).strip()
        if not t:
            continue
        if re.fullmatch(r"[A-Za-z0-9]+", t):
            tokens.append(t.lower())
        else:
            # CJK sequence: keep as-is (no lowercasing needed).
            tokens.append(t)
    return tokens


_ZH_STOPWORDS = {
    "的",
    "了",
    "與",
    "和",
    "或",
    "是",
    "在",
    "用",
    "把",
    "將",
    "為",
    "對",
    "及",
    "並",
    "需",
    "需要",
    "提供",
    "目前",
    "未來",
}
_EN_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "in",
    "for",
    "on",
    "with",
    "is",
    "are",
}


def _extract_keywords(text: str, *, k: int = 5) -> list[str]:
    # Deterministic keyword extractor based on token frequency.
    tokens = _tokenize_for_keywords(text)
    if not tokens:
        return []

    counts: dict[str, int] = {}
    for t in tokens:
        if t in _ZH_STOPWORDS or t in _EN_STOPWORDS:
            continue
        if len(t) <= 1:
            continue
        counts[t] = counts.get(t, 0) + 1

    if not counts:
        return []

    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [t for t, _ in ranked[:k]]


@dataclass(frozen=True)
class _Vec:
    data: list[float]

    def dot(self, other: "_Vec") -> float:
        return sum(a * b for a, b in zip(self.data, other.data))

    def norm(self) -> float:
        return (sum(a * a for a in self.data) ** 0.5) or 1.0

    def normalized(self) -> "_Vec":
        n = self.norm()
        return _Vec([a / n for a in self.data])


class HashingEmbedder:
    """
    可替換的 embedding 介面（預設為 deterministic、無外部依賴的 hashing 向量）。
    之後可換成 sentence-transformers / LLM embeddings，介面保持一致。
    """

    def __init__(self, dim: int = 256):
        self.dim = dim

    def embed(self, text: str) -> _Vec:
        v = [0.0] * self.dim
        tokens = _tokenize_for_keywords(text)
        for t in tokens:
            h = _stable_hash_int(t)
            idx = h % self.dim
            sign = -1.0 if (h >> 8) & 1 else 1.0
            v[idx] += sign
        return _Vec(v).normalized()


@dataclass
class _TopicState:
    id: str
    member_ids: list[str]
    centroid: _Vec
    min_source_index: int


def _cosine_similarity(a: _Vec, b: _Vec) -> float:
    return a.dot(b) / (a.norm() * b.norm())


def _average_vec(vecs: list[_Vec]) -> _Vec:
    if not vecs:
        return _Vec([0.0]).normalized()
    dim = len(vecs[0].data)
    acc = [0.0] * dim
    for v in vecs:
        for i, x in enumerate(v.data):
            acc[i] += x
    return _Vec([x / len(vecs) for x in acc]).normalized()


def _pick_topic_title(paragraphs: list[Paragraph]) -> str:
    # Prefer the most common keyword; fallback to first summary.
    keyword_counts: dict[str, int] = {}
    for p in paragraphs:
        for kw in p.keywords:
            keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
    if keyword_counts:
        kw = sorted(keyword_counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        return kw
    return paragraphs[0].summary if paragraphs else "未命名主題"


def _make_bullets(paragraphs: list[Paragraph], *, max_bullets: int, target_min: int) -> list[str]:
    bullets: list[str] = []
    seen: set[str] = set()
    for p in paragraphs:
        b = p.summary.strip()
        if not b or b in seen:
            continue
        bullets.append(b)
        seen.add(b)
        if len(bullets) >= max_bullets:
            break

    # Try to reach target_min (still must be within 1..5).
    if len(bullets) < min(target_min, max_bullets):
        # Add a keyword bullet if helpful.
        kws: list[str] = []
        for p in paragraphs:
            for kw in p.keywords:
                if kw not in kws:
                    kws.append(kw)
        if kws:
            extra = f"關鍵詞：{', '.join(kws[:5])}"
            if extra not in seen and len(bullets) < max_bullets:
                bullets.append(extra)
                seen.add(extra)

    if len(bullets) < min(target_min, max_bullets) and paragraphs:
        snippet_src = re.sub(r"\s+", " ", paragraphs[0].text).strip()
        if snippet_src:
            snippet = snippet_src if len(snippet_src) <= 50 else snippet_src[:49].rstrip() + "…"
            extra2 = f"原文片段：{snippet}"
            if extra2 not in seen and len(bullets) < max_bullets:
                bullets.append(extra2)

    return bullets[:max_bullets] if bullets else ["（此卡片目前沒有內容）"]


def generate_deck(
    text: str,
    options: AgentAOptions | None = None,
    *,
    debug: bool = False,
) -> Deck:
    """
    核心管線（不做任何檔案/URL I/O）：
    text(str) -> Deck(JSON schema 與 frontend/src/types.ts 完全一致)
    """
    options = options or AgentAOptions()
    text = _normalize_text(text)

    if not text:
        raise ValueError("輸入為空：請提供非空的純文字字串。")
    if len(text) > options.maxInputChars:
        raise ValueError(
            f"輸入過長：目前上限為 {options.maxInputChars} 字元，實際為 {len(text)}。"
        )

    raw_paragraphs = _split_paragraphs(text)
    if not raw_paragraphs:
        raise ValueError("無法切分出任何段落：請確認輸入文字內容。")

    paragraphs: list[Paragraph] = []
    for i, p_text in enumerate(raw_paragraphs):
        pid = f"p{i + 1}"
        summary = _make_summary(p_text)
        keywords = _extract_keywords(p_text, k=5)
        paragraphs.append(
            Paragraph(
                id=pid,
                text=p_text,
                summary=summary,
                keywords=keywords,
                sourceIndex=i,
            )
        )

    embedder = HashingEmbedder(dim=options.embeddingDim)
    embeddings: dict[str, _Vec] = {}
    for p in paragraphs:
        embeddings[p.id] = embedder.embed(f"{p.summary}\n{' '.join(p.keywords)}\n{p.text}")

    # Threshold clustering with maxTopics cap (deterministic, single-pass).
    topics_state: list[_TopicState] = []
    topic_members_vecs: dict[str, list[_Vec]] = {}

    for p in paragraphs:
        v = embeddings[p.id]
        if not topics_state:
            tid = "t1"
            topics_state.append(
                _TopicState(
                    id=tid,
                    member_ids=[p.id],
                    centroid=v,
                    min_source_index=p.sourceIndex,
                )
            )
            topic_members_vecs[tid] = [v]
            continue

        sims = [(_cosine_similarity(v, t.centroid), idx) for idx, t in enumerate(topics_state)]
        sims.sort(key=lambda x: (-x[0], x[1]))
        best_sim, best_idx = sims[0]
        best_topic = topics_state[best_idx]

        should_create = best_sim < options.topicThreshold and len(topics_state) < options.maxTopics
        if should_create:
            tid = f"t{len(topics_state) + 1}"
            topics_state.append(
                _TopicState(
                    id=tid,
                    member_ids=[p.id],
                    centroid=v,
                    min_source_index=p.sourceIndex,
                )
            )
            topic_members_vecs[tid] = [v]
        else:
            best_topic.member_ids.append(p.id)
            best_topic.min_source_index = min(best_topic.min_source_index, p.sourceIndex)
            topic_members_vecs[best_topic.id].append(v)
            best_topic.centroid = _average_vec(topic_members_vecs[best_topic.id])

    # Enforce deterministic ordering: by topic min sourceIndex, then by id.
    topics_state.sort(key=lambda t: (t.min_source_index, t.id))

    topics: list[Topic] = []
    cards: list[Card] = []
    card_seq = 1
    paragraphs_by_id = {p.id: p for p in paragraphs}

    for t_idx, t in enumerate(topics_state, start=1):
        tid = f"t{t_idx}"
        # Re-map topic IDs to be contiguous after sorting, but keep member ordering.
        member_ids = sorted(
            t.member_ids,
            key=lambda pid: (paragraphs_by_id[pid].sourceIndex, pid),
        )
        member_paras = [paragraphs_by_id[pid] for pid in member_ids]
        title = _pick_topic_title(member_paras)
        topics.append(Topic(id=tid, title=title, memberIds=member_ids))

        # Cards: 1 per topic; split into 2 if too many members.
        splits: list[list[Paragraph]]
        if len(member_paras) > 8:
            mid = (len(member_paras) + 1) // 2
            splits = [member_paras[:mid], member_paras[mid:]]
        else:
            splits = [member_paras]

        for s_idx, chunk in enumerate(splits):
            suffix = ""
            if len(splits) == 2:
                suffix = "（上）" if s_idx == 0 else "（下）"
            bullets = _make_bullets(
                chunk,
                max_bullets=options.maxBulletsPerCard,
                target_min=options.minBulletsPerCardTarget,
            )
            cards.append(
                Card(
                    id=f"c{card_seq}",
                    topicId=tid,
                    title=f"{title}{suffix}" if title else f"未命名卡片{suffix}",
                    bullets=bullets,
                )
            )
            card_seq += 1

    deck = Deck(
        paragraphs=paragraphs,
        topics=topics,
        cards=cards,
        stats=DeckStats(
            paragraphCount=len(paragraphs),
            topicCount=len(topics),
            cardCount=len(cards),
        ),
    )

    if debug:
        print(
            json.dumps(
                {
                    "paragraphCount": len(paragraphs),
                    "topicCount": len(topics),
                    "cardCount": len(cards),
                    "topicThreshold": options.topicThreshold,
                    "maxTopics": options.maxTopics,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )

    return deck


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="agent-a",
        description="Agent A: 文本→段落→摘要/關鍵詞→語意分群→卡片草稿→Deck JSON（固定輸出到 frontend/public/deck.json）",
    )
    p.add_argument(
        "--text",
        required=True,
        help="輸入純文字字串（請自行在呼叫方完成檔案讀取/抓取）。",
    )
    p.add_argument("--topic-threshold", type=float, default=0.75)
    p.add_argument("--max-topics", type=int, default=5)
    p.add_argument("--max-bullets", type=int, default=5)
    p.add_argument("--debug", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    options = AgentAOptions(
        topicThreshold=args.topic_threshold,
        maxTopics=args.max_topics,
        maxBulletsPerCard=max(1, min(5, args.max_bullets)),
    )
    deck = generate_deck(args.text, options=options, debug=args.debug)
    deck_json = json.dumps(deck.model_dump(), ensure_ascii=False, sort_keys=True, indent=2)
    
    # 判斷是否輸出到 stdout
    if args.output in ("-", "stdout"):
        # 輸出到 stdout（方便管道操作）
        print(deck_json)
    else:
        # 寫入檔案（自動建立目錄）
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(deck_json, encoding="utf-8")
        print(f"✓ 已成功輸出到：{output_path.absolute()}", file=sys.stderr)
        print(f"  - 段落數：{deck.stats.paragraphCount}", file=sys.stderr)
        print(f"  - 主題數：{deck.stats.topicCount}", file=sys.stderr)
        print(f"  - 卡片數：{deck.stats.cardCount}", file=sys.stderr)
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


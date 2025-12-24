from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from dataclasses import dataclass
from hashlib import blake2b
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple


# -----------------------------
# 規格常數（依 technical-spec.md）
# -----------------------------

DEFAULT_TOPIC_THRESHOLD = 0.75
DEFAULT_MAX_TOPICS = 5
DEFAULT_MAX_BULLETS = 5

# 依 5k tokens 級別做保守字元上限；可依需求調整
MAX_TEXT_CHARS = 20_000


# -----------------------------
# Schema（需符合 frontend/src/types.ts）
# -----------------------------


@dataclass(frozen=True)
class Paragraph:
    id: str  # p1, p2, ...
    text: str
    summary: str
    keywords: List[str]
    sourceIndex: int


@dataclass(frozen=True)
class Topic:
    id: str  # t1, t2, ...
    title: str
    memberIds: List[str]


@dataclass(frozen=True)
class Card:
    id: str  # c1, c2, ...
    topicId: str
    title: str
    bullets: List[str]


# -----------------------------
# 小工具
# -----------------------------


_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def _has_cjk(text: str) -> bool:
    return _CJK_RE.search(text) is not None


def _normalize_text(text: str) -> str:
    # 保留內容但避免雜訊：統一換行、去除行尾空白
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return text.strip()


def decode_cli_text(text: str) -> str:
    """
    Agent B 會把特殊字元跳脫後塞進 --text 的雙引號字串，例如：
    - \\n, \\r
    - \\\\（反斜線）
    - \\\"（雙引號）

    這裡做最小必要的反跳脫，讓後續段落切分能正常工作。
    """
    if not text:
        return text
    # 先處理換行，再處理引號與反斜線（順序重要）
    out = text
    out = out.replace("\\r", "\r").replace("\\n", "\n")
    out = out.replace('\\"', '"')
    out = out.replace("\\\\", "\\")
    return out


def _project_root() -> Path:
    # backend/main.py -> backend/ -> <root>
    return Path(__file__).resolve().parent.parent


def _debug_print(enabled: bool, msg: str) -> None:
    if enabled:
        print(msg, file=sys.stderr)


def _clip(s: str, max_len: int) -> str:
    s = s.strip()
    if len(s) <= max_len:
        return s
    # 用單一字元省略號避免超過上限太多
    return s[: max(0, max_len - 1)].rstrip() + "…"


def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


# -----------------------------
# 1) 段落切分
# -----------------------------


_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+\S")
_LIST_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+\.\s+)\S")


def split_paragraphs(raw_text: str) -> List[str]:
    """
    依標題（#）、空行、清單項目切分。
    - 標題會作為一個段落區塊的開頭，與其後的內容併在同一段落（直到下一個切分點）
    - 清單項目每一行視為獨立段落（避免多點混在一起）
    """
    text = _normalize_text(raw_text)
    if not text:
        return []

    lines = text.split("\n")
    blocks: List[str] = []
    buf: List[str] = []

    def flush() -> None:
        nonlocal buf
        joined = "\n".join(buf).strip()
        if joined:
            blocks.append(joined)
        buf = []

    for line in lines:
        if not line.strip():
            flush()
            continue

        if _LIST_RE.match(line):
            flush()
            blocks.append(line.strip())
            continue

        if _HEADING_RE.match(line):
            flush()
            buf.append(line.strip())
            continue

        buf.append(line.strip())

    flush()
    return blocks


# -----------------------------
# 2) 摘要與關鍵詞（deterministic heuristic）
# -----------------------------


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？.!?])\s+")
_ZH_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,}")
_EN_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}")

_STOPWORDS_ZH = {
    "我們",
    "你們",
    "他們",
    "以及",
    "但是",
    "因此",
    "因為",
    "如果",
    "目前",
    "可以",
    "需要",
    "不需要",
    "不得",
    "必須",
    "功能",
    "需求",
    "規範",
    "系統",
    "資料",
    "內容",
}
_STOPWORDS_EN = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "your",
    "you",
    "are",
    "was",
    "were",
    "will",
    "can",
    "should",
    "could",
    "would",
    "not",
}


def summarize(paragraph_text: str) -> str:
    one_line = re.sub(r"\s+", " ", paragraph_text.strip())
    if not one_line:
        return ""
    # 優先用第一句；否則用前綴
    parts = _SENTENCE_SPLIT_RE.split(one_line)
    first = parts[0].strip() if parts else one_line
    return _clip(first, 60)


def extract_keywords(paragraph_text: str, max_keywords: int = 5) -> List[str]:
    text = paragraph_text.strip()
    if not text:
        return ["重點"]

    # 拿掉 Markdown heading 的 #，避免成為 token 垃圾
    cleaned = re.sub(r"^\s{0,3}#{1,6}\s+", "", text)
    cleaned = re.sub(r"[`*_>\[\]\(\)]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if _has_cjk(cleaned):
        tokens = _ZH_TOKEN_RE.findall(cleaned)
        tokens = [t for t in tokens if t not in _STOPWORDS_ZH]
    else:
        tokens = [t.lower() for t in _EN_TOKEN_RE.findall(cleaned)]
        tokens = [t for t in tokens if t not in _STOPWORDS_EN]

    if not tokens:
        # 最後 fallback：用摘要的前 2~6 字元/字母
        s = summarize(cleaned)
        return [_clip(s, 12) or "重點"]

    counts = Counter(tokens)
    # 次序 deterministic：先頻率、再字串排序
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    out: List[str] = []
    for token, _ in ranked:
        if token and token not in out:
            out.append(_clip(token, 20))
        if len(out) >= max(1, min(max_keywords, 5)):
            break
    return out or ["重點"]


# -----------------------------
# 3) 向量化（deterministic hashing embedding）與相似度
# -----------------------------


def _tokens_for_embedding(text: str) -> List[str]:
    text = text.strip()
    if not text:
        return []
    # 混合策略：中文以字串序列，英文以單字
    if _has_cjk(text):
        toks = _ZH_TOKEN_RE.findall(text)
        return toks[:128]
    toks = [t.lower() for t in _EN_TOKEN_RE.findall(text)]
    return toks[:128]


def embed_text(text: str, dim: int = 128) -> List[float]:
    """
    使用 feature hashing 產生固定維度向量，避免引入外部依賴。
    """
    vec = [0.0] * dim
    tokens = _tokens_for_embedding(text)
    if not tokens:
        return vec

    for tok in tokens:
        h = blake2b(tok.encode("utf-8"), digest_size=8).digest()
        # 前 4 bytes 當 index，後 4 bytes 當 sign/weight
        idx = int.from_bytes(h[:4], "little") % dim
        sign = -1.0 if (h[4] & 1) else 1.0
        vec[idx] += sign

    # L2 normalize
    norm = math.sqrt(sum(x * x for x in vec))
    if norm:
        vec = [x / norm for x in vec]
    return vec


def cosine_sim(a: Sequence[float], b: Sequence[float]) -> float:
    # a, b 已 normalize 時 dot 即 cosine；仍可容錯
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return _safe_div(dot, na * nb)


def mean_vector(vectors: Sequence[Sequence[float]]) -> List[float]:
    if not vectors:
        return []
    dim = len(vectors[0])
    out = [0.0] * dim
    for v in vectors:
        for i in range(dim):
            out[i] += v[i]
    out = [x / len(vectors) for x in out]
    norm = math.sqrt(sum(x * x for x in out))
    if norm:
        out = [x / norm for x in out]
    return out


# -----------------------------
# 4) 閾值分群（尊重 maxTopics）
# -----------------------------


@dataclass
class _Cluster:
    member_indices: List[int]  # indices into paragraphs list
    centroid: List[float]


def cluster_by_threshold(
    embeddings: Sequence[Sequence[float]],
    threshold: float,
    max_topics: int,
) -> List[_Cluster]:
    if not embeddings:
        return []
    clusters: List[_Cluster] = []

    for i, emb in enumerate(embeddings):
        if not clusters:
            clusters.append(_Cluster(member_indices=[i], centroid=list(emb)))
            continue

        best_j = 0
        best_sim = -1.0
        for j, c in enumerate(clusters):
            sim = cosine_sim(emb, c.centroid)
            # tie-break：選較早建立的 cluster（j 小者）
            if sim > best_sim + 1e-12:
                best_sim = sim
                best_j = j

        if best_sim >= threshold or len(clusters) >= max_topics:
            clusters[best_j].member_indices.append(i)
            # 更新 centroid（deterministic）
            members = [embeddings[k] for k in clusters[best_j].member_indices]
            clusters[best_j].centroid = mean_vector(members)
        else:
            clusters.append(_Cluster(member_indices=[i], centroid=list(emb)))

    return clusters


# -----------------------------
# 5) Topic 命名與 6) 卡片生成
# -----------------------------


def choose_topic_title(member_paragraphs: Sequence[Paragraph]) -> str:
    # 先看關鍵詞統計，若不夠再 fallback 摘要
    kw = Counter()
    for p in member_paragraphs:
        kw.update([k for k in p.keywords if k])
    if kw:
        token, _ = sorted(kw.items(), key=lambda kv: (-kv[1], kv[0]))[0]
        return _clip(token, 30) or "未命名主題"
    return _clip(member_paragraphs[0].summary, 30) if member_paragraphs else "未命名主題"


def build_card_bullets(member_paragraphs: Sequence[Paragraph], max_bullets: int) -> List[str]:
    # bullets 依 sourceIndex 順序，去重
    bullets: List[str] = []
    for p in sorted(member_paragraphs, key=lambda x: x.sourceIndex):
        s = p.summary.strip()
        if s and s not in bullets:
            bullets.append(s)
        if len(bullets) >= max_bullets:
            break
    if not bullets:
        bullets = ["（此主題暫無可用摘要）"]
    # 最終保證 1–5
    return bullets[: max(1, min(max_bullets, 5))]


def generate_cards_for_topic(
    topic_id: str,
    topic_title: str,
    member_paragraphs: Sequence[Paragraph],
    max_bullets: int,
) -> List[Tuple[str, List[str]]]:
    """
    回傳 [(cardTitle, bullets), ...]；依規格 memberIds > 8 拆成 2 張。
    """
    members_sorted = sorted(member_paragraphs, key=lambda p: p.sourceIndex)
    if len(members_sorted) > 8:
        mid = (len(members_sorted) + 1) // 2
        first = members_sorted[:mid]
        second = members_sorted[mid:]
        return [
            (f"{topic_title}（上）", build_card_bullets(first, max_bullets)),
            (f"{topic_title}（下）", build_card_bullets(second, max_bullets)),
        ]
    return [(topic_title, build_card_bullets(members_sorted, max_bullets))]


# -----------------------------
# 管線整合
# -----------------------------


def build_deck(
    text: str,
    topic_threshold: float,
    max_topics: int,
    max_bullets: int,
    debug: bool,
) -> dict:
    decoded = decode_cli_text(text)
    normalized = _normalize_text(decoded)
    if not normalized:
        raise ValueError("輸入為空：請提供非空的純文字字串。")
    if len(normalized) > MAX_TEXT_CHARS:
        raise ValueError(f"輸入過長：目前上限為 {MAX_TEXT_CHARS} 字元，實際為 {len(normalized)}。")

    blocks = split_paragraphs(normalized)
    if not blocks:
        raise ValueError("無法切分出任何段落：請確認輸入文字內容。")

    _debug_print(debug, f"[debug] paragraphs(raw)={len(blocks)}")

    paragraphs: List[Paragraph] = []
    embeddings: List[List[float]] = []
    for idx, block in enumerate(blocks):
        pid = f"p{idx + 1}"
        summ = summarize(block)
        kws = extract_keywords(block, max_keywords=5)
        paragraphs.append(
            Paragraph(
                id=pid,
                text=block,
                summary=summ,
                keywords=kws,
                sourceIndex=idx,
            )
        )
        embeddings.append(embed_text(f"{summ} {' '.join(kws)}\n{block}"))

    clusters = cluster_by_threshold(embeddings, threshold=topic_threshold, max_topics=max_topics)
    if not clusters:
        # 理論上不會發生，但保底
        clusters = [_Cluster(member_indices=list(range(len(paragraphs))), centroid=mean_vector(embeddings))]

    # 先建立 topics（未排序前按建立順序），之後依最小 sourceIndex 排序
    topics_unsorted: List[Topic] = []
    cluster_member_ids: List[List[str]] = []
    for i, c in enumerate(clusters):
        member = [paragraphs[k] for k in c.member_indices]
        title = choose_topic_title(member)
        member_ids = [p.id for p in sorted(member, key=lambda p: p.sourceIndex)]
        topics_unsorted.append(Topic(id=f"t{i + 1}", title=title, memberIds=member_ids))
        cluster_member_ids.append(member_ids)

    # Deterministic 排序：Topics 依其 memberIds 中最小 sourceIndex
    p_index = {p.id: p.sourceIndex for p in paragraphs}
    topics_sorted = sorted(
        topics_unsorted,
        key=lambda t: min(p_index[pid] for pid in t.memberIds) if t.memberIds else 10**9,
    )

    # 依 topic 順序產生 cards
    cards: List[Card] = []
    next_card_num = 1
    for topic in topics_sorted:
        member_paras = [p for p in paragraphs if p.id in set(topic.memberIds)]
        card_defs = generate_cards_for_topic(topic.id, topic.title, member_paras, max_bullets=max_bullets)
        for card_title, bullets in card_defs:
            cards.append(
                Card(
                    id=f"c{next_card_num}",
                    topicId=topic.id,
                    title=_clip(card_title, 60) or "未命名卡片",
                    bullets=bullets,
                )
            )
            next_card_num += 1

    deck = {
        "paragraphs": [
            {
                "id": p.id,
                "text": p.text,
                "summary": p.summary,
                "keywords": p.keywords[:5],
                "sourceIndex": p.sourceIndex,
            }
            for p in sorted(paragraphs, key=lambda x: x.sourceIndex)
        ],
        "topics": [
            {"id": t.id, "title": t.title or "未命名主題", "memberIds": list(t.memberIds)}
            for t in topics_sorted
        ],
        "cards": [{"id": c.id, "topicId": c.topicId, "title": c.title, "bullets": c.bullets[:5]} for c in cards],
        "stats": {
            "paragraphCount": len(paragraphs),
            "topicCount": len(topics_sorted),
            "cardCount": len(cards),
        },
    }

    # debug：顯示 topic 分配摘要
    if debug:
        for t in topics_sorted:
            _debug_print(
                True,
                f"[debug] {t.id} title={t.title!r} members={len(t.memberIds)} firstIndex="
                f"{min(p_index[pid] for pid in t.memberIds) if t.memberIds else 'n/a'}",
            )
        _debug_print(True, f"[debug] cards={len(cards)}")

    return deck


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="learn2cards",
        description="Agent A：核心 NLP/LLM 管線（Backend CLI）",
    )
    parser.add_argument("--text", type=str, required=True, help="輸入的純文字字串（可含 Markdown）")
    parser.add_argument(
        "--topic-threshold",
        type=float,
        default=DEFAULT_TOPIC_THRESHOLD,
        help=f"分群閾值（0.0–1.0，預設 {DEFAULT_TOPIC_THRESHOLD}）",
    )
    parser.add_argument(
        "--max-topics",
        type=int,
        default=DEFAULT_MAX_TOPICS,
        help=f"最大主題數（>=1，預設 {DEFAULT_MAX_TOPICS}）",
    )
    parser.add_argument(
        "--max-bullets",
        type=int,
        default=DEFAULT_MAX_BULLETS,
        help=f"每卡 bullets 上限（1–5，預設 {DEFAULT_MAX_BULLETS}）",
    )
    parser.add_argument("--debug", action="store_true", help="輸出除錯訊息（stderr）")
    return parser.parse_args(list(argv))


def validate_args(args: argparse.Namespace) -> None:
    if not (0.0 <= args.topic_threshold <= 1.0):
        raise ValueError("參數錯誤：--topic-threshold 必須在 0.0–1.0 之間。")
    if args.max_topics < 1:
        raise ValueError("參數錯誤：--max-topics 必須 >= 1。")
    if not (1 <= args.max_bullets <= 5):
        raise ValueError("參數錯誤：--max-bullets 必須在 1–5 之間。")


def write_deck_json(deck: dict, debug: bool) -> Path:
    root = _project_root()
    out_dir = root / "frontend" / "public"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "deck.json"

    # UTF-8（無 BOM），縮排 2，確保中文顯示，sort_keys=True
    payload = json.dumps(deck, ensure_ascii=False, indent=2, sort_keys=True)
    out_path.write_text(payload + "\n", encoding="utf-8", newline="\n")

    # 成功訊息依 spec 輸出到 stderr
    stats = deck.get("stats") or {}
    print(f"✓ 已成功輸出到：{out_path.resolve()}", file=sys.stderr)
    print(f"  - 段落數：{stats.get('paragraphCount', 0)}", file=sys.stderr)
    print(f"  - 主題數：{stats.get('topicCount', 0)}", file=sys.stderr)
    print(f"  - 卡片數：{stats.get('cardCount', 0)}", file=sys.stderr)

    _debug_print(debug, f"[debug] wrote_bytes={out_path.stat().st_size}")
    return out_path


def main(argv: Sequence[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    try:
        args = parse_args(argv)
        validate_args(args)
        deck = build_deck(
            text=args.text,
            topic_threshold=float(args.topic_threshold),
            max_topics=int(args.max_topics),
            max_bullets=int(args.max_bullets),
            debug=bool(args.debug),
        )
        write_deck_json(deck, debug=bool(args.debug))
        return 0
    except Exception as e:
        print(f"錯誤：{e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

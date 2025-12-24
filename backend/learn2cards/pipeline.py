from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import blake2b

from .models import Card, Deck, DeckOptions, Keypoint, Meta, Paragraph, Stats, Topic


_RE_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_RE_LIST = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")


def generate_deck(text: str, *, source: str = "text", options: DeckOptions | None = None) -> Deck:
    """Core pipeline (pure text in, Deck out). No file I/O here."""
    if options is None:
        options = DeckOptions()

    cleaned = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not cleaned:
        raise ValueError("input text is empty")
    if len(cleaned) > 500_000:
        raise ValueError("input text too large (>500k chars) for demo pipeline")

    paragraphs = _split_paragraphs(cleaned)
    keypoints = [_extract_keypoint(p, options) for p in paragraphs]

    vectors = [_embed_for_clustering(p, keypoints[i], options) for i, p in enumerate(paragraphs)]
    clusters = _threshold_cluster(vectors, paragraphs, options)

    topics = _build_topics(clusters, paragraphs, keypoints)
    cards = _build_cards(topics, paragraphs, keypoints, options)

    deck = Deck(
        meta=Meta(
            source=source,
            generatedAt=datetime.now(timezone.utc).isoformat(),
            schemaVersion="1.0.0",
        ),
        paragraphs=paragraphs,
        keypoints=keypoints,
        topics=topics,
        cards=cards,
        stats=Stats(
            totalParagraphs=len(paragraphs),
            totalKeypoints=len(keypoints),
            totalTopics=len(topics),
            totalCards=len(cards),
        ),
    )
    return deck


def _split_paragraphs(text: str) -> list[Paragraph]:
    """Split markdown/plain text into paragraphs, preserving heading hierarchy."""
    lines = text.split("\n")
    section_stack: list[str] = []

    paragraphs: list[Paragraph] = []
    buf: list[str] = []
    cur_heading_level: int | None = None
    cur_section_path: list[str] | None = None

    def flush():
        nonlocal buf, cur_heading_level, cur_section_path
        if not buf:
            return
        raw = "\n".join(buf).strip()
        buf = []
        if not raw:
            return
        pid = f"p{len(paragraphs) + 1}"
        paragraphs.append(
            Paragraph(
                id=pid,
                idx=len(paragraphs),
                text=raw,
                headingLevel=cur_heading_level,
                sectionPath=cur_section_path[:] if cur_section_path else None,
            )
        )
        cur_heading_level = None
        cur_section_path = None

    for line in lines:
        m = _RE_HEADING.match(line.strip())
        if m:
            flush()
            level = len(m.group(1))
            title = m.group(2).strip()
            # maintain stack as section path
            section_stack = section_stack[: level - 1]
            section_stack.append(title)
            cur_heading_level = level
            cur_section_path = section_stack[:]
            # a heading itself becomes a paragraph (so idx is stable and groupable)
            buf = [title]
            flush()
            continue

        if not line.strip():
            flush()
            continue

        # list lines: keep as a single paragraph block (bullet list)
        lm = _RE_LIST.match(line)
        if lm:
            buf.append(f"- {lm.group(1).strip()}")
        else:
            buf.append(line.strip())

    flush()
    return paragraphs


_STOP_EN = {
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
    "was",
    "were",
    "be",
    "as",
    "by",
    "at",
    "from",
    "that",
    "this",
    "it",
    "we",
    "you",
    "they",
    "i",
    "he",
    "she",
    "them",
    "our",
    "your",
}


def _extract_keypoint(p: Paragraph, options: DeckOptions) -> Keypoint:
    text = p.text.strip()
    sentence = _first_sentence(text)
    keywords = _extract_keywords(text, max_n=5)
    # ensure 1..5
    if not keywords:
        keywords = ["重點"]
    return Keypoint(paragraphId=p.id, sentence=sentence, keywords=keywords[:5])


def _first_sentence(text: str) -> str:
    t = " ".join([ln.strip() for ln in text.splitlines() if ln.strip()])
    # prefer first list item if it's a list
    if t.startswith("- "):
        first = t.split("- ", 1)[1]
        first = first.split(" - ", 1)[0]
        return (first.strip()[:240] or "（重點略）").strip()

    # split by common sentence terminators
    parts = re.split(r"(?<=[。！？!?\.])\s+", t)
    for part in parts:
        s = part.strip()
        if s:
            return (s[:240] if len(s) > 240 else s)
    return (t[:240] or "（重點略）").strip()


def _is_cjk(s: str) -> bool:
    for ch in s:
        if "\u4e00" <= ch <= "\u9fff":
            return True
    return False


def _extract_keywords(text: str, *, max_n: int = 5) -> list[str]:
    t = unicodedata.normalize("NFKC", text)
    if _is_cjk(t):
        # For CJK: extract frequent 2-4 length Han sequences
        seqs = re.findall(r"[\u4e00-\u9fff]{2,4}", t)
        c = Counter(seqs)
        # filter ultra-common/meaningless tokens (very small demo set)
        for bad in ["我們", "可以", "需要", "以及", "如果", "因此", "但是", "這個", "目前", "可能"]:
            c.pop(bad, None)
        return [w for w, _ in c.most_common(max_n)]

    # English-ish
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{1,}", t.lower())
    words = [w for w in words if w not in _STOP_EN and len(w) >= 3]
    c = Counter(words)
    return [w for w, _ in c.most_common(max_n)]


def _tokenize_for_hash(text: str) -> list[str]:
    t = unicodedata.normalize("NFKC", text)
    if _is_cjk(t):
        # take 2-gram of Han characters to get some signal
        hans = re.findall(r"[\u4e00-\u9fff]", t)
        return ["".join(hans[i : i + 2]) for i in range(len(hans) - 1)]
    return re.findall(r"[A-Za-z][A-Za-z0-9_-]{1,}", t.lower())


def _hash_to_index(token: str, dim: int) -> int:
    h = blake2b(token.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(h, "little") % dim


def _embed_for_clustering(p: Paragraph, kp: Keypoint, options: DeckOptions) -> list[float]:
    dim = options.embeddingDim
    vec = [0.0] * dim
    tokens = _tokenize_for_hash(p.text) + kp.keywords
    for tok in tokens:
        if not tok or tok.isspace():
            continue
        idx = _hash_to_index(tok, dim)
        vec[idx] += 1.0
    return _l2_normalize(vec)


def _l2_normalize(v: list[float]) -> list[float]:
    s = math.sqrt(sum(x * x for x in v))
    if s <= 0:
        return v
    return [x / s for x in v]


def _cosine(a: list[float], b: list[float]) -> float:
    # vectors are normalized; dot is cosine
    return float(sum(x * y for x, y in zip(a, b, strict=False)))


@dataclass
class _Cluster:
    member_indices: list[int]
    centroid: list[float]


def _threshold_cluster(vectors: list[list[float]], paragraphs: list[Paragraph], options: DeckOptions) -> list[_Cluster]:
    if not vectors:
        return []

    clusters: list[_Cluster] = [_Cluster(member_indices=[0], centroid=vectors[0][:])]

    def update_centroid(c: _Cluster, new_vec: list[float]) -> None:
        n = len(c.member_indices)
        # centroid = average then normalize
        c.centroid = _l2_normalize([(c.centroid[i] * (n - 1) + new_vec[i]) / n for i in range(len(new_vec))])

    for i in range(1, len(vectors)):
        v = vectors[i]
        best_j = 0
        best_sim = -1.0
        for j, c in enumerate(clusters):
            sim = _cosine(v, c.centroid)
            if sim > best_sim:
                best_sim = sim
                best_j = j

        if best_sim >= options.topicThreshold:
            clusters[best_j].member_indices.append(i)
            update_centroid(clusters[best_j], v)
            continue

        if len(clusters) < options.maxTopics:
            clusters.append(_Cluster(member_indices=[i], centroid=v[:]))
            continue

        # maxTopics reached: force-assign to closest cluster (even if below threshold)
        clusters[best_j].member_indices.append(i)
        update_centroid(clusters[best_j], v)

    # At least 1 topic required
    return clusters or [_Cluster(member_indices=[0], centroid=vectors[0][:])]


def _build_topics(clusters: list[_Cluster], paragraphs: list[Paragraph], keypoints: list[Keypoint]) -> list[Topic]:
    # Sort deterministic: by smallest paragraph idx in memberIndices
    cluster_order = sorted(
        enumerate(clusters),
        key=lambda it: min(it[1].member_indices),
    )

    # Build keyword pool per paragraphId for naming
    kp_by_pid = {k.paragraphId: k for k in keypoints}

    topics: list[Topic] = []
    for tidx, (_orig_idx, c) in enumerate(cluster_order, start=1):
        member_ids = [paragraphs[i].id for i in sorted(c.member_indices)]
        kw_counter: Counter[str] = Counter()
        for pid in member_ids:
            kw_counter.update(kp_by_pid[pid].keywords)
        top_kw = [w for w, _ in kw_counter.most_common(3)]
        title = "、".join(top_kw) if top_kw else f"主題 {tidx}"

        # summaryBullets: use first up to 3 keypoint sentences
        summary = [kp_by_pid[pid].sentence for pid in member_ids[:3]]
        topics.append(
            Topic(
                id=f"t{tidx}",
                title=title,
                memberIds=member_ids,
                summaryBullets=summary if summary else None,
            )
        )
    return topics


def _build_cards(
    topics: list[Topic],
    paragraphs: list[Paragraph],
    keypoints: list[Keypoint],
    options: DeckOptions,
) -> list[Card]:
    kp_by_pid = {k.paragraphId: k for k in keypoints}
    para_by_id = {p.id: p for p in paragraphs}

    cards: list[Card] = []

    def bullets_for(member_ids: list[str]) -> list[str]:
        bullets: list[str] = []
        for pid in member_ids:
            s = kp_by_pid[pid].sentence.strip()
            if s and s not in bullets:
                bullets.append(s)
            if len(bullets) >= options.maxBulletsPerCard:
                break

        # If too few bullets, add short fragments from paragraph text deterministically
        if len(bullets) < options.targetMinBullets:
            for pid in member_ids:
                frag = _first_sentence(para_by_id[pid].text)
                if frag and frag not in bullets:
                    bullets.append(frag)
                if len(bullets) >= options.targetMinBullets:
                    break

        return bullets[: options.maxBulletsPerCard] or ["（此卡片目前沒有內容）"]

    for t in topics:
        members = t.memberIds
        if len(members) > 8:
            mid = len(members) // 2
            parts = [members[:mid], members[mid:]]
        else:
            parts = [members]

        for part_idx, part_members in enumerate(parts, start=1):
            suffix = f"（{part_idx}/{len(parts)}）" if len(parts) > 1 else ""
            cards.append(
                Card(
                    id=f"c{len(cards) + 1}",
                    topicId=t.id,
                    title=f"{t.title}{suffix}",
                    bullets=bullets_for(part_members),
                )
            )

    return cards


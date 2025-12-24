from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import math
import re
from collections import Counter
from typing import Any, Iterable, Literal


Language = Literal["zh", "en", "auto"]


@dataclasses.dataclass(frozen=True)
class AnalyzeOptions:
    language: Language = "auto"
    max_topics: int = 5
    topic_threshold: float = 0.75
    max_bullets_per_card: int = 5
    target_bullets_per_card: int = 4
    embedding_dim: int = 256
    seed: int | None = 0
    source: str = "text"
    verbose: bool = False
    # Soft limits (avoid pathological inputs)
    max_chars: int = 200_000


class PipelineError(ValueError):
    pass


_RE_MD_HEADING = re.compile(r"^(#{1,6})\s+(.*)\s*$")
_RE_LIST_ITEM = re.compile(r"^(\s*)(?:[-*+]|(\d+)[.)])\s+(.*)\s*$")


def analyze_text(text: str, options: AnalyzeOptions | None = None) -> dict[str, Any]:
    """Run Agent A pipeline.

    IMPORTANT: This function accepts *text strings only* and performs no I/O.
    """

    opt = options or AnalyzeOptions()
    _validate_options(opt)

    if text is None:
        raise PipelineError("輸入為 None。請提供 UTF-8 文字字串。")
    if not isinstance(text, str):
        raise PipelineError(f"輸入必須是 str，收到：{type(text)!r}")

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.strip("\n")
    if not normalized.strip():
        raise PipelineError("輸入文字為空。")
    if len(normalized) > opt.max_chars:
        raise PipelineError(
            f"輸入過長（{len(normalized)} chars），上限為 {opt.max_chars}。"
        )

    paragraphs = _split_paragraphs(normalized)
    if not paragraphs:
        raise PipelineError("切段後沒有任何段落。")

    # Add stable IDs and sequential idx
    paragraph_objs: list[dict[str, Any]] = []
    for i, p in enumerate(paragraphs):
        pid = f"p{i+1}"
        obj: dict[str, Any] = {
            "id": pid,
            "idx": i,
            "text": p["text"],
        }
        if p.get("headingLevel") is not None:
            obj["headingLevel"] = p["headingLevel"]
        if p.get("sectionPath") is not None:
            obj["sectionPath"] = p["sectionPath"]
        paragraph_objs.append(obj)

    lang = _resolve_language(opt.language, normalized)
    keypoints = _extract_keypoints(paragraph_objs, language=lang)

    vectors = _embed_paragraphs(paragraph_objs, keypoints, dim=opt.embedding_dim, lang=lang)
    topics = _cluster_threshold(
        paragraph_objs,
        keypoints,
        vectors,
        threshold=opt.topic_threshold,
        max_topics=opt.max_topics,
        lang=lang,
    )

    cards = _generate_cards(
        topics,
        paragraph_objs,
        keypoints,
        lang=lang,
        max_bullets=opt.max_bullets_per_card,
        target_bullets=opt.target_bullets_per_card,
    )

    # Deterministic order & stable IDs after sort.
    topics = _sort_topics_deterministic(topics, paragraph_objs)
    topics, topic_id_map = _reassign_topic_ids(topics)
    cards = _remap_cards_topic_ids(cards, topic_id_map)
    cards = _sort_cards_deterministic(cards, topics)
    cards = _reassign_card_ids(cards)

    stats = {
        "totalParagraphs": len(paragraph_objs),
        "totalKeypoints": len(keypoints),
        "totalTopics": len(topics),
        "totalCards": len(cards),
    }

    deck = {
        "meta": {
            "source": opt.source,
            "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
            "schemaVersion": "1.0.0",
        },
        "paragraphs": paragraph_objs,
        "keypoints": keypoints,
        "topics": topics,
        "cards": cards,
        "stats": stats,
    }

    if opt.verbose:
        deck["_debug"] = {
            "resolvedLanguage": lang,
            "options": dataclasses.asdict(opt),
        }

    return deck


def _validate_options(opt: AnalyzeOptions) -> None:
    if opt.max_topics < 1:
        raise PipelineError("max_topics 必須 >= 1")
    if not (0.0 <= opt.topic_threshold <= 1.0):
        raise PipelineError("topic_threshold 必須介於 0.0~1.0")
    if opt.embedding_dim < 16:
        raise PipelineError("embedding_dim 過小（建議 >= 16）")
    if not (1 <= opt.max_bullets_per_card <= 5):
        raise PipelineError("max_bullets_per_card 必須介於 1~5")
    if not (1 <= opt.target_bullets_per_card <= 5):
        raise PipelineError("target_bullets_per_card 必須介於 1~5")
    if opt.target_bullets_per_card > opt.max_bullets_per_card:
        raise PipelineError("target_bullets_per_card 不得大於 max_bullets_per_card")


def _resolve_language(language: Language, text: str) -> Literal["zh", "en"]:
    if language in ("zh", "en"):
        return language
    # auto: simple heuristic (presence of CJK)
    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh"
    return "en"


def _split_paragraphs(text: str) -> list[dict[str, Any]]:
    """Split Markdown/plain text into paragraphs.

    Rules (fixed & dumb by design):
    - Markdown headings (#..######) update sectionPath; headings are not paragraphs.
    - Blank line ends a paragraph.
    - Each list item becomes its own paragraph.
    """

    lines = text.split("\n")
    section_stack: list[str] = []
    heading_titles: list[str] = []
    current_heading_level: int | None = None

    def set_heading(level: int, title: str) -> None:
        nonlocal section_stack, heading_titles, current_heading_level
        # keep stack length == level
        if level <= 0:
            section_stack = []
            heading_titles = []
            current_heading_level = None
            return
        if len(heading_titles) >= level:
            heading_titles = heading_titles[: level - 1]
        while len(heading_titles) < level - 1:
            heading_titles.append("")
        heading_titles.append(title.strip())
        section_stack = [t for t in heading_titles if t]
        current_heading_level = level

    paras: list[dict[str, Any]] = []
    buf: list[str] = []

    def flush_buf() -> None:
        nonlocal buf
        joined = "\n".join(buf).strip()
        if joined:
            p: dict[str, Any] = {"text": joined}
            # attach current section context (if any)
            if section_stack:
                p["sectionPath"] = list(section_stack)
            if current_heading_level is not None:
                p["headingLevel"] = current_heading_level
            paras.append(p)
        buf = []

    for line in lines:
        m_h = _RE_MD_HEADING.match(line)
        if m_h:
            flush_buf()
            level = len(m_h.group(1))
            title = m_h.group(2).strip()
            set_heading(level, title)
            continue

        if not line.strip():
            flush_buf()
            continue

        m_li = _RE_LIST_ITEM.match(line)
        if m_li:
            flush_buf()
            item_text = m_li.group(3).strip()
            if item_text:
                p: dict[str, Any] = {"text": item_text}
                if section_stack:
                    p["sectionPath"] = list(section_stack)
                if current_heading_level is not None:
                    p["headingLevel"] = current_heading_level
                paras.append(p)
            continue

        buf.append(line.rstrip())

    flush_buf()
    return paras


_STOPWORDS_EN = {
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
    "by",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "it",
    "this",
    "that",
    "these",
    "those",
    "at",
    "from",
    "we",
    "you",
    "they",
    "i",
    "our",
    "your",
    "their",
}

_STOPWORDS_ZH = {
    "的",
    "了",
    "與",
    "和",
    "及",
    "或",
    "在",
    "對",
    "把",
    "是",
    "為",
    "並",
    "而",
    "也",
    "都",
    "及其",
    "以及",
    "如果",
    "因為",
    "所以",
    "我們",
    "你們",
    "他們",
    "她們",
    "它們",
}


def _first_sentence(text: str, lang: Literal["zh", "en"]) -> str:
    t = re.sub(r"\s+", " ", text).strip()
    if not t:
        return ""
    if lang == "zh":
        parts = re.split(r"[。！？!?]", t, maxsplit=1)
        s = parts[0].strip()
        return s if s else t[:120]
    parts = re.split(r"[.?!]\s", t, maxsplit=1)
    s = parts[0].strip()
    return s if s else t[:120]


def _tokenize(text: str, lang: Literal["zh", "en"]) -> list[str]:
    t = text.lower()
    if lang == "zh":
        # Extract CJK sequences and alphanum words
        tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[a-z0-9]{2,}", t)
        return tokens
    return re.findall(r"[a-z0-9]{2,}", t)


def _extract_keywords(text: str, lang: Literal["zh", "en"], k: int = 5) -> list[str]:
    tokens = _tokenize(text, lang)
    if lang == "zh":
        tokens = [x for x in tokens if x not in _STOPWORDS_ZH]
    else:
        tokens = [x for x in tokens if x not in _STOPWORDS_EN]
    if not tokens:
        return []
    cnt = Counter(tokens)
    # deterministic: sort by (-freq, token)
    ranked = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))
    kws = [w for (w, _) in ranked[:k]]
    return kws


def _extract_keypoints(
    paragraphs: list[dict[str, Any]], *, language: Literal["zh", "en"]
) -> list[dict[str, Any]]:
    keypoints: list[dict[str, Any]] = []
    for p in paragraphs:
        pid = p["id"]
        text = p["text"]
        sent = _first_sentence(text, language)
        kws = _extract_keywords(text, language, k=5)
        if not sent:
            sent = text[:160].strip()
        if not kws:
            kws = _extract_keywords(sent, language, k=5)
        kws = kws[:5]
        if len(kws) == 0:
            # ensure at least 1 keyword if possible
            toks = _tokenize(text, language)
            kws = toks[:1] if toks else []
        keypoints.append(
            {
                "paragraphId": pid,
                "sentence": sent,
                "keywords": kws[:5] if kws else [],
            }
        )
    return keypoints


def _hash_token(token: str) -> int:
    # stable across processes/platforms
    h = hashlib.md5(token.encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def _embed_paragraphs(
    paragraphs: list[dict[str, Any]],
    keypoints: list[dict[str, Any]],
    *,
    dim: int,
    lang: Literal["zh", "en"],
) -> list[list[float]]:
    # Use hashed bag-of-words from paragraph text + keywords.
    kp_by_pid = {k["paragraphId"]: k for k in keypoints}
    vectors: list[list[float]] = []
    for p in paragraphs:
        pid = p["id"]
        toks = _tokenize(p["text"], lang)
        kws = kp_by_pid.get(pid, {}).get("keywords", [])
        toks.extend([f"kw:{kw}" for kw in kws])
        if not toks:
            vectors.append([0.0] * dim)
            continue
        vec = [0.0] * dim
        for tok in toks:
            idx = _hash_token(tok) % dim
            vec[idx] += 1.0
        _l2_normalize_inplace(vec)
        vectors.append(vec)
    return vectors


def _l2_normalize_inplace(vec: list[float]) -> None:
    s2 = sum(x * x for x in vec)
    if s2 <= 0.0:
        return
    inv = 1.0 / math.sqrt(s2)
    for i, x in enumerate(vec):
        vec[i] = x * inv


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for (x, y) in zip(a, b))


def _mean_vector(vs: list[list[float]]) -> list[float]:
    if not vs:
        return []
    dim = len(vs[0])
    out = [0.0] * dim
    for v in vs:
        for i, x in enumerate(v):
            out[i] += x
    inv = 1.0 / float(len(vs))
    for i in range(dim):
        out[i] *= inv
    _l2_normalize_inplace(out)
    return out


def _cluster_threshold(
    paragraphs: list[dict[str, Any]],
    keypoints: list[dict[str, Any]],
    vectors: list[list[float]],
    *,
    threshold: float,
    max_topics: int,
    lang: Literal["zh", "en"],
) -> list[dict[str, Any]]:
    if not paragraphs:
        return []
    kp_by_pid = {k["paragraphId"]: k for k in keypoints}

    topics: list[dict[str, Any]] = []
    centroids: list[list[float]] = []

    for p, v in zip(paragraphs, vectors):
        pid = p["id"]
        if not topics:
            topics.append(
                {
                    "id": "t1",
                    "title": "",
                    "memberIds": [pid],
                    "summaryBullets": [],
                }
            )
            centroids.append(v[:])
            continue

        sims = [_dot(v, c) for c in centroids]
        best_i = max(range(len(sims)), key=lambda i: sims[i])
        best_sim = sims[best_i]

        if best_sim >= threshold:
            topics[best_i]["memberIds"].append(pid)
            centroids[best_i] = _mean_vector([vectors[_pid_to_index(paragraphs, mid)] for mid in topics[best_i]["memberIds"]])
            continue

        if len(topics) < max_topics:
            topics.append(
                {
                    "id": f"t{len(topics)+1}",
                    "title": "",
                    "memberIds": [pid],
                    "summaryBullets": [],
                }
            )
            centroids.append(v[:])
            continue

        # max topics reached: force-assign to best topic
        topics[best_i]["memberIds"].append(pid)
        centroids[best_i] = _mean_vector([vectors[_pid_to_index(paragraphs, mid)] for mid in topics[best_i]["memberIds"]])

    # Name topics using aggregated keywords; make summary bullets from member keypoint sentences.
    for t in topics:
        member_kws: list[str] = []
        member_sents: list[str] = []
        for mid in t["memberIds"]:
            kp = kp_by_pid.get(mid)
            if not kp:
                continue
            member_kws.extend(kp.get("keywords", []))
            member_sents.append(kp.get("sentence", ""))

        title = _title_from_keywords(member_kws, lang=lang)
        t["title"] = title
        bullets = [s for s in _dedupe(member_sents) if s]
        t["summaryBullets"] = bullets[:3] if bullets else []

    return topics


def _pid_to_index(paragraphs: list[dict[str, Any]], pid: str) -> int:
    # paragraph ids are p1..pn and idx aligned; keep safe anyway
    if pid.startswith("p"):
        try:
            n = int(pid[1:])
            i = n - 1
            if 0 <= i < len(paragraphs) and paragraphs[i]["id"] == pid:
                return i
        except Exception:
            pass
    for i, p in enumerate(paragraphs):
        if p["id"] == pid:
            return i
    raise PipelineError(f"找不到 paragraph id：{pid}")


def _title_from_keywords(keywords: list[str], *, lang: Literal["zh", "en"]) -> str:
    kws = [k for k in keywords if k]
    if not kws:
        return "未命名主題" if lang == "zh" else "Untitled Topic"
    cnt = Counter(kws)
    ranked = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))
    picked = [w for (w, _) in ranked[:4]]
    # Keep it short
    picked = picked[:3] if len(picked) > 3 else picked
    if lang == "zh":
        return "、".join(picked)
    return " / ".join(picked)


def _dedupe(items: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for x in items:
        key = x.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _generate_cards(
    topics: list[dict[str, Any]],
    paragraphs: list[dict[str, Any]],
    keypoints: list[dict[str, Any]],
    *,
    lang: Literal["zh", "en"],
    max_bullets: int,
    target_bullets: int,
) -> list[dict[str, Any]]:
    kp_by_pid = {k["paragraphId"]: k for k in keypoints}
    cards: list[dict[str, Any]] = []

    for topic in topics:
        mids = list(topic["memberIds"])
        # Split rule: if > 8 members, split into 2 cards
        chunks: list[list[str]]
        if len(mids) > 8:
            cut = (len(mids) + 1) // 2
            chunks = [mids[:cut], mids[cut:]]
        else:
            chunks = [mids]

        for chunk_i, chunk in enumerate(chunks):
            title = topic.get("title") or "未命名主題"
            if len(chunks) == 2:
                title = f"{title}（{chunk_i+1}/2）"

            # bullets from member keypoint sentences (fallback to paragraph text)
            bullets: list[str] = []
            for pid in chunk:
                kp = kp_by_pid.get(pid)
                if kp and kp.get("sentence"):
                    bullets.append(str(kp["sentence"]).strip())
                else:
                    p = paragraphs[_pid_to_index(paragraphs, pid)]
                    bullets.append(_first_sentence(p.get("text", ""), lang))

            bullets = _dedupe(bullets)
            bullets = [b for b in bullets if b]
            if len(bullets) > max_bullets:
                bullets = bullets[:max_bullets]
            if len(bullets) == 0:
                bullets = ["（此卡片目前沒有內容）"]
            # try to hit target 3-5, but must be 1-5
            if len(bullets) > target_bullets:
                bullets = bullets[:target_bullets]

            cards.append(
                {
                    "id": f"c{len(cards)+1}",
                    "topicId": topic["id"],
                    "title": title,
                    "bullets": bullets[:max_bullets],
                }
            )

    return cards


def _sort_topics_deterministic(
    topics: list[dict[str, Any]], paragraphs: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    idx_by_pid = {p["id"]: p["idx"] for p in paragraphs}

    def topic_key(t: dict[str, Any]) -> tuple[int, str]:
        mids = t.get("memberIds", [])
        min_idx = min((idx_by_pid.get(mid, 10**9) for mid in mids), default=10**9)
        # tiebreaker: title for stability
        return (min_idx, str(t.get("title", "")))

    return sorted(topics, key=topic_key)


def _reassign_topic_ids(
    topics: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    id_map: dict[str, str] = {}
    out: list[dict[str, Any]] = []
    for i, t in enumerate(topics):
        old = str(t["id"])
        new = f"t{i+1}"
        id_map[old] = new
        t2 = dict(t)
        t2["id"] = new
        out.append(t2)
    return out, id_map


def _remap_cards_topic_ids(
    cards: list[dict[str, Any]], topic_id_map: dict[str, str]
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for c in cards:
        c2 = dict(c)
        tid = str(c2.get("topicId", ""))
        c2["topicId"] = topic_id_map.get(tid, tid)
        out.append(c2)
    return out


def _sort_cards_deterministic(cards: list[dict[str, Any]], topics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    topic_order = {t["id"]: i for i, t in enumerate(topics)}

    def card_key(c: dict[str, Any]) -> tuple[int, str]:
        return (topic_order.get(c["topicId"], 10**9), str(c.get("title", "")))

    return sorted(cards, key=card_key)


def _reassign_card_ids(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, c in enumerate(cards):
        c2 = dict(c)
        c2["id"] = f"c{i+1}"
        out.append(c2)
    return out


def to_pretty_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=False) + "\n"


from __future__ import annotations

import dataclasses
import datetime as _dt
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Literal


SchemaVersion = Literal["1.0.0"]


class AgentAError(RuntimeError):
    """User-facing error for CLI."""


def _iso_now() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).isoformat()


def read_text_file(path: str | Path, *, max_bytes: int = 5_000_000) -> str:
    p = Path(path)
    if not p.exists():
        raise AgentAError(f"找不到輸入檔案：{p}")
    if not p.is_file():
        raise AgentAError(f"輸入路徑不是檔案：{p}")

    size = p.stat().st_size
    if size == 0:
        raise AgentAError("輸入檔案是空的，無法產生 deck。")
    if size > max_bytes:
        raise AgentAError(f"輸入檔案過大（{size} bytes），上限為 {max_bytes} bytes。")

    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise AgentAError("檔案不是 UTF-8 編碼，請轉成 UTF-8 後再試。") from e


def _strip_md_inline(text: str) -> str:
    # Very small markdown cleanup: links, inline code, emphasis markers.
    t = text
    t = re.sub(r"`([^`]+)`", r"\1", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    t = t.replace("**", "").replace("__", "").replace("*", "").replace("_", "")
    return t


def _is_heading(line: str) -> tuple[int, str] | None:
    m = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
    if not m:
        return None
    level = len(m.group(1))
    title = m.group(2).strip()
    return level, title


def _is_list_item(line: str) -> tuple[str, int] | None:
    # Returns (content, indent_spaces)
    m = re.match(r"^(\s*)([-*+])\s+(.+?)\s*$", line)
    if m:
        return m.group(3).strip(), len(m.group(1))
    m2 = re.match(r"^(\s*)(\d+)[.)]\s+(.+?)\s*$", line)
    if m2:
        return m2.group(3).strip(), len(m2.group(1))
    return None


def split_paragraphs(text: str) -> list[dict[str, Any]]:
    """
    Markdown/純文字切段（保留 heading hierarchy）：
    - Heading 本身是一個 paragraph（含 headingLevel, sectionPath）
    - 一般段落依空行分隔
    - 清單項目每項獨立成段（含續行縮排）
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    paragraphs: list[dict[str, Any]] = []
    section_path: list[str] = []

    in_code = False
    buf: list[str] = []
    buf_section_path: list[str] | None = None

    def flush_buf() -> None:
        nonlocal buf, buf_section_path
        content = "\n".join(buf).strip()
        if content:
            p = {
                "id": "",  # filled later
                "idx": len(paragraphs),
                "text": content,
            }
            if buf_section_path:
                p["sectionPath"] = list(buf_section_path)
            paragraphs.append(p)
        buf = []
        buf_section_path = None

    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip("\n")

        if re.match(r"^\s*```", line):
            # treat code fence as paragraph boundary; keep fence line in buffer
            if not in_code:
                flush_buf()
                in_code = True
                buf_section_path = list(section_path)
                buf.append(line)
            else:
                buf.append(line)
                flush_buf()
                in_code = False
            i += 1
            continue

        if in_code:
            if buf_section_path is None:
                buf_section_path = list(section_path)
            buf.append(line)
            i += 1
            continue

        h = _is_heading(line)
        if h:
            flush_buf()
            level, title = h
            # update section path
            section_path = section_path[: level - 1]
            section_path.append(title)
            paragraphs.append(
                {
                    "id": "",
                    "idx": len(paragraphs),
                    "text": title,
                    "headingLevel": level,
                    "sectionPath": list(section_path),
                }
            )
            i += 1
            continue

        if not line.strip():
            flush_buf()
            i += 1
            continue

        li = _is_list_item(line)
        if li:
            flush_buf()
            item_text, item_indent = li
            item_lines = [item_text]
            # absorb continuation lines (indented)
            j = i + 1
            while j < len(lines):
                nxt = lines[j].rstrip("\n")
                if not nxt.strip():
                    break
                if _is_heading(nxt) or _is_list_item(nxt):
                    break
                cont_indent = len(re.match(r"^(\s*)", nxt).group(1))
                if cont_indent > item_indent:
                    item_lines.append(nxt.strip())
                    j += 1
                    continue
                break
            p = {
                "id": "",
                "idx": len(paragraphs),
                "text": "\n".join(item_lines).strip(),
            }
            if section_path:
                p["sectionPath"] = list(section_path)
            paragraphs.append(p)
            i = j
            continue

        # normal line into buffer
        if buf_section_path is None:
            buf_section_path = list(section_path)
        buf.append(line)
        i += 1

    flush_buf()

    # fill ids deterministically
    for idx, p in enumerate(paragraphs):
        p["id"] = f"p{idx + 1}"
        p["idx"] = idx
    return paragraphs


def _split_sentences(text: str) -> list[str]:
    t = _strip_md_inline(text)
    t = re.sub(r"\s+", " ", t).strip()
    if not t:
        return []
    parts = re.split(r"(?<=[。！？.!?])\s+", t)
    parts = [p.strip() for p in parts if p.strip()]
    return parts or [t]


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
    "as",
    "is",
    "are",
    "was",
    "were",
    "be",
    "by",
    "it",
    "this",
    "that",
    "these",
    "those",
}


def _guess_language(text: str) -> Literal["zh", "en"]:
    # Extremely small heuristic: if there are CJK characters, treat as zh.
    return "zh" if re.search(r"[\u4e00-\u9fff]", text) else "en"


def extract_keypoint_sentence(paragraph_text: str, *, max_len: int = 160) -> str:
    sents = _split_sentences(paragraph_text)
    if not sents:
        return ""
    s = sents[0]
    if len(s) > max_len:
        return s[: max_len - 1].rstrip() + "…"
    return s


def extract_keywords(
    paragraph_text: str,
    *,
    language: Literal["zh", "en", "auto"] = "auto",
    max_keywords: int = 5,
) -> list[str]:
    if max_keywords < 1:
        return []
    cleaned = _strip_md_inline(paragraph_text)
    lang = _guess_language(cleaned) if language == "auto" else language

    counts: Counter[str] = Counter()

    if lang == "en":
        tokens = re.findall(r"[A-Za-z][A-Za-z0-9']+", cleaned.lower())
        for t in tokens:
            if len(t) <= 2 or t in _STOP_EN:
                continue
            counts[t] += 1
    else:
        # CJK bigrams as lightweight keywords.
        chars = re.findall(r"[\u4e00-\u9fff]", cleaned)
        for i in range(len(chars) - 1):
            bg = chars[i] + chars[i + 1]
            counts[bg] += 1
        # Keep a few longer runs too (2-6 chars).
        for run in re.findall(r"[\u4e00-\u9fff]{2,6}", cleaned):
            counts[run] += 1

    top = [k for k, _ in counts.most_common(max_keywords)]
    # Ensure 1–5 if possible by adding fallback tokens.
    if not top:
        fallback = cleaned.strip()
        if fallback:
            top = [fallback[: min(6, len(fallback))]]
    return top[:max_keywords]


def _hash_token(token: str) -> int:
    return int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)


def embed_text(
    text: str,
    *,
    dim: int = 256,
    language: Literal["zh", "en", "auto"] = "auto",
) -> list[float]:
    cleaned = _strip_md_inline(text)
    lang = _guess_language(cleaned) if language == "auto" else language
    if lang == "en":
        toks = re.findall(r"[A-Za-z][A-Za-z0-9']+", cleaned.lower())
        toks = [t for t in toks if len(t) > 2 and t not in _STOP_EN]
    else:
        # Use CJK bigrams.
        chars = re.findall(r"[\u4e00-\u9fff]", cleaned)
        toks = [chars[i] + chars[i + 1] for i in range(len(chars) - 1)]
        if not toks:
            toks = re.findall(r"[\u4e00-\u9fff]{2,6}", cleaned)

    if not toks:
        return [0.0] * dim

    vec = [0.0] * dim
    for t, c in Counter(toks).items():
        h = _hash_token(t)
        idx = h % dim
        sign = 1.0 if ((h >> 1) & 1) == 1 else -1.0
        vec[idx] += sign * float(c)

    # L2 normalize
    norm = math.sqrt(sum(x * x for x in vec))
    if norm <= 1e-12:
        return vec
    return [x / norm for x in vec]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError("vector dims mismatch")
    return float(sum(x * y for x, y in zip(a, b)))


@dataclasses.dataclass
class _Cluster:
    member_paragraph_ids: list[str]
    centroid: list[float]


def _mean_vector(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return []
    dim = len(vectors[0])
    s = [0.0] * dim
    for v in vectors:
        for i, x in enumerate(v):
            s[i] += x
    norm = math.sqrt(sum(x * x for x in s))
    if norm <= 1e-12:
        return s
    return [x / norm for x in s]


def cluster_by_threshold(
    paragraph_ids: list[str],
    vectors: list[list[float]],
    *,
    topic_threshold: float = 0.75,
    max_topics: int = 5,
) -> list[list[str]]:
    if max_topics < 1:
        max_topics = 1
    if not paragraph_ids:
        return [[]]

    clusters: list[_Cluster] = []
    member_vectors: dict[str, list[float]] = {}
    for pid, v in zip(paragraph_ids, vectors):
        member_vectors[pid] = v

    for pid in paragraph_ids:
        v = member_vectors[pid]
        if not clusters:
            clusters.append(_Cluster(member_paragraph_ids=[pid], centroid=v))
            continue

        sims = [cosine_similarity(v, c.centroid) for c in clusters]
        best_i = max(range(len(sims)), key=lambda i: sims[i])
        best_sim = sims[best_i]

        if best_sim >= topic_threshold:
            clusters[best_i].member_paragraph_ids.append(pid)
        else:
            if len(clusters) < max_topics:
                clusters.append(_Cluster(member_paragraph_ids=[pid], centroid=v))
            else:
                clusters[best_i].member_paragraph_ids.append(pid)

        # update centroid for touched cluster(s) deterministically
        for ci in {best_i, len(clusters) - 1}:
            if 0 <= ci < len(clusters):
                vids = [member_vectors[x] for x in clusters[ci].member_paragraph_ids]
                clusters[ci].centroid = _mean_vector(vids) or clusters[ci].centroid

    return [c.member_paragraph_ids for c in clusters] or [[]]


def _topic_title_from_keywords(
    paragraph_id_to_keywords: dict[str, list[str]],
    member_ids: list[str],
    *,
    language: Literal["zh", "en", "auto"] = "auto",
) -> str:
    counts: Counter[str] = Counter()
    for pid in member_ids:
        for k in paragraph_id_to_keywords.get(pid, []):
            counts[k] += 1
    top = [k for k, _ in counts.most_common(4)]
    if not top:
        return "未命名主題"
    lang = _guess_language("".join(top)) if language == "auto" else language
    if lang == "en":
        return " / ".join(top[:3])
    return "・".join(top[:3])


def _bullets_from_keypoints(
    paragraph_id_to_sentence: dict[str, str],
    member_ids: list[str],
    *,
    max_bullets: int = 5,
) -> list[str]:
    max_bullets = max(1, min(5, max_bullets))
    bullets: list[str] = []
    seen = set()
    for pid in member_ids:
        s = (paragraph_id_to_sentence.get(pid) or "").strip()
        if not s:
            continue
        if s in seen:
            continue
        seen.add(s)
        bullets.append(s)
        if len(bullets) >= max_bullets:
            break
    if not bullets:
        bullets = ["（此卡片目前沒有內容）"]
    return bullets[:max_bullets]


def generate_deck(
    input_text: str,
    *,
    source: str,
    schema_version: SchemaVersion = "1.0.0",
    language: Literal["zh", "en", "auto"] = "auto",
    topic_threshold: float = 0.75,
    max_topics: int = 5,
    bullets_per_card: int = 5,
    embedding_dim: int = 256,
    verbose: bool = False,
) -> dict[str, Any]:
    paragraphs = split_paragraphs(input_text)
    if not paragraphs:
        raise AgentAError("切段後沒有任何段落可用，請確認輸入內容。")

    paragraph_ids = [p["id"] for p in paragraphs]

    # keypoints
    keypoints: list[dict[str, Any]] = []
    pid_to_sentence: dict[str, str] = {}
    pid_to_keywords: dict[str, list[str]] = {}

    for p in paragraphs:
        pid = p["id"]
        sentence = extract_keypoint_sentence(p["text"])
        keywords = extract_keywords(p["text"], language=language, max_keywords=5)
        pid_to_sentence[pid] = sentence
        pid_to_keywords[pid] = keywords
        keypoints.append({"paragraphId": pid, "sentence": sentence, "keywords": keywords[:5]})

    # embeddings
    vectors = [embed_text(p["text"], dim=embedding_dim, language=language) for p in paragraphs]
    if all(all(abs(x) < 1e-12 for x in v) for v in vectors):
        raise AgentAError("向量化失敗（所有向量皆為 0），請確認輸入內容是否可解析。")

    clusters = cluster_by_threshold(
        paragraph_ids,
        vectors,
        topic_threshold=topic_threshold,
        max_topics=max_topics,
    )
    if not clusters:
        clusters = [paragraph_ids]

    pid_to_idx = {p["id"]: p["idx"] for p in paragraphs}
    cluster_infos = []
    for member_ids in clusters:
        member_ids = [pid for pid in member_ids if pid in pid_to_idx]
        if not member_ids:
            continue
        min_idx = min(pid_to_idx[pid] for pid in member_ids)
        cluster_infos.append((min_idx, member_ids))

    if not cluster_infos:
        cluster_infos = [(0, paragraph_ids)]

    # deterministic topic sort
    cluster_infos.sort(key=lambda x: (x[0], len(x[1]), x[1][0]))

    topics: list[dict[str, Any]] = []
    cards: list[dict[str, Any]] = []

    for t_i, (_, member_ids) in enumerate(cluster_infos, start=1):
        topic_id = f"t{t_i}"
        title = _topic_title_from_keywords(pid_to_keywords, member_ids, language=language)
        summary_bullets = _bullets_from_keypoints(pid_to_sentence, member_ids, max_bullets=5)

        topics.append(
            {
                "id": topic_id,
                "title": title,
                "memberIds": member_ids,
                "summaryBullets": summary_bullets[:5],
            }
        )

        # cards: 1 per topic, or 2 if > 8 members
        if len(member_ids) > 8:
            mid = (len(member_ids) + 1) // 2
            parts = [member_ids[:mid], member_ids[mid:]]
        else:
            parts = [member_ids]

        for part_i, part in enumerate(parts, start=1):
            card_id = f"c{len(cards) + 1}"
            card_title = title if len(parts) == 1 else f"{title}（{part_i}/2）"
            bullets = _bullets_from_keypoints(pid_to_sentence, part, max_bullets=bullets_per_card)
            cards.append(
                {
                    "id": card_id,
                    "topicId": topic_id,
                    "title": card_title,
                    "bullets": bullets,
                }
            )

    deck = {
        "meta": {"source": source, "generatedAt": _iso_now(), "schemaVersion": schema_version},
        "paragraphs": paragraphs,
        "keypoints": keypoints,
        "topics": topics,
        "cards": cards,
        "stats": {
            "totalParagraphs": len(paragraphs),
            "totalKeypoints": len(keypoints),
            "totalTopics": len(topics),
            "totalCards": len(cards),
        },
    }

    if verbose:
        # keep logging minimal but useful
        print(
            json.dumps(
                {
                    "debug": {
                        "paragraphs": len(paragraphs),
                        "topics": [{"id": t["id"], "members": len(t["memberIds"])} for t in topics],
                        "cards": len(cards),
                    }
                },
                ensure_ascii=False,
                indent=2,
            )
        )

    return deck


def write_deck_json(deck: dict[str, Any], output_path: str | Path, *, force: bool = False) -> None:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and not force:
        raise AgentAError(f"輸出檔已存在：{out}（可加上 --force 覆寫）")
    out.write_text(json.dumps(deck, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_deck(deck: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    def err(msg: str) -> None:
        errors.append(msg)

    if not isinstance(deck, dict):
        return ["deck JSON 必須是物件 (object)"]

    for k in ("meta", "paragraphs", "keypoints", "topics", "cards", "stats"):
        if k not in deck:
            err(f"缺少頂層欄位：{k}")

    if errors:
        return errors

    meta = deck["meta"]
    if not isinstance(meta, dict):
        err("meta 必須是物件")
    else:
        if meta.get("schemaVersion") != "1.0.0":
            err("meta.schemaVersion 必須是 '1.0.0'")
        if not isinstance(meta.get("source"), str) or not meta.get("source"):
            err("meta.source 必須是非空字串")
        if not isinstance(meta.get("generatedAt"), str) or not meta.get("generatedAt"):
            err("meta.generatedAt 必須是 ISO8601 字串")

    paragraphs = deck["paragraphs"]
    keypoints = deck["keypoints"]
    topics = deck["topics"]
    cards = deck["cards"]
    stats = deck["stats"]

    if not isinstance(paragraphs, list):
        err("paragraphs 必須是陣列")
        return errors
    if not isinstance(keypoints, list):
        err("keypoints 必須是陣列")
        return errors
    if not isinstance(topics, list):
        err("topics 必須是陣列")
        return errors
    if not isinstance(cards, list):
        err("cards 必須是陣列")
        return errors
    if not isinstance(stats, dict):
        err("stats 必須是物件")
        return errors

    # paragraphs
    pid_to_idx: dict[str, int] = {}
    for i, p in enumerate(paragraphs):
        if not isinstance(p, dict):
            err(f"paragraphs[{i}] 必須是物件")
            continue
        pid = p.get("id")
        if not isinstance(pid, str) or not pid:
            err(f"paragraphs[{i}].id 必須是非空字串")
            continue
        if pid in pid_to_idx:
            err(f"paragraph id 重複：{pid}")
            continue
        idx = p.get("idx")
        if not isinstance(idx, int) or idx != i:
            err(f"paragraphs[{i}].idx 必須等於其序列位置（預期 {i}）")
        if not isinstance(p.get("text"), str) or not p.get("text"):
            err(f"paragraphs[{i}].text 必須是非空字串")
        hl = p.get("headingLevel")
        if hl is not None and (not isinstance(hl, int) or hl < 1 or hl > 6):
            err(f"paragraphs[{i}].headingLevel 必須是 1..6 或省略")
        sp = p.get("sectionPath")
        if sp is not None:
            if not isinstance(sp, list) or any(not isinstance(x, str) or not x for x in sp):
                err(f"paragraphs[{i}].sectionPath 必須是字串陣列")
        pid_to_idx[pid] = i

    # keypoints
    kp_seen: set[str] = set()
    for i, kp in enumerate(keypoints):
        if not isinstance(kp, dict):
            err(f"keypoints[{i}] 必須是物件")
            continue
        pid = kp.get("paragraphId")
        if not isinstance(pid, str) or pid not in pid_to_idx:
            err(f"keypoints[{i}].paragraphId 必須對應 paragraphs.id")
        else:
            kp_seen.add(pid)
        if not isinstance(kp.get("sentence"), str):
            err(f"keypoints[{i}].sentence 必須是字串")
        kws = kp.get("keywords")
        if not isinstance(kws, list) or not (1 <= len(kws) <= 5) or any(not isinstance(x, str) or not x for x in kws):
            err(f"keypoints[{i}].keywords 必須是 1–5 個非空字串")

    if len(kp_seen) != len(paragraphs):
        err("keypoints 必須涵蓋每一個 paragraph（每段一筆 keypoint）")

    # topics
    if len(topics) < 1:
        err("topics 至少需要 1 個")
    tid_set: set[str] = set()
    for i, t in enumerate(topics):
        if not isinstance(t, dict):
            err(f"topics[{i}] 必須是物件")
            continue
        tid = t.get("id")
        if not isinstance(tid, str) or not tid:
            err(f"topics[{i}].id 必須是非空字串")
        elif tid in tid_set:
            err(f"topic id 重複：{tid}")
        else:
            tid_set.add(tid)
        if not isinstance(t.get("title"), str) or not t.get("title"):
            err(f"topics[{i}].title 必須是非空字串")
        members = t.get("memberIds")
        if not isinstance(members, list) or not members or any(not isinstance(x, str) or x not in pid_to_idx for x in members):
            err(f"topics[{i}].memberIds 必須是對應 paragraphs.id 的非空陣列")
        sb = t.get("summaryBullets")
        if sb is not None:
            if not isinstance(sb, list) or any(not isinstance(x, str) or not x for x in sb):
                err(f"topics[{i}].summaryBullets 必須是字串陣列")

    # cards
    cid_set: set[str] = set()
    for i, c in enumerate(cards):
        if not isinstance(c, dict):
            err(f"cards[{i}] 必須是物件")
            continue
        cid = c.get("id")
        if not isinstance(cid, str) or not cid:
            err(f"cards[{i}].id 必須是非空字串")
        elif cid in cid_set:
            err(f"card id 重複：{cid}")
        else:
            cid_set.add(cid)
        if c.get("topicId") not in tid_set:
            err(f"cards[{i}].topicId 必須對應 topics.id")
        if not isinstance(c.get("title"), str) or not c.get("title"):
            err(f"cards[{i}].title 必須是非空字串")
        bullets = c.get("bullets")
        if not isinstance(bullets, list) or not (1 <= len(bullets) <= 5) or any(not isinstance(x, str) or not x for x in bullets):
            err(f"cards[{i}].bullets 必須是 1–5 條非空字串")

    # stats
    expected_stats = {
        "totalParagraphs": len(paragraphs),
        "totalKeypoints": len(keypoints),
        "totalTopics": len(topics),
        "totalCards": len(cards),
    }
    for k, v in expected_stats.items():
        if stats.get(k) != v:
            err(f"stats.{k} 必須等於 {v}（目前為 {stats.get(k)!r}）")

    # deterministic sort checks
    try:
        topic_min_idxs = []
        for t in topics:
            members = t.get("memberIds") or []
            min_idx = min(pid_to_idx[m] for m in members)
            topic_min_idxs.append(min_idx)
        if topic_min_idxs != sorted(topic_min_idxs):
            err("topics 順序需依各 topic memberIds 中最小 paragraphs.idx 由小到大排序")
    except Exception:
        err("無法檢查 topics 排序（memberIds 或 paragraphs.idx 異常）")

    # cards order: grouped by topic order
    topic_order = [t.get("id") for t in topics if isinstance(t, dict)]
    topic_pos = {tid: i for i, tid in enumerate(topic_order)}
    card_topic_positions = [topic_pos.get(c.get("topicId"), -1) for c in cards if isinstance(c, dict)]
    if any(x < 0 for x in card_topic_positions):
        err("cards.topicId 有不在 topics 的值，無法檢查 cards 排序")
    else:
        if card_topic_positions != sorted(card_topic_positions):
            err("cards 順序需依 topics 順序排列（同一 topic 的卡需相鄰）")

    # card count rule per topic
    cards_by_topic: dict[str, int] = defaultdict(int)
    for c in cards:
        if isinstance(c, dict) and isinstance(c.get("topicId"), str):
            cards_by_topic[c["topicId"]] += 1
    for t in topics:
        if not isinstance(t, dict) or not isinstance(t.get("id"), str):
            continue
        tid = t["id"]
        members = t.get("memberIds") or []
        expected = 2 if isinstance(members, list) and len(members) > 8 else 1
        if cards_by_topic.get(tid, 0) != expected:
            err(f"topic {tid} 的 cards 數量應為 {expected}（目前 {cards_by_topic.get(tid, 0)}）")

    return errors


def load_deck_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise AgentAError(f"找不到 deck.json：{p}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except UnicodeDecodeError as e:
        raise AgentAError("deck.json 不是 UTF-8，請轉成 UTF-8 後再試。") from e
    except json.JSONDecodeError as e:
        raise AgentAError(f"deck.json 不是合法 JSON：{e}") from e


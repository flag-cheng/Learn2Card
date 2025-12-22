from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: list[str]


def validate_deck(deck: Any) -> ValidationResult:
    errors: list[str] = []

    if not isinstance(deck, dict):
        return ValidationResult(False, ["根物件必須是 JSON object。"])

    # Required top-level keys
    for k in ["meta", "paragraphs", "keypoints", "topics", "cards", "stats"]:
        if k not in deck:
            errors.append(f"缺少頂層欄位：{k}")

    if errors:
        return ValidationResult(False, errors)

    meta = deck["meta"]
    if not isinstance(meta, dict):
        errors.append("meta 必須是 object。")
    else:
        for k in ["source", "generatedAt", "schemaVersion"]:
            if k not in meta:
                errors.append(f"meta 缺少欄位：{k}")
        if meta.get("schemaVersion") != "1.0.0":
            errors.append("meta.schemaVersion 必須為 '1.0.0'。")

    paragraphs = deck["paragraphs"]
    keypoints = deck["keypoints"]
    topics = deck["topics"]
    cards = deck["cards"]
    stats = deck["stats"]

    if not isinstance(paragraphs, list):
        errors.append("paragraphs 必須是 array。")
        paragraphs = []
    if not isinstance(keypoints, list):
        errors.append("keypoints 必須是 array。")
        keypoints = []
    if not isinstance(topics, list):
        errors.append("topics 必須是 array。")
        topics = []
    if not isinstance(cards, list):
        errors.append("cards 必須是 array。")
        cards = []
    if not isinstance(stats, dict):
        errors.append("stats 必須是 object。")
        stats = {}

    # Paragraph validation
    paragraph_ids: list[str] = []
    paragraph_idx_by_id: dict[str, int] = {}
    for i, p in enumerate(paragraphs):
        if not isinstance(p, dict):
            errors.append(f"paragraphs[{i}] 必須是 object。")
            continue
        pid = p.get("id")
        idx = p.get("idx")
        text = p.get("text")
        if not isinstance(pid, str) or not pid:
            errors.append(f"paragraphs[{i}].id 必須是非空字串。")
            continue
        if pid in paragraph_idx_by_id:
            errors.append(f"paragraph id 重複：{pid}")
        paragraph_ids.append(pid)
        if not isinstance(idx, int) or idx < 0:
            errors.append(f"paragraphs[{i}].idx 必須是 >=0 的整數。")
        else:
            paragraph_idx_by_id[pid] = idx
        if not isinstance(text, str) or not text.strip():
            errors.append(f"paragraphs[{i}].text 必須是非空字串。")
        # Optional fields
        if "headingLevel" in p and not isinstance(p["headingLevel"], int):
            errors.append(f"paragraphs[{i}].headingLevel 必須是 int（若提供）。")
        if "sectionPath" in p:
            sp = p["sectionPath"]
            if not isinstance(sp, list) or any(not isinstance(x, str) for x in sp):
                errors.append(f"paragraphs[{i}].sectionPath 必須是 string array（若提供）。")

    # Keypoints validation
    kp_paragraph_ids: set[str] = set()
    for i, kp in enumerate(keypoints):
        if not isinstance(kp, dict):
            errors.append(f"keypoints[{i}] 必須是 object。")
            continue
        pid = kp.get("paragraphId")
        if not isinstance(pid, str) or not pid:
            errors.append(f"keypoints[{i}].paragraphId 必須是非空字串。")
            continue
        kp_paragraph_ids.add(pid)
        if pid not in paragraph_idx_by_id:
            errors.append(f"keypoints[{i}].paragraphId 不存在於 paragraphs：{pid}")
        sent = kp.get("sentence")
        if not isinstance(sent, str) or not sent.strip():
            errors.append(f"keypoints[{i}].sentence 必須是非空字串。")
        kws = kp.get("keywords")
        if not isinstance(kws, list) or any(not isinstance(x, str) or not x for x in kws):
            errors.append(f"keypoints[{i}].keywords 必須是 string array。")
        else:
            if not (1 <= len(kws) <= 5):
                errors.append(f"keypoints[{i}].keywords 長度必須介於 1~5。")

    # Topics validation
    if len(topics) < 1:
        errors.append("topics 至少要有 1 個 topic。")
    topic_ids: set[str] = set()
    topic_min_idx: dict[str, int] = {}
    member_count_by_topic: dict[str, int] = {}

    for i, t in enumerate(topics):
        if not isinstance(t, dict):
            errors.append(f"topics[{i}] 必須是 object。")
            continue
        tid = t.get("id")
        if not isinstance(tid, str) or not tid:
            errors.append(f"topics[{i}].id 必須是非空字串。")
            continue
        if tid in topic_ids:
            errors.append(f"topic id 重複：{tid}")
        topic_ids.add(tid)

        title = t.get("title")
        if not isinstance(title, str) or not title.strip():
            errors.append(f"topics[{i}].title 必須是非空字串。")

        mids = t.get("memberIds")
        if not isinstance(mids, list) or any(not isinstance(x, str) or not x for x in mids):
            errors.append(f"topics[{i}].memberIds 必須是 string array。")
            continue
        if len(mids) < 1:
            errors.append(f"topics[{i}].memberIds 不得為空。")
        member_count_by_topic[tid] = len(mids)

        min_idx = None
        for mid in mids:
            if mid not in paragraph_idx_by_id:
                errors.append(f"topics[{i}].memberIds 包含不存在的 paragraphId：{mid}")
                continue
            pi = paragraph_idx_by_id[mid]
            min_idx = pi if min_idx is None else min(min_idx, pi)
        topic_min_idx[tid] = min_idx if min_idx is not None else 10**9

        if "summaryBullets" in t:
            sb = t["summaryBullets"]
            if not isinstance(sb, list) or any(not isinstance(x, str) for x in sb):
                errors.append(f"topics[{i}].summaryBullets 必須是 string array（若提供）。")

    # Cards validation
    card_ids: set[str] = set()
    cards_by_topic: dict[str, list[dict[str, Any]]] = {}
    for i, c in enumerate(cards):
        if not isinstance(c, dict):
            errors.append(f"cards[{i}] 必須是 object。")
            continue
        cid = c.get("id")
        if not isinstance(cid, str) or not cid:
            errors.append(f"cards[{i}].id 必須是非空字串。")
        elif cid in card_ids:
            errors.append(f"card id 重複：{cid}")
        else:
            card_ids.add(cid)

        tid = c.get("topicId")
        if not isinstance(tid, str) or not tid:
            errors.append(f"cards[{i}].topicId 必須是非空字串。")
        elif tid not in topic_ids:
            errors.append(f"cards[{i}].topicId 不存在於 topics：{tid}")

        title = c.get("title")
        if not isinstance(title, str) or not title.strip():
            errors.append(f"cards[{i}].title 必須是非空字串。")

        bullets = c.get("bullets")
        if not isinstance(bullets, list) or any(not isinstance(x, str) or not x.strip() for x in bullets):
            errors.append(f"cards[{i}].bullets 必須是非空字串 array。")
        else:
            if not (1 <= len(bullets) <= 5):
                errors.append(f"cards[{i}].bullets 長度必須介於 1~5。")

        if isinstance(tid, str) and tid:
            cards_by_topic.setdefault(tid, []).append(c)

    # Stats validation
    def _require_int(name: str) -> None:
        v = stats.get(name)
        if not isinstance(v, int) or v < 0:
            errors.append(f"stats.{name} 必須是 >=0 的整數。")

    for k in ["totalParagraphs", "totalKeypoints", "totalTopics", "totalCards"]:
        _require_int(k)

    if isinstance(stats.get("totalParagraphs"), int) and stats["totalParagraphs"] != len(paragraphs):
        errors.append("stats.totalParagraphs 與 paragraphs 長度不一致。")
    if isinstance(stats.get("totalKeypoints"), int) and stats["totalKeypoints"] != len(keypoints):
        errors.append("stats.totalKeypoints 與 keypoints 長度不一致。")
    if isinstance(stats.get("totalTopics"), int) and stats["totalTopics"] != len(topics):
        errors.append("stats.totalTopics 與 topics 長度不一致。")
    if isinstance(stats.get("totalCards"), int) and stats["totalCards"] != len(cards):
        errors.append("stats.totalCards 與 cards 長度不一致。")

    # Deterministic ordering validation (only if basics passed enough)
    if topics and paragraph_idx_by_id:
        # Topic order: by min member paragraph idx ascending
        mins = [topic_min_idx.get(t.get("id", ""), 10**9) for t in topics if isinstance(t, dict)]
        if mins != sorted(mins):
            errors.append("topics 排序必須依 memberIds 中最小 paragraphs.idx 由小到大（deterministic）。")

        # Card order: grouped by topic order
        topic_order = {t["id"]: i for i, t in enumerate(topics) if isinstance(t, dict) and isinstance(t.get("id"), str)}
        card_topic_orders: list[int] = []
        for c in cards:
            if not isinstance(c, dict):
                continue
            tid = c.get("topicId")
            if isinstance(tid, str):
                card_topic_orders.append(topic_order.get(tid, 10**9))
        if card_topic_orders != sorted(card_topic_orders):
            errors.append("cards 排序必須依 topics 順序（deterministic）。")

    # Card split rule (strict): each topic has 1 card, or 2 cards if memberIds > 8
    for tid, member_count in member_count_by_topic.items():
        expected = 2 if member_count > 8 else 1
        actual = len(cards_by_topic.get(tid, []))
        if actual != expected:
            errors.append(
                f"topic {tid} 需有 {expected} 張卡（memberIds={member_count}），實際為 {actual}。"
            )

    return ValidationResult(len(errors) == 0, errors)


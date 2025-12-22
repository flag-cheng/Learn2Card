from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError

from .models import Deck


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


def parse_deck(obj: object) -> tuple[Deck | None, list[ValidationIssue]]:
    try:
        return Deck.model_validate(obj), []
    except ValidationError as e:
        issues = [
            ValidationIssue(code="schema", message=f"{err.get('loc')}: {err.get('msg')}")
            for err in e.errors()
        ]
        return None, issues


def validate_deck(deck: Deck) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    para_ids = [p.id for p in deck.paragraphs]
    para_id_set = set(para_ids)
    topic_ids = [t.id for t in deck.topics]
    topic_id_set = set(topic_ids)

    # id uniqueness
    if len(para_ids) != len(para_id_set):
        issues.append(ValidationIssue("id", "paragraphs.id must be unique"))
    if len(topic_ids) != len(topic_id_set):
        issues.append(ValidationIssue("id", "topics.id must be unique"))
    card_ids = [c.id for c in deck.cards]
    if len(card_ids) != len(set(card_ids)):
        issues.append(ValidationIssue("id", "cards.id must be unique"))

    # referential integrity
    kp_para_ids = [k.paragraphId for k in deck.keypoints]
    for pid in kp_para_ids:
        if pid not in para_id_set:
            issues.append(ValidationIssue("ref", f"keypoints.paragraphId not found: {pid}"))

    for t in deck.topics:
        for pid in t.memberIds:
            if pid not in para_id_set:
                issues.append(ValidationIssue("ref", f"topics[{t.id}].memberIds contains unknown paragraphId: {pid}"))

    for c in deck.cards:
        if c.topicId not in topic_id_set:
            issues.append(ValidationIssue("ref", f"cards[{c.id}].topicId not found: {c.topicId}"))

    # bullets length rule is already enforced by schema, but keep explicit message
    for c in deck.cards:
        if not (1 <= len(c.bullets) <= 5):
            issues.append(ValidationIssue("rule", f"cards[{c.id}].bullets length must be 1..5"))

    # stats
    expected = {
        "totalParagraphs": len(deck.paragraphs),
        "totalKeypoints": len(deck.keypoints),
        "totalTopics": len(deck.topics),
        "totalCards": len(deck.cards),
    }
    actual = deck.stats.model_dump()
    for k, v in expected.items():
        if actual.get(k) != v:
            issues.append(ValidationIssue("stats", f"stats.{k}={actual.get(k)} but expected {v}"))

    # deterministic order rules
    idx_by_pid = {p.id: p.idx for p in deck.paragraphs}
    expected_topic_order = sorted(
        deck.topics,
        key=lambda t: min(idx_by_pid.get(pid, 10**9) for pid in t.memberIds) if t.memberIds else 10**9,
    )
    if [t.id for t in expected_topic_order] != [t.id for t in deck.topics]:
        issues.append(ValidationIssue("order", "topics must be sorted by min member paragraph idx asc"))

    topic_pos = {t.id: i for i, t in enumerate(deck.topics)}
    expected_card_order = sorted(deck.cards, key=lambda c: topic_pos.get(c.topicId, 10**9))
    if [c.id for c in expected_card_order] != [c.id for c in deck.cards]:
        issues.append(ValidationIssue("order", "cards must follow topics order"))

    # at least 1 topic
    if len(deck.topics) < 1:
        issues.append(ValidationIssue("rule", "must generate at least 1 topic"))

    # card splitting rule: each topic default 1, if memberIds>8 then 2
    cards_by_topic: dict[str, int] = {}
    for c in deck.cards:
        cards_by_topic[c.topicId] = cards_by_topic.get(c.topicId, 0) + 1
    for t in deck.topics:
        expected_cards = 2 if len(t.memberIds) > 8 else 1
        got = cards_by_topic.get(t.id, 0)
        if got != expected_cards:
            issues.append(
                ValidationIssue(
                    "rule",
                    f"topic {t.id} has {len(t.memberIds)} members, expected {expected_cards} card(s) but got {got}",
                )
            )

    return issues


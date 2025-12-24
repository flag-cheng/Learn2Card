from __future__ import annotations

from .models import Card, Keypoint, PipelineOptions, Topic
from .text_utils import unique_preserve_order


def build_cards(
    topics: list[Topic],
    keypoints: list[Keypoint],
    options: PipelineOptions,
) -> list[Card]:
    kp_by_pid = {k.paragraphId: k for k in keypoints}
    cards: list[Card] = []

    def bullets_for(member_ids: list[str]) -> list[str]:
        sentences = [kp_by_pid[pid].sentence for pid in member_ids if pid in kp_by_pid and kp_by_pid[pid].sentence.strip()]
        bullets = unique_preserve_order(sentences)
        target = max(1, min(options.targetBulletsPerCard, options.maxBulletsPerCard))
        # Try to hit target 3-5 but allow shorter if not enough content.
        bullets = bullets[: max(1, min(len(bullets), options.maxBulletsPerCard, target))]
        return bullets if bullets else ["（內容不足，請補充更多段落或文字）"]

    card_idx = 0
    for t in topics:
        member_ids = list(t.memberIds)
        if len(member_ids) > 8:
            mid = len(member_ids) // 2
            parts = [member_ids[:mid], member_ids[mid:]]
            for pi, part in enumerate(parts, start=1):
                card_idx += 1
                cards.append(
                    Card(
                        id=f"c{card_idx}",
                        topicId=t.id,
                        title=f"{t.title}（第{pi}部分）",
                        bullets=bullets_for(part),
                    )
                )
        else:
            card_idx += 1
            cards.append(
                Card(
                    id=f"c{card_idx}",
                    topicId=t.id,
                    title=t.title,
                    bullets=bullets_for(member_ids),
                )
            )

    return cards


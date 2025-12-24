from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .models import Keypoint, Paragraph, PipelineOptions, Topic
from .text_utils import unique_preserve_order


@dataclass
class _TopicState:
    id: str
    member_ids: list[str]
    centroid: np.ndarray  # normalized


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    # both expected normalized
    return float(a @ b)


def _update_centroid(centroid: np.ndarray, v: np.ndarray, *, n_members: int) -> np.ndarray:
    # Online mean then normalize.
    new = (centroid * n_members + v) / float(n_members + 1)
    norm = float(np.linalg.norm(new))
    return new / norm if norm > 0 else new


def cluster_topics(
    paragraphs: list[Paragraph],
    keypoints: list[Keypoint],
    vectors: np.ndarray,
    options: PipelineOptions,
) -> tuple[list[Topic], dict[str, list[str]]]:
    """Threshold-based clustering with maxTopics cap.

    Deterministic behavior:
    - Process paragraphs by idx order.
    - Create a new topic when similarity < threshold and topic count < maxTopics.
    - Otherwise assign to the best existing topic.
    - Output topics sorted by the smallest member paragraph idx.
    """

    if len(paragraphs) == 0:
        return [], {}
    if vectors.shape[0] != len(paragraphs):
        raise ValueError("vectors length mismatch with paragraphs")

    kp_by_pid = {k.paragraphId: k for k in keypoints}
    pid_to_idx = {p.id: p.idx for p in paragraphs}

    states: list[_TopicState] = []

    # Always create at least one topic
    first = paragraphs[0]
    states.append(_TopicState(id="t0", member_ids=[first.id], centroid=vectors[0].copy()))

    for i in range(1, len(paragraphs)):
        pid = paragraphs[i].id
        v = vectors[i]
        # find best topic
        best_j = 0
        best_sim = _cosine(states[0].centroid, v)
        for j in range(1, len(states)):
            sim = _cosine(states[j].centroid, v)
            # deterministic tie-breaker: lowest topic index
            if sim > best_sim + 1e-12:
                best_sim = sim
                best_j = j

        if best_sim >= options.topicThreshold or len(states) >= options.maxTopics:
            st = states[best_j]
            st.centroid = _update_centroid(st.centroid, v, n_members=len(st.member_ids))
            st.member_ids.append(pid)
        else:
            tid = f"t{len(states)}"
            states.append(_TopicState(id=tid, member_ids=[pid], centroid=v.copy()))

    # Derive stable ordering by min paragraph idx
    states_sorted = sorted(states, key=lambda st: min(pid_to_idx[pid] for pid in st.member_ids))

    topics: list[Topic] = []
    members_by_topic: dict[str, list[str]] = {}

    for new_idx, st in enumerate(states_sorted):
        tid = f"t{new_idx}"
        member_ids = sorted(st.member_ids, key=lambda pid: pid_to_idx[pid])
        members_by_topic[tid] = member_ids

        # Title: most frequent keyword among members; fallback to first member sentence
        kw_freq: dict[str, int] = {}
        for pid in member_ids:
            kp = kp_by_pid.get(pid)
            if not kp:
                continue
            for kw in kp.keywords:
                kw_freq[kw] = kw_freq.get(kw, 0) + 1
        if kw_freq:
            title = sorted(kw_freq.items(), key=lambda x: (-x[1], x[0]))[0][0]
        else:
            first_kp = kp_by_pid.get(member_ids[0])
            title = (first_kp.sentence if first_kp else member_ids[0]).strip()
            title = title[:60].rstrip() if len(title) > 60 else title

        # summaryBullets: unique member keypoint sentences, keep order, cap
        bullets = unique_preserve_order(
            [kp_by_pid[pid].sentence for pid in member_ids if pid in kp_by_pid and kp_by_pid[pid].sentence.strip()]
        )
        bullets = bullets[: options.maxSummaryBulletsPerTopic]

        topics.append(Topic(id=tid, title=title, memberIds=member_ids, summaryBullets=bullets))

    return topics, members_by_topic


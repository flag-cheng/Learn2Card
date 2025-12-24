from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from .cards import build_cards
from .cluster import cluster_topics
from .embedding import EmbeddingError, embed_paragraphs
from .keypoints import extract_keypoints
from .models import AgentAOutput, PipelineOptions, Stats
from .segmenter import segment_text


class PipelineInputError(ValueError):
    pass


@dataclass
class DebugInfo:
    options: dict[str, Any]
    total_chars: int
    note: str = ""


def run_agent_a(
    text: str,
    *,
    options: PipelineOptions | None = None,
    debug: bool = False,
) -> tuple[AgentAOutput, DebugInfo | None]:
    """Run Agent A pipeline.

    Input must be a text string (no file/URL I/O).
    Returns (output, debugInfo|None).
    """

    opts = options or PipelineOptions()

    if text is None:
        raise PipelineInputError("Input text is None. Please provide a text string.")
    if not isinstance(text, str):
        raise PipelineInputError("Input must be a text string (str).")
    if not text.strip():
        raise PipelineInputError("Input text is empty.")
    if len(text) > opts.maxChars:
        raise PipelineInputError(f"Input too long: {len(text)} chars (maxChars={opts.maxChars}).")

    paragraphs = segment_text(text)
    if not paragraphs:
        raise PipelineInputError("No paragraphs found after segmentation.")

    keypoints = extract_keypoints(paragraphs, opts)

    try:
        vectors = embed_paragraphs(paragraphs, opts)
    except EmbeddingError as e:
        raise PipelineInputError(str(e)) from e

    topics, _ = cluster_topics(paragraphs, keypoints, vectors, opts)
    if not topics:
        # Should not happen due to "at least 1 topic" logic; guard anyway.
        topics = []

    cards = build_cards(topics, keypoints, opts)

    stats = Stats(
        totalParagraphs=len(paragraphs),
        totalKeypoints=len(keypoints),
        totalTopics=len(topics),
        totalCards=len(cards),
    )

    try:
        output = AgentAOutput(
            paragraphs=paragraphs,
            keypoints=keypoints,
            topics=topics,
            cards=cards,
            stats=stats,
        )
    except ValidationError as e:
        raise RuntimeError(f"Internal schema validation failed: {e}") from e

    debug_info = DebugInfo(options=opts.to_debug_dict(), total_chars=len(text)) if debug else None
    return output, debug_info


def to_stable_json(output: AgentAOutput) -> str:
    """Deterministic JSON string (stable key order, UTF-8, no float noise)."""

    data = output.model_dump()
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


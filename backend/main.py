from __future__ import annotations

import argparse
import sys

from agent_a.models import PipelineOptions
from agent_a.pipeline import PipelineInputError, run_agent_a, to_stable_json


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="learn2cards-agent-a",
        description="Agent A demo CLI: text -> paragraphs/keypoints/topics/cards/stats (JSON). No file/URL I/O.",
    )

    p.add_argument(
        "--text",
        required=True,
        help="Input text string. Note: this CLI does not accept file paths/URLs.",
    )
    p.add_argument(
        "--unescape",
        action="store_true",
        help="Interpret common escape sequences in --text (e.g. \\n, \\t).",
    )
    p.add_argument("--language", default="zh-TW", help="Language hint (default: zh-TW).")
    p.add_argument("--topic-threshold", type=float, default=0.75, help="Topic similarity threshold (default: 0.75).")
    p.add_argument("--max-topics", type=int, default=5, help="Max topics (default: 5, min: 1).")
    p.add_argument("--embedding-dim", type=int, default=384, help="Embedding dimension (default: 384).")
    p.add_argument("--embedding-batch-size", type=int, default=64, help="Embedding batch size (default: 64).")
    p.add_argument("--max-bullets-per-card", type=int, default=5, help="Max bullets per card (1-5, default: 5).")
    p.add_argument("--target-bullets-per-card", type=int, default=4, help="Target bullets per card (default: 4).")
    p.add_argument("--max-chars", type=int, default=200_000, help="Max input characters (default: 200000).")
    p.add_argument("--debug", action="store_true", help="Print intermediate info to stderr.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    text = args.text
    if args.unescape:
        # Only CLI convenience; the core pipeline still operates on a plain str.
        text = bytes(text, "utf-8").decode("unicode_escape")

    options = PipelineOptions(
        language=args.language,
        topicThreshold=args.topic_threshold,
        maxTopics=args.max_topics,
        embeddingDimension=args.embedding_dim,
        embeddingBatchSize=args.embedding_batch_size,
        maxBulletsPerCard=args.max_bullets_per_card,
        targetBulletsPerCard=args.target_bullets_per_card,
        maxChars=args.max_chars,
    )

    try:
        output, dbg = run_agent_a(text, options=options, debug=args.debug)
    except PipelineInputError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    if args.debug and dbg is not None:
        print(f"[debug] total_chars={dbg.total_chars}", file=sys.stderr)
        print(f"[debug] options={dbg.options}", file=sys.stderr)
        print(
            f"[debug] counts paragraphs={output.stats.totalParagraphs} keypoints={output.stats.totalKeypoints} "
            f"topics={output.stats.totalTopics} cards={output.stats.totalCards}",
            file=sys.stderr,
        )

    print(to_stable_json(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

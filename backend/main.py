from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pipeline import ProcessingError, build_deck, write_deck_json


REPO_ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Learn2Cards Backend CLI（僅接受純文字字串；輸出固定為 frontend/public/deck.json）"
    )
    parser.add_argument("--text", required=True, help="輸入的純文字內容（必填）")
    parser.add_argument("--topic-threshold", type=float, default=0.75, help="分群閾值（0.0–1.0，預設 0.75）")
    parser.add_argument("--max-topics", type=int, default=5, help="最大主題數（最小 1，預設 5）")
    parser.add_argument("--max-bullets", type=int, default=5, help="每卡 bullets 上限（1–5，預設 5）")
    parser.add_argument("--debug", action="store_true", help="顯示除錯資訊")
    args = parser.parse_args(argv)

    try:
        deck = build_deck(
            text=args.text,
            topic_threshold=args.topic_threshold,
            max_topics=args.max_topics,
            max_bullets=args.max_bullets,
        )
        out_path = write_deck_json(deck, repo_root=REPO_ROOT)

        stats = deck.get("stats") or {}
        print(f"✓ 已成功輸出到：{out_path.resolve()}", file=sys.stderr)
        print(f"  - 段落數：{stats.get('paragraphCount', 0)}", file=sys.stderr)
        print(f"  - 主題數：{stats.get('topicCount', 0)}", file=sys.stderr)
        print(f"  - 卡片數：{stats.get('cardCount', 0)}", file=sys.stderr)

        if args.debug:
            print("— debug —", file=sys.stderr)
            print(f"repoRoot={REPO_ROOT}", file=sys.stderr)
            print(f"topicThreshold={args.topic_threshold}", file=sys.stderr)
            print(f"maxTopics={args.max_topics}", file=sys.stderr)
            print(f"maxBullets={args.max_bullets}", file=sys.stderr)

        return 0
    except ProcessingError as e:
        print(str(e), file=sys.stderr)
        return 2
    except Exception as e:
        print(f"內部錯誤：{e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

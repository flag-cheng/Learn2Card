from __future__ import annotations

import argparse
import sys
from pathlib import Path

from backend.agent_a import (
    AgentAError,
    generate_deck,
    load_deck_json,
    read_text_file,
    validate_deck,
    write_deck_json,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "frontend/public/deck.json"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cli", description="Learn2Cards Agent A CLI (generate/validate)")
    sub = p.add_subparsers(dest="command", required=True)

    g = sub.add_parser("generate", help="從 Markdown/純文字產生 deck.json")
    g.add_argument("--input", required=True, help="輸入檔案路徑（Markdown/純文字）")
    g.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help=f"輸出 deck.json 路徑（預設：{DEFAULT_OUTPUT}）",
    )
    g.add_argument("--force", action="store_true", help="覆寫既有輸出檔")
    g.add_argument("--max-topics", type=int, default=5, help="主題上限（預設 5，至少 1）")
    g.add_argument("--topic-threshold", type=float, default=0.75, help="相似度閾值（預設 0.75）")
    g.add_argument("--bullets-per-card", type=int, default=5, help="每卡 bullets 上限（1–5，預設 5）")
    g.add_argument("--embedding-dim", type=int, default=256, help="向量維度（預設 256）")
    g.add_argument("--batch-size", type=int, default=64, help="保留參數（demo 不使用）")
    g.add_argument("--language", choices=["zh", "en", "auto"], default="auto", help="語言（預設 auto）")
    g.add_argument("--verbose", action="store_true", help="輸出中間結果（除錯用）")
    g.add_argument("--temperature", type=float, default=0.0, help="保留參數（demo 不使用）")
    g.add_argument("--top-p", type=float, default=1.0, help="保留參數（demo 不使用）")
    g.add_argument("--seed", type=int, default=0, help="保留參數（demo 不使用；目前流程本身 deterministic）")
    g.add_argument("--max-tokens", type=int, default=0, help="保留參數（demo 不使用）")
    g.add_argument("--model", default="demo", help="保留參數（demo 不使用）")

    v = sub.add_parser("validate", help="驗證 deck.json 是否符合 schema 與規則")
    v.add_argument("--input", required=True, help="deck.json 路徑")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "generate":
            text = read_text_file(args.input)
            deck = generate_deck(
                text,
                source=str(args.input),
                language=args.language,
                topic_threshold=float(args.topic_threshold),
                max_topics=int(args.max_topics),
                bullets_per_card=int(args.bullets_per_card),
                embedding_dim=int(args.embedding_dim),
                verbose=bool(args.verbose),
            )
            write_deck_json(deck, args.output, force=bool(args.force))

            # Always validate what we wrote.
            written = load_deck_json(args.output)
            errs = validate_deck(written)
            if errs:
                for e in errs:
                    print(f"- {e}", file=sys.stderr)
                print("產生 deck.json，但 validate 失敗。", file=sys.stderr)
                return 2

            print(f"OK：已產生 {args.output}")
            return 0

        if args.command == "validate":
            deck = load_deck_json(args.input)
            errs = validate_deck(deck)
            if errs:
                for e in errs:
                    print(f"- {e}", file=sys.stderr)
                print("FAIL", file=sys.stderr)
                return 2
            print("OK")
            return 0

        parser.print_help()
        return 1

    except AgentAError as e:
        print(str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())


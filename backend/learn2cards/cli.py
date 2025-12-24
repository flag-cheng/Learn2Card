from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .models import DeckOptions
from .pipeline import generate_deck
from .validate import parse_deck, validate_deck


def _project_root() -> Path:
    # Walk up from this file until we find 'frontend' folder.
    here = Path(__file__).resolve()
    for p in [here.parent, *here.parents]:
        if (p / "frontend").is_dir():
            return p
        if (p / "backend").is_dir() and (p / "frontend").is_dir():
            return p
    # fallback to repo root assumption: backend/learn2cards/..
    return here.parents[2]


def _default_output_path() -> Path:
    root = _project_root()
    return root / "frontend" / "public" / "deck.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli", description="Learn2Cards Agent A CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    g = sub.add_parser("generate", help="Generate deck.json from a Markdown/txt input file")
    g.add_argument("--input", required=True, help="Path to input .md/.txt file")
    g.add_argument("--output", default=None, help="Output path (default: frontend/public/deck.json)")
    g.add_argument("--force", action="store_true", help="Overwrite output if exists")
    g.add_argument("--max-topics", type=int, default=5)
    g.add_argument("--topic-threshold", type=float, default=0.75)
    g.add_argument("--language", choices=["zh", "en", "auto"], default="auto")
    g.add_argument("--temperature", type=float, default=0.2)
    g.add_argument("--top-p", type=float, default=1.0)
    g.add_argument("--seed", type=int, default=None)
    g.add_argument("--verbose", action="store_true")

    v = sub.add_parser("validate", help="Validate an existing deck.json")
    v.add_argument("--input", required=True, help="Path to deck.json")

    args = parser.parse_args(argv)

    if args.command == "generate":
        in_path = Path(args.input)
        if not in_path.exists():
            print(f"ERROR: input not found: {in_path}", file=sys.stderr)
            return 2
        try:
            raw = in_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            print("ERROR: input must be UTF-8 text", file=sys.stderr)
            return 2

        out_path = Path(args.output) if args.output else _default_output_path()
        if out_path.exists() and not args.force:
            print(f"ERROR: output already exists: {out_path} (use --force to overwrite)", file=sys.stderr)
            return 2
        out_path.parent.mkdir(parents=True, exist_ok=True)

        options = DeckOptions(
            maxTopics=args.max_topics,
            topicThreshold=args.topic_threshold,
            language=args.language,
            temperature=args.temperature,
            top_p=args.top_p,
            seed=args.seed,
            verbose=args.verbose,
        )
        try:
            deck = generate_deck(raw, source=str(in_path), options=options)
        except Exception as e:
            print(f"ERROR: generate failed: {e}", file=sys.stderr)
            return 1

        out_path.write_text(deck.model_dump_json(indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        # Run validate to guarantee output meets schema/rules
        issues = validate_deck(deck)
        if issues:
            print("WARN: generated deck has validation issues:", file=sys.stderr)
            for it in issues:
                print(f"- {it}", file=sys.stderr)
            return 1

        print(f"OK: wrote {out_path}")
        return 0

    if args.command == "validate":
        p = Path(args.input)
        if not p.exists():
            print(f"ERROR: input not found: {p}", file=sys.stderr)
            return 2
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            print("ERROR: deck.json must be UTF-8", file=sys.stderr)
            return 2
        except json.JSONDecodeError as e:
            print(f"ERROR: invalid JSON: {e}", file=sys.stderr)
            return 2

        deck, schema_issues = parse_deck(obj)
        if schema_issues:
            for it in schema_issues:
                print(f"- {it}", file=sys.stderr)
            return 1
        assert deck is not None

        issues = validate_deck(deck)
        if issues:
            for it in issues:
                print(f"- {it}", file=sys.stderr)
            return 1

        print("OK")
        return 0

    print("ERROR: unknown command", file=sys.stderr)
    return 2


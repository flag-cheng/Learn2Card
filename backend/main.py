from __future__ import annotations

from cli import main as cli_main


def main() -> int:
    # Backward-compatible entrypoint: `uv run python main.py ...`
    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())

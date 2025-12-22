from __future__ import annotations

import sys

from learn2cards.cli import main as _cli_main


def main() -> None:
    raise SystemExit(_cli_main())


if __name__ == "__main__":
    main()

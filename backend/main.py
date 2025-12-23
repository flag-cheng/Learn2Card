from __future__ import annotations

from learn2cards.agent_a import main as agent_a_main


def main() -> int:
    # Demo entrypoint (no file I/O): delegate to Agent A CLI.
    return agent_a_main()


if __name__ == "__main__":
    raise SystemExit(main())

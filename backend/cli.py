from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from learn2cards.pipeline import AnalyzeOptions, PipelineError, analyze_text, to_pretty_json
from learn2cards.validate import validate_deck


def _repo_root() -> Path:
    # backend/cli.py -> repo root
    return Path(__file__).resolve().parents[1]


def _read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SystemExit(f"找不到檔案：{path}")
    except UnicodeDecodeError:
        raise SystemExit(f"檔案編碼錯誤（請使用 UTF-8）：{path}")


def cmd_generate(args: argparse.Namespace) -> int:
    inp = Path(args.input)
    text = _read_text_file(inp)

    out: Path
    if args.output:
        out = Path(args.output)
    else:
        out = _repo_root() / "frontend" / "public" / "deck.json"

    if out.exists() and not args.force:
        raise SystemExit(f"輸出檔已存在：{out}（加上 --force 以覆寫）")
    out.parent.mkdir(parents=True, exist_ok=True)

    opt = AnalyzeOptions(
        language=args.language,
        max_topics=args.max_topics,
        topic_threshold=args.topic_threshold,
        max_bullets_per_card=args.max_bullets_per_card,
        target_bullets_per_card=args.target_bullets_per_card,
        embedding_dim=args.embedding_dim,
        source=str(inp.name),
        verbose=args.verbose,
    )

    try:
        deck = analyze_text(text, opt)
    except PipelineError as e:
        raise SystemExit(str(e))

    # Validate before writing (fail fast)
    res = validate_deck(deck)
    if not res.ok:
        msg = "產生的 deck.json 未通過 validate：\n- " + "\n- ".join(res.errors)
        raise SystemExit(msg)

    out.write_text(to_pretty_json(deck), encoding="utf-8")
    print(f"OK: 已輸出 {out}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    path = Path(args.input)
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SystemExit(f"找不到檔案：{path}")
    except UnicodeDecodeError:
        raise SystemExit(f"檔案編碼錯誤（請使用 UTF-8）：{path}")

    try:
        deck = json.loads(raw)
    except json.JSONDecodeError as e:
        raise SystemExit(f"JSON 解析失敗：{e}")

    res = validate_deck(deck)
    if res.ok:
        print("OK")
        return 0
    print("FAIL")
    for err in res.errors:
        print(f"- {err}")
    return 1


def cmd_analyze(args: argparse.Namespace) -> int:
    # Demo helper: analyze a raw text string (no file I/O in the pipeline)
    text = args.text
    if text == "-":
        text = sys.stdin.read()

    opt = AnalyzeOptions(
        language=args.language,
        max_topics=args.max_topics,
        topic_threshold=args.topic_threshold,
        max_bullets_per_card=args.max_bullets_per_card,
        target_bullets_per_card=args.target_bullets_per_card,
        embedding_dim=args.embedding_dim,
        source=args.source or "text",
        verbose=args.verbose,
    )

    try:
        deck = analyze_text(text, opt)
    except PipelineError as e:
        raise SystemExit(str(e))

    print(to_pretty_json(deck), end="")
    return 0


class _Handler(BaseHTTPRequestHandler):
    server_version = "learn2cards/0.1"

    def _send_json(self, status: int, obj: object) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/healthz":
            return self._send_json(200, {"ok": True})
        return self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/analyze":
            return self._send_json(404, {"error": "not found"})

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self._send_json(400, {"error": "invalid Content-Length"})
        raw = self.rfile.read(length) if length > 0 else b""
        try:
            payload = json.loads(raw.decode("utf-8") if raw else "{}")
        except Exception as e:
            return self._send_json(400, {"error": f"invalid json: {e}"})

        text = payload.get("text", "")
        if not isinstance(text, str):
            return self._send_json(400, {"error": "text must be a string"})

        opt_in = payload.get("options") or {}
        if not isinstance(opt_in, dict):
            return self._send_json(400, {"error": "options must be an object"})

        # Whitelist mapping (avoid arbitrary fields)
        try:
            opt = AnalyzeOptions(
                language=opt_in.get("language", "auto"),
                max_topics=int(opt_in.get("max_topics", 5)),
                topic_threshold=float(opt_in.get("topic_threshold", 0.75)),
                max_bullets_per_card=int(opt_in.get("max_bullets_per_card", 5)),
                target_bullets_per_card=int(opt_in.get("target_bullets_per_card", 4)),
                embedding_dim=int(opt_in.get("embedding_dim", 256)),
                source=str(opt_in.get("source", "text")),
                verbose=bool(opt_in.get("verbose", False)),
            )
        except Exception as e:
            return self._send_json(400, {"error": f"invalid options: {e}"})

        try:
            deck = analyze_text(text, opt)
        except PipelineError as e:
            return self._send_json(400, {"error": str(e)})
        except Exception as e:
            return self._send_json(500, {"error": f"internal error: {e}"})

        return self._send_json(200, deck)


def cmd_serve(args: argparse.Namespace) -> int:
    httpd = ThreadingHTTPServer((args.host, args.port), _Handler)
    print(f"Serving on http://{args.host}:{args.port} (POST /analyze, GET /healthz)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down...")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="learn2cards-cli", description="Agent A CLI (generate/validate)")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_gen = sub.add_parser("generate", help="從 .md/.txt 產生 deck.json")
    p_gen.add_argument("--input", required=True, help="輸入檔案路徑（.md 或 .txt）")
    p_gen.add_argument("--output", help="輸出 JSON 路徑（預設 frontend/public/deck.json）")
    p_gen.add_argument("--force", action="store_true", help="覆寫既有輸出檔")
    p_gen.add_argument("--language", choices=["zh", "en", "auto"], default="auto")
    p_gen.add_argument("--max-topics", type=int, default=5)
    p_gen.add_argument("--topic-threshold", type=float, default=0.75)
    p_gen.add_argument("--embedding-dim", type=int, default=256)
    p_gen.add_argument("--max-bullets-per-card", type=int, default=5)
    p_gen.add_argument("--target-bullets-per-card", type=int, default=4)
    p_gen.add_argument("--verbose", action="store_true")
    p_gen.set_defaults(func=cmd_generate)

    p_val = sub.add_parser("validate", help="驗證 deck.json 是否符合 schema 與規則")
    p_val.add_argument("--input", required=True, help="deck.json 路徑")
    p_val.set_defaults(func=cmd_validate)

    p_ana = sub.add_parser("analyze", help="直接分析文字（--text 或 stdin），輸出 JSON 到 stdout")
    p_ana.add_argument("--text", required=True, help="要分析的文字；傳 '-' 代表從 stdin 讀取")
    p_ana.add_argument("--source", help="meta.source")
    p_ana.add_argument("--language", choices=["zh", "en", "auto"], default="auto")
    p_ana.add_argument("--max-topics", type=int, default=5)
    p_ana.add_argument("--topic-threshold", type=float, default=0.75)
    p_ana.add_argument("--embedding-dim", type=int, default=256)
    p_ana.add_argument("--max-bullets-per-card", type=int, default=5)
    p_ana.add_argument("--target-bullets-per-card", type=int, default=4)
    p_ana.add_argument("--verbose", action="store_true")
    p_ana.set_defaults(func=cmd_analyze)

    p_srv = sub.add_parser("serve", help="啟動簡易 HTTP API（無外部依賴）")
    p_srv.add_argument("--host", default="127.0.0.1")
    p_srv.add_argument("--port", type=int, default=8000)
    p_srv.set_defaults(func=cmd_serve)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())


from __future__ import annotations

import json
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0") or "0")
    raw = handler.rfile.read(length) if length > 0 else b""
    try:
        return json.loads(raw.decode("utf-8") if raw else "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 解析失敗：{exc.msg}") from exc


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Trim and collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def _split_markdown_blocks(text: str) -> list[str]:
    """
    Very small, deterministic splitter:
    - Treat markdown headings as their own blocks.
    - Otherwise split by blank lines.
    """
    lines = text.split("\n")
    blocks: list[str] = []
    buf: list[str] = []

    def flush_buf() -> None:
        nonlocal buf
        block = "\n".join(buf).strip()
        if block:
            blocks.append(block)
        buf = []

    for line in lines:
        if re.match(r"^\s{0,3}#{1,6}\s+\S", line):
            flush_buf()
            blocks.append(line.strip())
            continue
        if line.strip() == "":
            flush_buf()
            continue
        buf.append(line)

    flush_buf()
    return blocks


def _extract_keywords(text: str, limit: int = 4) -> list[str]:
    # Tokenize by basic unicode word chars; keep CJK chunks too.
    tokens = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{2,}", text)
    stop = {
        "the",
        "and",
        "or",
        "to",
        "of",
        "in",
        "a",
        "an",
        "is",
        "are",
        "for",
        "with",
        "on",
        "as",
        "be",
        "this",
        "that",
        "it",
        "we",
        "you",
    }
    freq: dict[str, int] = {}
    for t in tokens:
        key = t.lower()
        if len(key) <= 1 or key in stop:
            continue
        freq[key] = freq.get(key, 0) + 1
    # Sort by frequency desc then length desc then lexicographically for stability
    ranked = sorted(freq.items(), key=lambda kv: (-kv[1], -len(kv[0]), kv[0]))
    return [k for k, _ in ranked[:limit]]


def _summarize(text: str, limit: int = 64) -> str:
    s = re.sub(r"\s+", " ", text).strip()
    if len(s) <= limit:
        return s
    return s[: limit - 1] + "…"


def build_deck_from_text(text: str) -> dict[str, Any]:
    """
    Demo-only deck builder (Agent A placeholder).
    Produces a Deck JSON matching frontend/src/types.ts
    """
    text = _normalize_text(text)
    if not text:
        raise ValueError("文字內容為空，請貼上內容或上傳 .txt/.md 檔案。")

    blocks = _split_markdown_blocks(text)
    if not blocks:
        raise ValueError("文字內容為空或無法解析為段落。")

    paragraphs: list[dict[str, Any]] = []
    topics: list[dict[str, Any]] = []
    cards: list[dict[str, Any]] = []

    # Topic detection: markdown headings start new topic.
    current_topic_title = "內容"
    current_topic_member_pids: list[str] = []
    topic_seq = 0
    para_seq = 0

    def finalize_topic() -> None:
        nonlocal topic_seq, current_topic_title, current_topic_member_pids
        if not current_topic_member_pids:
            return
        topic_seq += 1
        tid = f"t{topic_seq}"
        topics.append({"id": tid, "title": current_topic_title, "memberIds": current_topic_member_pids})
        # Build one card per topic using member paragraph summaries.
        bullet_texts: list[str] = []
        for pid in current_topic_member_pids:
            p = next((x for x in paragraphs if x["id"] == pid), None)
            if not p:
                continue
            bullet_texts.append(p["summary"])
            if len(bullet_texts) >= 5:
                break
        if not bullet_texts:
            bullet_texts = ["（此主題沒有可用的摘要）"]
        cards.append(
            {
                "id": f"c{topic_seq}",
                "topicId": tid,
                "title": current_topic_title or "未命名主題",
                "bullets": bullet_texts[:5],
            }
        )
        current_topic_member_pids = []

    for b in blocks:
        heading = re.match(r"^\s{0,3}(#{1,6})\s+(.+)$", b)
        if heading:
            # finalize previous topic before starting new one
            finalize_topic()
            current_topic_title = heading.group(2).strip()
            continue

        para_seq += 1
        pid = f"p{para_seq}"
        summary = _summarize(b, limit=80)
        paragraphs.append(
            {
                "id": pid,
                "text": b,
                "summary": summary,
                "keywords": _extract_keywords(b, limit=4),
                "sourceIndex": para_seq - 1,
            }
        )
        current_topic_member_pids.append(pid)

    finalize_topic()

    stats = {
        "paragraphCount": len(paragraphs),
        "topicCount": len(topics),
        "cardCount": len(cards),
    }

    return {"paragraphs": paragraphs, "topics": topics, "cards": cards, "stats": stats}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            _json_response(self, 200, {"ok": True})
            return
        _json_response(self, 404, {"error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/process":
            _json_response(self, 404, {"error": "Not found"})
            return
        try:
            payload = _read_json(self)
            text = payload.get("text")
            if not isinstance(text, str):
                raise ValueError("缺少必要欄位 text（string）。")
            # Simulate a little processing time for demo UX (kept short).
            time.sleep(0.2)
            deck = build_deck_from_text(text)
            _json_response(self, 200, deck)
        except ValueError as exc:
            _json_response(self, 400, {"error": str(exc)})
        except Exception:
            _json_response(self, 500, {"error": "伺服器發生未預期錯誤。"})

    def log_message(self, fmt: str, *args: Any) -> None:
        # Keep console output minimal in demo.
        return


def main() -> None:
    host = "0.0.0.0"
    port = 8000
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Backend API listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()

from __future__ import annotations

from typing import Any, Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend.agent_a import AgentAError, generate_deck, validate_deck


MAX_UPLOAD_BYTES = 5_000_000
Language = Literal["zh", "en", "auto"]


def _decode_uploaded_text(data: bytes) -> str:
    if not data:
        raise HTTPException(status_code=400, detail="上傳檔案是空的，無法產生卡片。")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"上傳檔案過大（{len(data)} bytes），上限為 {MAX_UPLOAD_BYTES} bytes。",
        )
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as e:
        raise HTTPException(status_code=400, detail="檔案不是 UTF-8 編碼，請轉成 UTF-8 後再試。") from e


app = FastAPI(title="Learn2Cards API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True}


@app.post("/api/generate")
async def generate(
    file: UploadFile = File(...),
    max_topics: int = 5,
    topic_threshold: float = 0.75,
    bullets_per_card: int = 5,
    embedding_dim: int = 256,
    language: Language = "auto",
) -> dict[str, Any]:
    """
    上傳 Markdown/純文字 → 後端分析 → 回傳 deck JSON（前端可直接渲染卡片）。
    """
    try:
        data = await file.read()
        text = _decode_uploaded_text(data)

        deck = generate_deck(
            text,
            source=file.filename or "upload",
            language=language,
            topic_threshold=float(topic_threshold),
            max_topics=int(max_topics),
            bullets_per_card=int(bullets_per_card),
            embedding_dim=int(embedding_dim),
            verbose=False,
        )

        errors = validate_deck(deck)
        if errors:
            # 理論上不應發生；若發生代表後端產生器有 bug
            raise HTTPException(
                status_code=500,
                detail={"message": "後端已產生 deck，但 validate 失敗。", "errors": errors},
            )

        return deck

    except AgentAError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

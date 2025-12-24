from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from pipeline import ProcessingError, build_deck, write_deck_json


REPO_ROOT = Path(__file__).resolve().parents[1]


class ParagraphModel(BaseModel):
    id: str
    text: str
    summary: str
    keywords: list[str]
    sourceIndex: int


class TopicModel(BaseModel):
    id: str
    title: str
    memberIds: list[str]


class CardModel(BaseModel):
    id: str
    topicId: str
    title: str
    bullets: list[str]


class DeckStatsModel(BaseModel):
    paragraphCount: int
    topicCount: int
    cardCount: int


class DeckModel(BaseModel):
    paragraphs: list[ParagraphModel]
    topics: list[TopicModel]
    cards: list[CardModel]
    stats: DeckStatsModel


class ProcessRequest(BaseModel):
    text: str = Field(..., description="輸入的純文字內容（必填）")
    topic_threshold: float = Field(0.75, ge=0.0, le=1.0)
    max_topics: int = Field(5, ge=1)
    max_bullets: int = Field(5, ge=1, le=5)
    debug: bool = False

    @field_validator("text")
    @classmethod
    def _non_empty_text(cls, v: str) -> str:
        if v is None:
            raise ValueError("text 為必填欄位")
        if not v.strip():
            raise ValueError("輸入為空：請提供非空的純文字字串。")
        return v


class ProcessResponse(BaseModel):
    ok: Literal[True]
    deck: DeckModel
    outputPath: str
    stats: DeckStatsModel
    debug: Optional[dict[str, Any]] = None


class ErrorResponse(BaseModel):
    ok: Literal[False]
    error: str


app = FastAPI(title="Learn2Cards Backend (Agent A)", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/api/process",
    response_model=ProcessResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def process(req: ProcessRequest) -> ProcessResponse:
    try:
        deck_dict = build_deck(
            text=req.text,
            topic_threshold=req.topic_threshold,
            max_topics=req.max_topics,
            max_bullets=req.max_bullets,
        )
        out_path = write_deck_json(deck_dict, repo_root=REPO_ROOT)
        deck = DeckModel.model_validate(deck_dict)

        debug: Optional[dict[str, Any]] = None
        if req.debug:
            debug = {
                "repoRoot": str(REPO_ROOT),
                "topicThreshold": req.topic_threshold,
                "maxTopics": req.max_topics,
                "maxBullets": req.max_bullets,
            }

        return ProcessResponse(
            ok=True,
            deck=deck,
            outputPath=str(out_path),
            stats=deck.stats,
            debug=debug,
        )
    except ProcessingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"內部錯誤：{e}")


@app.exception_handler(HTTPException)
def http_exception_handler(_, exc: HTTPException):
    # Normalize FastAPI errors into spec-friendly shape.
    status = exc.status_code
    msg = exc.detail if isinstance(exc.detail, str) else "參數錯誤"
    return fastapi_json(status, {"ok": False, "error": msg})


@app.exception_handler(RequestValidationError)
def request_validation_exception_handler(_, exc: RequestValidationError):
    # FastAPI default is 422; spec expects 400 for parameter validation errors.
    msg = "參數錯誤"
    try:
        errs = exc.errors()
        if errs:
            first = errs[0]
            if isinstance(first, dict):
                # Pydantic v2 "missing" (required field) handling
                if first.get("type") == "missing":
                    loc = first.get("loc")
                    if isinstance(loc, (list, tuple)) and loc and loc[-1] == "text":
                        msg = "text 為必填欄位"
                        return fastapi_json(400, {"ok": False, "error": msg})

                raw_msg = first.get("msg")
                if isinstance(raw_msg, str) and raw_msg:
                    # Normalize "Value error, <message>" into "<message>"
                    prefix = "Value error, "
                    msg = raw_msg[len(prefix) :] if raw_msg.startswith(prefix) else raw_msg
    except Exception:
        pass
    return fastapi_json(400, {"ok": False, "error": msg})


def fastapi_json(status_code: int, body: dict[str, Any]):
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=status_code, content=body)


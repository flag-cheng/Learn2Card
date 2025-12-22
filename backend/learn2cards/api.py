from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .models import Deck, DeckOptions
from .pipeline import generate_deck


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, description="Raw markdown/plain text")
    source: str = Field(default="text", description="Label for meta.source")
    options: DeckOptions | None = None


app = FastAPI(title="Learn2Cards Agent A API", version="0.1.0")

# Demo-friendly CORS (integration phase can tighten this)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_model=Deck)
def analyze(req: AnalyzeRequest) -> Deck:
    deck = generate_deck(req.text, source=req.source, options=req.options)
    return deck


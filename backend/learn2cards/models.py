from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator


SchemaVersion = Literal["1.0.0"]


class Meta(BaseModel):
    source: str = Field(default="text", description="Input filename / URL / label")
    generatedAt: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO8601 timestamp",
    )
    schemaVersion: SchemaVersion = "1.0.0"


class Paragraph(BaseModel):
    id: str
    idx: int = Field(ge=0)
    text: str = Field(min_length=1)
    headingLevel: int | None = Field(default=None, ge=1, le=6)
    sectionPath: list[str] | None = None


class Keypoint(BaseModel):
    paragraphId: str
    sentence: str = Field(min_length=1)
    keywords: list[str] = Field(min_length=1, max_length=5)

    @field_validator("keywords")
    @classmethod
    def _no_empty_keywords(cls, v: list[str]) -> list[str]:
        cleaned = [k.strip() for k in v if k.strip()]
        if not cleaned:
            raise ValueError("keywords must contain at least 1 non-empty item")
        return cleaned[:5]


class Topic(BaseModel):
    id: str
    title: str = Field(min_length=1)
    memberIds: list[str] = Field(min_length=1)
    summaryBullets: list[str] | None = None


class Card(BaseModel):
    id: str
    topicId: str
    title: str = Field(min_length=1)
    bullets: list[str] = Field(min_length=1, max_length=5)

    @field_validator("bullets")
    @classmethod
    def _clean_bullets(cls, v: list[str]) -> list[str]:
        cleaned: list[str] = []
        for b in v:
            s = (b or "").strip()
            if not s:
                continue
            if s not in cleaned:
                cleaned.append(s)
        if not cleaned:
            raise ValueError("bullets must contain at least 1 non-empty item")
        return cleaned[:5]


class Stats(BaseModel):
    totalParagraphs: int = Field(ge=0)
    totalKeypoints: int = Field(ge=0)
    totalTopics: int = Field(ge=0)
    totalCards: int = Field(ge=0)


class Deck(BaseModel):
    meta: Meta
    paragraphs: list[Paragraph]
    keypoints: list[Keypoint]
    topics: list[Topic]
    cards: list[Card]
    stats: Stats


class DeckOptions(BaseModel):
    # Core clustering/card rules (Agent A PRD / Technical Spec defaults)
    maxTopics: int = Field(default=5, ge=1, le=50)
    topicThreshold: float = Field(default=0.75, ge=0.0, le=1.0)
    maxBulletsPerCard: int = Field(default=5, ge=1, le=5)
    targetMinBullets: int = Field(default=3, ge=1, le=5)

    # LLM-ish knobs (kept for interface compatibility; heuristic impl uses them deterministically)
    language: Literal["zh", "en", "auto"] = "auto"
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    seed: int | None = None

    # Embedding knobs
    embeddingDim: int = Field(default=256, ge=32, le=4096)

    # Debug
    verbose: bool = False


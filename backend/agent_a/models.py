from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, ConfigDict


class Paragraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str = Field(min_length=1)
    headingLevel: int | None = Field(default=None, ge=1, le=6)
    sectionPath: list[str] | None = None
    idx: int = Field(ge=0)


class Keypoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paragraphId: str
    sentence: str = Field(min_length=1)
    keywords: list[str] = Field(default_factory=list, max_length=5)


class Topic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str = Field(min_length=1)
    memberIds: list[str] = Field(default_factory=list)
    summaryBullets: list[str] = Field(default_factory=list, max_length=5)


class Card(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    topicId: str
    title: str = Field(min_length=1)
    bullets: list[str] = Field(min_length=1, max_length=5)


class Stats(BaseModel):
    model_config = ConfigDict(extra="forbid")

    totalParagraphs: int = Field(ge=0)
    totalKeypoints: int = Field(ge=0)
    totalTopics: int = Field(ge=0)
    totalCards: int = Field(ge=0)


class AgentAOutput(BaseModel):
    """Stable output schema required by docs/prd/agent-a.md."""

    model_config = ConfigDict(extra="forbid")

    paragraphs: list[Paragraph]
    keypoints: list[Keypoint]
    topics: list[Topic]
    cards: list[Card]
    stats: Stats


class PipelineOptions(BaseModel):
    """Configurable knobs; some are placeholders for LLM swap-in."""

    model_config = ConfigDict(extra="forbid")

    language: str = "zh-TW"

    topicThreshold: float = Field(default=0.75, ge=0.0, le=1.0)
    maxTopics: int = Field(default=5, ge=1)

    # Bullet constraints: each card 1-5, target 3-5 (heuristic target used).
    maxBulletsPerCard: int = Field(default=5, ge=1, le=5)
    targetBulletsPerCard: int = Field(default=4, ge=1, le=5)
    maxSummaryBulletsPerTopic: int = Field(default=5, ge=1, le=5)

    # Embedding controls
    embeddingModel: Literal["hashing_v1"] = "hashing_v1"
    embeddingDimension: int = Field(default=384, ge=8, le=8192)
    embeddingBatchSize: int = Field(default=64, ge=1, le=4096)

    # Safety limits
    maxChars: int = Field(default=200_000, ge=1)

    # LLM-ish params (not used by the default heuristic implementation)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    seed: int | None = None
    max_tokens: int | None = Field(default=None, ge=1)

    deterministic: bool = True

    def to_debug_dict(self) -> dict[str, Any]:
        return self.model_dump()


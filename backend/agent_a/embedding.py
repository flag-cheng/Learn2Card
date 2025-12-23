from __future__ import annotations

import hashlib
import math
from collections.abc import Iterable

import numpy as np

from .models import Paragraph, PipelineOptions
from .text_utils import extract_cjk_keywords, extract_latin_keywords, is_cjk_heavy


class EmbeddingError(RuntimeError):
    pass


def _hash_to_index_and_sign(token: str, dim: int) -> tuple[int, float]:
    # Deterministic across runs and machines.
    h = hashlib.sha256(token.encode("utf-8")).digest()
    idx = int.from_bytes(h[:8], "big") % dim
    sign = -1.0 if (h[8] & 1) else 1.0
    return idx, sign


def _tokens_for_embedding(text: str, *, language: str) -> list[str]:
    if is_cjk_heavy(language, text):
        toks = extract_cjk_keywords(text, max_keywords=50)
        return toks if toks else [c for c in text if "\u4e00" <= c <= "\u9fff"][:50]
    return extract_latin_keywords(text, max_keywords=80)


class HashingEmbedder:
    """A dependency-light, deterministic embedder using feature hashing.

    This is a placeholder for real embedding models; the interface is stable.
    """

    def __init__(self, *, dim: int, batch_size: int, language: str) -> None:
        if dim <= 0:
            raise EmbeddingError("embeddingDimension must be a positive integer.")
        if batch_size <= 0:
            raise EmbeddingError("embeddingBatchSize must be a positive integer.")
        self.dim = dim
        self.batch_size = batch_size
        self.language = language

    def embed_texts(self, texts: Iterable[str]) -> np.ndarray:
        try:
            vectors: list[np.ndarray] = []
            for t in texts:
                v = np.zeros((self.dim,), dtype=np.float32)
                toks = _tokens_for_embedding(t, language=self.language)
                if not toks:
                    vectors.append(v)
                    continue
                for tok in toks:
                    idx, sign = _hash_to_index_and_sign(tok, self.dim)
                    v[idx] += sign
                # L2 normalize for cosine similarity
                norm = float(np.linalg.norm(v))
                if norm > 0:
                    v /= norm
                vectors.append(v)
            return np.stack(vectors, axis=0) if vectors else np.zeros((0, self.dim), dtype=np.float32)
        except Exception as e:  # noqa: BLE001 - wrap into readable error
            raise EmbeddingError(f"Embedding failed: {e}") from e


def build_embedder(options: PipelineOptions) -> HashingEmbedder:
    if options.embeddingModel != "hashing_v1":
        raise EmbeddingError(f"Unsupported embeddingModel: {options.embeddingModel}")
    return HashingEmbedder(
        dim=options.embeddingDimension,
        batch_size=options.embeddingBatchSize,
        language=options.language,
    )


def cosine_similarity_matrix(vectors: np.ndarray) -> np.ndarray:
    """Cosine similarity for already-normalized vectors."""

    if vectors.ndim != 2:
        raise EmbeddingError("Vectors must be a 2D array.")
    if vectors.shape[0] == 0:
        return np.zeros((0, 0), dtype=np.float32)
    # vectors are L2-normalized; dot product equals cosine similarity.
    sim = vectors @ vectors.T
    # Numerical guard
    np.clip(sim, -1.0, 1.0, out=sim)
    return sim.astype(np.float32, copy=False)


def embed_paragraphs(paragraphs: list[Paragraph], options: PipelineOptions) -> np.ndarray:
    embedder = build_embedder(options)
    texts = [p.text for p in paragraphs]
    # batch_size exposed for future real model; no-op for hashing embedder.
    _ = embedder.batch_size
    vecs = embedder.embed_texts(texts)
    if vecs.shape != (len(paragraphs), options.embeddingDimension):
        raise EmbeddingError(
            f"Embedding dimension mismatch: got {vecs.shape}, expected ({len(paragraphs)}, {options.embeddingDimension})"
        )
    # Ensure normalization
    for i in range(vecs.shape[0]):
        norm = float(np.linalg.norm(vecs[i]))
        if norm > 0 and not math.isclose(norm, 1.0, rel_tol=1e-3, abs_tol=1e-3):
            vecs[i] /= norm
    return vecs


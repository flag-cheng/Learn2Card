from __future__ import annotations

from .models import Keypoint, Paragraph, PipelineOptions
from .text_utils import (
    extract_cjk_keywords,
    extract_latin_keywords,
    is_cjk_heavy,
    split_sentences,
)


def extract_keypoints(paragraphs: list[Paragraph], options: PipelineOptions) -> list[Keypoint]:
    """One sentence + 1-5 keywords per paragraph (heuristic, deterministic)."""

    out: list[Keypoint] = []
    for p in paragraphs:
        sentences = split_sentences(p.text, language=options.language)
        sentence = sentences[0] if sentences else p.text.strip()
        sentence = sentence.strip()
        if len(sentence) > 280:
            sentence = sentence[:277].rstrip() + "..."

        if is_cjk_heavy(options.language, p.text):
            keywords = extract_cjk_keywords(p.text, max_keywords=5)
        else:
            keywords = extract_latin_keywords(p.text, max_keywords=5)

        out.append(
            Keypoint(
                paragraphId=p.id,
                sentence=sentence,
                keywords=keywords[:5],
            )
        )
    return out


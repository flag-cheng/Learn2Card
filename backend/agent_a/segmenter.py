from __future__ import annotations

import re

from .models import Paragraph
from .text_utils import normalize_whitespace


_RE_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_RE_UL_ITEM = re.compile(r"^\s*[-*+]\s+(.*\S)\s*$")
_RE_OL_ITEM = re.compile(r"^\s*\d+\.\s+(.*\S)\s*$")
_RE_INDENT_CONT = re.compile(r"^\s{2,}(\S.*)$")


def segment_text(text: str) -> list[Paragraph]:
    """Split markdown/plain text into paragraphs.

    Rules (intentionally dumb & deterministic):
    - Headings (#..######) update section path; they are not output as paragraphs.
    - Blank lines split paragraphs.
    - List items (-/*/+ or 1.) become individual paragraphs; indented lines attach to the previous list item.
    - No short-paragraph merging.
    """

    lines = (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")

    paragraphs: list[Paragraph] = []
    buf: list[str] = []

    section_stack: list[tuple[int, str]] = []
    current_heading_level: int | None = None

    def current_section_path() -> list[str] | None:
        if not section_stack:
            return None
        return [t for _, t in section_stack]

    def flush_buf() -> None:
        nonlocal buf
        if not buf:
            return
        joined = normalize_whitespace("\n".join(buf))
        buf = []
        if not joined:
            return
        idx = len(paragraphs)
        pid = f"p{idx}"
        paragraphs.append(
            Paragraph(
                id=pid,
                text=joined,
                headingLevel=current_heading_level,
                sectionPath=current_section_path(),
                idx=idx,
            )
        )

    for line in lines:
        m_h = _RE_HEADING.match(line)
        if m_h:
            flush_buf()
            hashes, title = m_h.group(1), m_h.group(2).strip()
            level = len(hashes)
            # pop to parent
            while section_stack and section_stack[-1][0] >= level:
                section_stack.pop()
            section_stack.append((level, title))
            current_heading_level = level
            continue

        if not line.strip():
            flush_buf()
            continue

        m_ul = _RE_UL_ITEM.match(line)
        m_ol = _RE_OL_ITEM.match(line)
        if m_ul or m_ol:
            flush_buf()
            item = (m_ul or m_ol).group(1).strip()
            buf = [item]
            continue

        m_cont = _RE_INDENT_CONT.match(line)
        if m_cont and buf:
            buf.append(m_cont.group(1).strip())
            continue

        buf.append(line.strip())

    flush_buf()
    return paragraphs


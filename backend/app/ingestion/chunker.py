from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Legal section heading patterns, ordered from most specific to least.
# These are used to split documents at natural structural boundaries.
_SECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^(ARTICLE\s+[IVXLCDM\d]+[\.\s])", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^(SECTION\s+\d+[\.\d]*[\.\s])", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^(\d+\.\s+[A-Z][A-Za-z\s]{3,})", re.MULTILINE),  # e.g. "1. Definitions"
    re.compile(r"^(\d+\.\d+[\.\d]*\s+[A-Z])", re.MULTILINE),  # e.g. "1.1 Term"
    re.compile(r"^(WHEREAS|NOW,\s+THEREFORE|IN WITNESS WHEREOF)", re.MULTILINE),
    re.compile(
        r"^(SCHEDULE\s+[A-Z\d]+|EXHIBIT\s+[A-Z\d]+|APPENDIX\s+[A-Z\d]+)",
        re.IGNORECASE | re.MULTILINE,
    ),
]


@dataclass
class Chunk:
    """A single text chunk ready for embedding and storage."""

    text: str
    chunk_index: int  # Position of this chunk within the document
    page_number: int  # 1-based page number (approximated for DOCX)
    section_title: str  # Nearest parent section heading, if found
    char_start: int  # Character offset in the full document text
    char_end: int


class LegalChunker:
    """Legal-aware text chunker.

    Strategy:
    1. Split the document at legal structural boundaries (articles, sections,
       numbered clauses, schedules) to keep related content together.
    2. If a section is still too large, split it further by sentences while
       respecting the max_chunk_size limit and adding overlap.
    3. Attach the nearest section heading to every chunk for context.
    """

    def __init__(
        self,
        max_chunk_size: int = 512,
        chunk_overlap: int = 50,
    ) -> None:
        """Initialise the chunker.

        Args:
            max_chunk_size: Maximum number of tokens (words) per chunk.
            chunk_overlap:  Number of words to repeat at the start of each
                            successive chunk so context is not lost at boundaries.
        """
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_pages(self, pages: list[str]) -> list[Chunk]:
        """Chunk a full document given its per-page text.

        Args:
            pages: List of page texts (index = page_number - 1).

        Returns:
            Ordered list of Chunk objects.
        """
        # Combine all pages into one string, keeping track of page boundaries.
        full_text, page_offsets = _combine_pages(pages)

        # Split on legal section markers first.
        sections = _split_into_sections(full_text)

        chunks: list[Chunk] = []
        chunk_index = 0

        for section_title, section_text, section_start in sections:
            # Size-split the section if it exceeds max_chunk_size.
            sub_chunks = self._split_section(section_text)

            offset = section_start
            for sub_text in sub_chunks:
                char_start = full_text.find(sub_text, offset)
                if char_start == -1:
                    char_start = offset  # fallback
                char_end = char_start + len(sub_text)
                page_number = _offset_to_page(char_start, page_offsets)

                chunks.append(
                    Chunk(
                        text=sub_text.strip(),
                        chunk_index=chunk_index,
                        page_number=page_number,
                        section_title=section_title,
                        char_start=char_start,
                        char_end=char_end,
                    )
                )
                chunk_index += 1
                offset = char_start + max(1, len(sub_text) - self._overlap_chars())

        logger.debug(f"Document chunked into {len(chunks)} chunks")
        return chunks

    def _split_section(self, text: str) -> list[str]:
        """Split a section's text into word-count-bounded chunks with overlap."""
        words = text.split()
        if len(words) <= self.max_chunk_size:
            return [text]

        result: list[str] = []
        start = 0
        while start < len(words):
            end = min(start + self.max_chunk_size, len(words))
            chunk_words = words[start:end]
            result.append(" ".join(chunk_words))
            # Move forward by (max_chunk_size - overlap), but at least 1 word.
            start += max(1, self.max_chunk_size - self.chunk_overlap)

        return result

    def _overlap_chars(self) -> int:
        """Approximate character count for the overlap window."""
        # Assume average English word ≈ 5 chars + 1 space
        return self.chunk_overlap * 6


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _combine_pages(pages: list[str]) -> tuple[str, list[int]]:
    """Join pages into a single string and record the character offset of each page.

    Args:
        pages: Per-page text list.

    Returns:
        (full_text, page_offsets) where page_offsets[i] is the char index
        at which page i+1 starts.
    """
    parts: list[str] = []
    offsets: list[int] = []
    cursor = 0
    for page_text in pages:
        offsets.append(cursor)
        parts.append(page_text)
        cursor += len(page_text) + 1  # +1 for the newline separator

    return "\n".join(parts), offsets


def _offset_to_page(char_offset: int, page_offsets: list[int]) -> int:
    """Convert a character offset to a 1-based page number.

    Args:
        char_offset:  Absolute character position in the full text.
        page_offsets: Start offsets for each page (from _combine_pages).

    Returns:
        1-based page number.
    """
    page = 1
    for i, start in enumerate(page_offsets):
        if char_offset >= start:
            page = i + 1
        else:
            break
    return page


def _split_into_sections(
    text: str,
) -> list[tuple[str, str, int]]:
    """Split document text at legal structural boundaries.

    Args:
        text: Full document text.

    Returns:
        List of (section_title, section_text, start_offset) tuples.
    """
    # Find all section-header positions across all patterns.
    split_points: list[tuple[int, str]] = []

    for pattern in _SECTION_PATTERNS:
        for match in pattern.finditer(text):
            split_points.append((match.start(), match.group(0).strip()))

    if not split_points:
        # No legal structure found — treat the whole document as one section.
        return [("", text, 0)]

    # Sort by position and deduplicate overlapping matches.
    split_points.sort(key=lambda x: x[0])
    deduplicated: list[tuple[int, str]] = []
    last_pos = -1
    for pos, title in split_points:
        if pos > last_pos + 10:  # ignore matches within 10 chars of each other
            deduplicated.append((pos, title))
            last_pos = pos

    sections: list[tuple[str, str, int]] = []

    # Text before the first heading is a preamble section.
    first_pos = deduplicated[0][0]
    if first_pos > 0:
        preamble = text[:first_pos].strip()
        if preamble:
            sections.append(("Preamble", preamble, 0))

    for i, (pos, title) in enumerate(deduplicated):
        next_pos = deduplicated[i + 1][0] if i + 1 < len(deduplicated) else len(text)
        section_text = text[pos:next_pos].strip()
        if section_text:
            sections.append((title, section_text, pos))

    return sections

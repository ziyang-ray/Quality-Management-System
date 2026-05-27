"""Chunk parsed compliance documents while preserving source traceability."""

import hashlib
import re

from open_deep_research.compliance.schemas import DocumentChunk, ParsedDocumentElement


DEFAULT_MAX_CHARS = 1800
DEFAULT_OVERLAP = 200


def chunk_elements(
    elements: list[ParsedDocumentElement],
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap: int = DEFAULT_OVERLAP,
) -> list[DocumentChunk]:
    """Split parsed elements into searchable chunks."""

    chunks: list[DocumentChunk] = []
    for element in elements:
        for chunk_index, text in enumerate(_split_text(element.text, max_chars, overlap)):
            if not text.strip():
                continue
            chunk_id = _chunk_id(element, chunk_index, text)
            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    source_type=element.source_type,
                    path=element.path,
                    file_name=element.file_name,
                    extension=element.extension,
                    text=text,
                    page_number=element.page_number,
                    sheet_name=element.sheet_name,
                    row_range=element.row_range,
                    section_hint=_section_hint(text),
                    metadata=element.metadata,
                )
            )
    return chunks


def _split_text(text: str, max_chars: int, overlap: int) -> list[str]:
    normalized = re.sub(r"\n{3,}", "\n\n", text.strip())
    if len(normalized) <= max_chars:
        return [normalized]

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", normalized) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            chunks.extend(_split_long_text(paragraph, max_chars, overlap))
            continue
        proposed = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(proposed) <= max_chars:
            current = proposed
            continue
        chunks.append(current.strip())
        current = _tail(current, overlap)
        current = f"{current}\n\n{paragraph}".strip() if current else paragraph
    if current:
        chunks.append(current.strip())
    return chunks


def _split_long_text(text: str, max_chars: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def _tail(text: str, max_chars: int) -> str:
    return text[-max_chars:].strip() if max_chars > 0 else ""


def _chunk_id(element: ParsedDocumentElement, chunk_index: int, text: str) -> str:
    digest_input = "|".join(
        [
            element.path,
            str(element.page_number or ""),
            element.sheet_name or "",
            element.row_range or "",
            str(chunk_index),
            text[:200],
        ]
    )
    return hashlib.sha256(digest_input.encode("utf-8")).hexdigest()[:24]


def _section_hint(text: str) -> str | None:
    for line in text.splitlines()[:8]:
        cleaned = line.strip()
        if re.match(r"^(\d+(\.\d+)*|[A-Z]\d+|[一二三四五六七八九十]+[、.])\s+", cleaned):
            return cleaned[:160]
    return None


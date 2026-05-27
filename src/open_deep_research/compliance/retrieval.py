"""Local retrieval over the compliance JSONL index."""

import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from open_deep_research.compliance.index_store import read_chunks
from open_deep_research.compliance.schemas import DocumentChunk, EvidenceItem, SourceType


class ComplianceRetriever:
    """Small local BM25-style retriever for compliance chunks."""

    def __init__(self, chunks: list[DocumentChunk]):
        self.chunks = chunks
        self._tokens = [_tokenize(chunk.text) for chunk in chunks]
        self._doc_freq: Counter[str] = Counter()
        self._term_freqs: list[Counter[str]] = []
        self._avg_len = 0.0
        self._prepare()

    @classmethod
    def from_index_dir(cls, index_dir: str | Path) -> "ComplianceRetriever":
        return cls(read_chunks(index_dir))

    def search(
        self,
        query: str,
        source_type: SourceType | None = None,
        top_k: int = 8,
        file_name_contains: str | None = None,
        preferred_terms: list[str] | None = None,
    ) -> list[EvidenceItem]:
        """Search indexed chunks and return traceable excerpts."""

        query_tokens = _tokenize(query)
        if not query_tokens or not self.chunks:
            return []

        scored: list[tuple[float, DocumentChunk]] = []
        for index, chunk in enumerate(self.chunks):
            if source_type and chunk.source_type != source_type:
                continue
            if file_name_contains and file_name_contains.lower() not in chunk.file_name.lower():
                continue
            score = self._score(query_tokens, index)
            score += _metadata_boost(chunk, preferred_terms or [])
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [_to_evidence(chunk, score, query) for score, chunk in scored[:top_k]]

    def _prepare(self) -> None:
        total_len = 0
        for tokens in self._tokens:
            term_freq = Counter(tokens)
            self._term_freqs.append(term_freq)
            total_len += len(tokens)
            for token in term_freq:
                self._doc_freq[token] += 1
        self._avg_len = total_len / len(self._tokens) if self._tokens else 0.0

    def _score(self, query_tokens: list[str], chunk_index: int) -> float:
        term_freq = self._term_freqs[chunk_index]
        doc_len = sum(term_freq.values()) or 1
        total_docs = len(self.chunks) or 1
        k1 = 1.5
        b = 0.75
        score = 0.0
        for token in query_tokens:
            freq = term_freq.get(token, 0)
            if freq == 0:
                continue
            doc_freq = self._doc_freq.get(token, 0)
            idf = math.log(1 + (total_docs - doc_freq + 0.5) / (doc_freq + 0.5))
            denom = freq + k1 * (1 - b + b * doc_len / (self._avg_len or 1))
            score += idf * (freq * (k1 + 1)) / denom
        return score


def _tokenize(text: str) -> list[str]:
    lowered = text.lower()
    latin_tokens = re.findall(r"[a-z0-9][a-z0-9_\-./]{1,}", lowered)
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", lowered)
    cjk_bigrams = [a + b for a, b in zip(cjk_chars, cjk_chars[1:])]
    return latin_tokens + cjk_chars + cjk_bigrams


def _to_evidence(chunk: DocumentChunk, score: float, query: str) -> EvidenceItem:
    return EvidenceItem(
        file_name=chunk.file_name,
        path=chunk.path,
        excerpt=_excerpt(chunk.text, query),
        source_type=chunk.source_type,
        page_number=chunk.page_number,
        sheet_name=chunk.sheet_name,
        row_range=chunk.row_range,
        score=round(score, 4),
    )


def _metadata_boost(chunk: DocumentChunk, preferred_terms: list[str]) -> float:
    """Boost chunks whose file names or section hints match the intended topic."""

    if not preferred_terms:
        return 0.0
    haystack = f"{chunk.file_name} {chunk.section_hint or ''}".lower()
    boost = 0.0
    for term in preferred_terms:
        normalized = term.lower().strip()
        if normalized and normalized in haystack:
            boost += 25.0
    return boost


def _excerpt(text: str, query: str, max_chars: int = 700) -> str:
    terms = _tokenize(query)
    positions: defaultdict[int, int] = defaultdict(int)
    lowered = text.lower()
    for term in terms:
        position = lowered.find(term.lower())
        if position >= 0:
            positions[position] += 1
    if not positions:
        return text[:max_chars].strip()
    anchor = min(positions)
    start = max(anchor - max_chars // 3, 0)
    end = min(start + max_chars, len(text))
    return text[start:end].strip()

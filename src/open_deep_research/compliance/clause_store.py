"""Clause store for loading and querying extracted standard clauses."""

import math
import re
from collections import Counter
from pathlib import Path

from open_deep_research.compliance.schemas import StandardClause


def _tokenize(text: str) -> list[str]:
    lowered = text.lower()
    latin_tokens = re.findall(r"[a-z0-9][a-z0-9_\-./]{1,}", lowered)
    cjk_chars = re.findall(r"[一-鿿]", lowered)
    cjk_bigrams = [a + b for a, b in zip(cjk_chars, cjk_chars[1:])]
    return latin_tokens + cjk_chars + cjk_bigrams


def _clause_key(standard: str, clause_id: str) -> str:
    return f"{standard}::{clause_id}"


class ClauseStore:
    """In-memory store for standard clauses with indexed lookup and BM25 search."""

    def __init__(self, clauses: list[StandardClause]):
        self._clauses = clauses
        self._by_id: dict[str, StandardClause] = {}
        self._by_standard: dict[str, list[StandardClause]] = {}
        self._tokens: list[list[str]] = []
        self._doc_freq: Counter[str] = Counter()
        self._term_freqs: list[Counter[str]] = []
        self._avg_len = 0.0
        self._build_indexes()

    def _build_indexes(self) -> None:
        total_len = 0
        for clause in self._clauses:
            key = _clause_key(clause.standard, clause.clause_id)
            self._by_id[key] = clause
            self._by_standard.setdefault(clause.standard, []).append(clause)

            tokens = _tokenize(f"{clause.title} {clause.text} {clause.requirement_summary}")
            self._tokens.append(tokens)
            term_freq = Counter(tokens)
            self._term_freqs.append(term_freq)
            total_len += len(tokens)
            for token in term_freq:
                self._doc_freq[token] += 1

        self._avg_len = total_len / len(self._clauses) if self._clauses else 0.0

    @classmethod
    def from_jsonl(cls, path: str | Path) -> "ClauseStore":
        """Load clauses from a JSONL file (one StandardClause per line)."""
        path = Path(path)
        clauses: list[StandardClause] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    clauses.append(StandardClause.model_validate_json(line))
        return cls(clauses)

    def get_clause(self, standard: str, clause_id: str) -> StandardClause | None:
        """Get a single clause by standard name and clause ID."""
        return self._by_id.get(_clause_key(standard, clause_id))

    def get_clauses_by_ids(self, clause_refs: list[tuple[str, str]]) -> list[StandardClause]:
        """Get multiple clauses by (standard, clause_id) pairs."""
        result = []
        for standard, clause_id in clause_refs:
            clause = self.get_clause(standard, clause_id)
            if clause:
                result.append(clause)
        return result

    def get_clauses_by_standard(self, standard: str) -> list[StandardClause]:
        """Get all clauses for a given standard."""
        return list(self._by_standard.get(standard, []))

    def get_clauses_by_prefix(self, clause_id_prefix: str) -> list[StandardClause]:
        """Get clauses whose ID starts with the given prefix (e.g. '4.2' returns 4.2.1, 4.2.2, ...)."""
        prefix = clause_id_prefix.strip().rstrip(".") + "."
        result = []
        for clause in self._clauses:
            if clause.clause_id.startswith(prefix) or clause.clause_id == clause_id_prefix:
                result.append(clause)
        return result

    def get_all(self) -> list[StandardClause]:
        """Return all clauses."""
        return list(self._clauses)

    def search_clauses(self, query: str, top_k: int = 20) -> list[StandardClause]:
        """BM25 search over clause title, text, and requirement_summary."""
        query_tokens = _tokenize(query)
        if not query_tokens or not self._clauses:
            return []

        k1 = 1.5
        b = 0.75
        total_docs = len(self._clauses) or 1

        scored: list[tuple[float, StandardClause]] = []
        for idx, clause in enumerate(self._clauses):
            term_freq = self._term_freqs[idx]
            doc_len = sum(term_freq.values()) or 1
            score = 0.0
            for token in query_tokens:
                freq = term_freq.get(token, 0)
                if freq == 0:
                    continue
                doc_freq = self._doc_freq.get(token, 0)
                idf = math.log(1 + (total_docs - doc_freq + 0.5) / (doc_freq + 0.5))
                denom = freq + k1 * (1 - b + b * doc_len / (self._avg_len or 1))
                score += idf * (freq * (k1 + 1)) / denom
            if score > 0:
                scored.append((score, clause))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [clause for _, clause in scored[:top_k]]

    def __len__(self) -> int:
        return len(self._clauses)

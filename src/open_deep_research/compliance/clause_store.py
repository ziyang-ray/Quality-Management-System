"""Load and query structured standard clause candidates with enhanced filtering and relationships."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from open_deep_research.compliance.schemas import StandardClause


DEFAULT_CLAUSE_FILE = Path("data/standard_clauses/clauses.jsonl")


class ClauseStatus(str, Enum):
    """Status of a standard clause in the review workflow."""

    CANDIDATE = "candidate"
    APPROVED = "approved"
    NEEDS_FIX = "needs_fix"
    IGNORE = "ignore"


@dataclass
class ClauseRelation:
    """A relationship between a clause and related entities."""

    relation_type: str  # requires, applies_to, controlled_by, produces, etc.
    target_id: str
    target_type: str  # expected_evidence, process, procedure, record, etc.
    metadata: dict = field(default_factory=dict)


@dataclass
class ClauseWithRelations:
    """A clause with its relationships and enhanced metadata."""

    clause: StandardClause
    relations: list[ClauseRelation] = field(default_factory=list)
    topic_ids: list[str] = field(default_factory=list)


class ClauseStore:
    """Enhanced JSONL-backed store for extracted standard clauses with filtering and relationships."""

    def __init__(
        self,
        clauses: list[StandardClause],
        relations: list[ClauseRelation] | None = None,
    ):
        self.clauses = clauses
        self._relations = relations or []
        self._by_key: dict[tuple[str, str], StandardClause] = {
            (clause.standard, clause.clause_id): clause for clause in clauses
        }
        self._by_standard: dict[str, list[StandardClause]] = defaultdict(list)
        self._by_status: dict[str, list[StandardClause]] = defaultdict(list)
        self._by_topic: dict[str, list[StandardClause]] = defaultdict(list)

        for clause in clauses:
            self._by_standard[clause.standard].append(clause)
            self._by_status[clause.extraction_status].append(clause)

        self._relations_by_source: dict[tuple[str, str], list[ClauseRelation]] = defaultdict(list)
        for rel in self._relations:
            key = (rel.metadata.get("standard", ""), rel.metadata.get("clause_id", ""))
            self._relations_by_source[key].append(rel)

    @classmethod
    def from_path(cls, path: str | Path | None = None) -> "ClauseStore":
        clause_path = Path(path) if path else DEFAULT_CLAUSE_FILE
        if not clause_path.exists():
            return cls([])

        clauses: list[StandardClause] = []
        with clause_path.open("r", encoding="utf-8") as file:
            for line in file:
                if line.strip():
                    try:
                        clauses.append(StandardClause.model_validate_json(line))
                    except Exception:
                        continue
        return cls(clauses)

    @classmethod
    def from_path_with_relations(
        cls,
        clause_path: str | Path | None = None,
        relations_path: str | Path | None = None,
    ) -> "ClauseStore":
        """Load clauses and optional relations from separate files."""

        store = cls.from_path(clause_path)
        if relations_path:
            rel_path = Path(relations_path)
            if rel_path.exists():
                relations = _load_relations(rel_path)
                store._relations = relations
                store._relations_by_source = defaultdict(list)
                for rel in relations:
                    key = (rel.metadata.get("standard", ""), rel.metadata.get("clause_id", ""))
                    store._relations_by_source[key].append(rel)
        return store

    def get(self, standard: str, clause_id: str) -> StandardClause | None:
        """Get one clause by exact standard and clause ID."""

        return self._by_key.get((standard, clause_id))

    def get_many(self, refs: tuple[tuple[str, str], ...] | list[tuple[str, str]]) -> list[StandardClause]:
        """Get clauses for a list of `(standard, clause_id)` references."""

        clauses: list[StandardClause] = []
        for standard, clause_id in refs:
            clause = self.get(standard, clause_id)
            if clause:
                clauses.append(clause)
        return clauses

    def get_by_status(self, status: ClauseStatus | str) -> list[StandardClause]:
        """Get all clauses with the specified status."""

        status_str = status.value if isinstance(status, ClauseStatus) else status
        return self._by_status.get(status_str, [])

    def get_approved(self) -> list[StandardClause]:
        """Get all approved clauses."""

        return self.get_by_status(ClauseStatus.APPROVED)

    def get_candidates(self) -> list[StandardClause]:
        """Get all candidate clauses awaiting review."""

        return self.get_by_status(ClauseStatus.CANDIDATE)

    def get_by_standard(self, standard: str) -> list[StandardClause]:
        """Get all clauses for a given standard."""

        return self._by_standard.get(standard, [])

    def get_by_topic(self, topic_id: str) -> list[StandardClause]:
        """Get clauses mapped to a specific topic."""

        return self._by_topic.get(topic_id, [])

    def map_topic_to_clauses(self, topic_id: str, clause_refs: list[tuple[str, str]]) -> None:
        """Map a topic to its relevant clause references."""

        for standard, clause_id in clause_refs:
            clause = self.get(standard, clause_id)
            if clause:
                self._by_topic[topic_id].append(clause)

    def get_relations(self, standard: str, clause_id: str) -> list[ClauseRelation]:
        """Get all relations for a specific clause."""

        return self._relations_by_source.get((standard, clause_id), [])

    def get_related_evidence(self, standard: str, clause_id: str) -> list[str]:
        """Get expected evidence IDs related to a clause."""

        relations = self.get_relations(standard, clause_id)
        return [
            rel.target_id
            for rel in relations
            if rel.relation_type == "requires" and rel.target_type == "expected_evidence"
        ]

    def get_related_processes(self, standard: str, clause_id: str) -> list[str]:
        """Get process IDs that a clause applies to."""

        relations = self.get_relations(standard, clause_id)
        return [
            rel.target_id
            for rel in relations
            if rel.relation_type == "applies_to" and rel.target_type == "process"
        ]

    def update_status(self, standard: str, clause_id: str, new_status: ClauseStatus) -> bool:
        """Update the status of a clause. Returns True if successful."""

        clause = self.get(standard, clause_id)
        if not clause:
            return False

        old_status = clause.extraction_status
        clause.extraction_status = new_status.value

        if old_status in self._by_status:
            self._by_status[old_status] = [
                c for c in self._by_status[old_status]
                if not (c.standard == standard and c.clause_id == clause_id)
            ]
        self._by_status[new_status.value].append(clause)
        return True

    def search_clauses(
        self,
        query: str,
        standard: str | None = None,
        status: ClauseStatus | None = None,
        limit: int = 20,
    ) -> list[StandardClause]:
        """Search clauses by query string with optional filters."""

        query_lower = query.lower()
        results: list[StandardClause] = []

        for clause in self.clauses:
            if standard and clause.standard != standard:
                continue
            if status and clause.extraction_status != status.value:
                continue

            searchable_text = " ".join([
                clause.title,
                clause.text,
                clause.requirement_summary,
                " ".join(clause.search_terms),
            ]).lower()

            if query_lower in searchable_text:
                results.append(clause)
                if len(results) >= limit:
                    break

        return results

    def get_statistics(self) -> dict[str, int]:
        """Get statistics about the clause store."""

        stats = {
            "total_clauses": len(self.clauses),
            "total_relations": len(self._relations),
        }

        for status in ClauseStatus:
            stats[f"status_{status.value}"] = len(self._by_status.get(status.value, []))

        for standard in self._by_standard:
            safe_key = standard.replace(":", "_").replace(" ", "_")
            stats[f"standard_{safe_key}"] = len(self._by_standard[standard])

        return stats

    def to_approved_subset(self) -> "ClauseStore":
        """Create a new store containing only approved clauses."""

        approved_clauses = self.get_approved()
        approved_keys = {(c.standard, c.clause_id) for c in approved_clauses}

        approved_relations = [
            rel for rel in self._relations
            if (rel.metadata.get("standard", ""), rel.metadata.get("clause_id", "")) in approved_keys
        ]

        return ClauseStore(approved_clauses, approved_relations)


def _load_relations(path: Path) -> list[ClauseRelation]:
    """Load relations from a JSONL file."""

    import json

    relations: list[ClauseRelation] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    relations.append(ClauseRelation(
                        relation_type=data.get("relation_type", ""),
                        target_id=data.get("target_id", ""),
                        target_type=data.get("target_type", ""),
                        metadata=data.get("metadata", {}),
                    ))
                except Exception:
                    continue
    return relations


def clause_file_for_index(index_dir: str | Path) -> Path:
    """Infer the standard clause file location from a compliance index directory."""

    index_path = Path(index_dir)
    if index_path.name == "compliance_index":
        return index_path.parent / "standard_clauses" / "clauses.jsonl"
    return DEFAULT_CLAUSE_FILE


def relations_file_for_index(index_dir: str | Path) -> Path:
    """Infer the relations file location from a compliance index directory."""

    index_path = Path(index_dir)
    if index_path.name == "compliance_index":
        return index_path.parent / "standard_clauses" / "relations.jsonl"
    return index_path.parent / "standard_clauses" / "relations.jsonl"

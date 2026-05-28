"""Tests for the clause store module."""

import json
from pathlib import Path

import pytest

from open_deep_research.compliance.clause_store import ClauseStore
from open_deep_research.compliance.schemas import StandardClause


@pytest.fixture
def sample_clauses() -> list[StandardClause]:
    """Create sample clauses for testing."""
    return [
        StandardClause(
            standard="ISO 13485:2016",
            clause_id="4.2.4",
            title="文件控制",
            text="组织应控制质量管理体系所要求的文件...",
            requirement_summary="文件控制要求",
            expected_evidence=["文件评审批准", "版本控制"],
            search_terms=["document", "control", "文件", "控制"],
            source_path="ISO13485.pdf",
            page_start=10,
            page_end=12,
        ),
        StandardClause(
            standard="ISO 13485:2016",
            clause_id="4.2.5",
            title="记录控制",
            text="组织应建立并保持记录...",
            requirement_summary="记录控制要求",
            expected_evidence=["记录保存", "检索"],
            search_terms=["record", "记录", "控制"],
            source_path="ISO13485.pdf",
            page_start=12,
            page_end=14,
        ),
        StandardClause(
            standard="ISO 13485:2016",
            clause_id="8.5.2",
            title="纠正措施",
            text="组织应采取措施消除不合格的原因...",
            requirement_summary="纠正措施要求",
            expected_evidence=["根因分析", "纠正措施计划"],
            search_terms=["corrective", "action", "纠正", "措施"],
            source_path="ISO13485.pdf",
            page_start=50,
            page_end=52,
        ),
        StandardClause(
            standard="ISO 14971:2019",
            clause_id="4.1",
            title="风险管理过程",
            text="制造商应建立风险管理过程...",
            requirement_summary="风险管理过程要求",
            expected_evidence=["风险管理计划"],
            search_terms=["risk", "management", "风险", "管理"],
            source_path="ISO14971.pdf",
            page_start=8,
            page_end=10,
        ),
    ]


@pytest.fixture
def clause_jsonl(tmp_path: Path, sample_clauses: list[StandardClause]) -> Path:
    """Create a temporary JSONL file with sample clauses."""
    path = tmp_path / "clauses.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for clause in sample_clauses:
            f.write(clause.model_dump_json() + "\n")
    return path


def test_from_jsonl_loads_all_clauses(clause_jsonl: Path, sample_clauses: list[StandardClause]):
    store = ClauseStore.from_jsonl(clause_jsonl)
    assert len(store) == len(sample_clauses)


def test_get_clause_returns_correct_clause(clause_jsonl: Path):
    store = ClauseStore.from_jsonl(clause_jsonl)
    clause = store.get_clause("ISO 13485:2016", "4.2.4")
    assert clause is not None
    assert clause.title == "文件控制"


def test_get_clause_returns_none_for_missing(clause_jsonl: Path):
    store = ClauseStore.from_jsonl(clause_jsonl)
    assert store.get_clause("ISO 13485:2016", "99.99") is None
    assert store.get_clause("ISO 9999:2020", "4.2.4") is None


def test_get_clauses_by_ids(clause_jsonl: Path):
    store = ClauseStore.from_jsonl(clause_jsonl)
    clauses = store.get_clauses_by_ids([
        ("ISO 13485:2016", "4.2.4"),
        ("ISO 13485:2016", "8.5.2"),
        ("ISO 13485:2016", "99.99"),  # does not exist
    ])
    assert len(clauses) == 2
    assert clauses[0].clause_id == "4.2.4"
    assert clauses[1].clause_id == "8.5.2"


def test_get_clauses_by_standard(clause_jsonl: Path):
    store = ClauseStore.from_jsonl(clause_jsonl)
    iso13485 = store.get_clauses_by_standard("ISO 13485:2016")
    iso14971 = store.get_clauses_by_standard("ISO 14971:2019")
    assert len(iso13485) == 3
    assert len(iso14971) == 1


def test_get_clauses_by_prefix(clause_jsonl: Path):
    store = ClauseStore.from_jsonl(clause_jsonl)
    clauses_42 = store.get_clauses_by_prefix("4.2")
    assert len(clauses_42) == 2
    ids = {c.clause_id for c in clauses_42}
    assert ids == {"4.2.4", "4.2.5"}


def test_get_all(clause_jsonl: Path):
    store = ClauseStore.from_jsonl(clause_jsonl)
    assert len(store.get_all()) == 4


def test_search_clauses_finds_by_text(clause_jsonl: Path):
    store = ClauseStore.from_jsonl(clause_jsonl)
    results = store.search_clauses("纠正措施", top_k=5)
    assert len(results) > 0
    assert results[0].clause_id == "8.5.2"


def test_search_clauses_finds_by_title(clause_jsonl: Path):
    store = ClauseStore.from_jsonl(clause_jsonl)
    results = store.search_clauses("记录控制", top_k=5)
    assert len(results) > 0
    assert results[0].clause_id == "4.2.5"


def test_search_clauses_returns_empty_for_no_match(clause_jsonl: Path):
    store = ClauseStore.from_jsonl(clause_jsonl)
    results = store.search_clauses("xyznonexistent", top_k=5)
    assert len(results) == 0


def test_empty_store():
    store = ClauseStore([])
    assert len(store) == 0
    assert store.get_all() == []
    assert store.search_clauses("test") == []

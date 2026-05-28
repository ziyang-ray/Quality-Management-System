"""Tests for clause-driven review components."""

import json
from pathlib import Path

import pytest

from open_deep_research.compliance.clause_store import ClauseStore
from open_deep_research.compliance.clause_topic_mapping import (
    TOPIC_CLAUSE_MAPPINGS,
    select_clauses_directly,
    select_topics_and_clauses,
)
from open_deep_research.compliance.schemas import StandardClause


@pytest.fixture
def sample_clauses() -> list[StandardClause]:
    """Create sample clauses covering all MVP topic clause_refs."""
    clause_defs = [
        ("ISO 13485:2016", "4.2.4", "文件控制"),
        ("ISO 13485:2016", "4.2.5", "记录控制"),
        ("ISO 13485:2016", "6.2", "人力资源"),
        ("ISO 13485:2016", "7.3.9", "设计和开发变更的控制"),
        ("ISO 13485:2016", "7.3.10", "设计和开发变更"),
        ("ISO 13485:2016", "8.5.2", "纠正措施"),
        ("ISO 13485:2016", "8.5.3", "预防措施"),
        ("ISO 13485:2016", "8.2.4", "内部审核"),
        ("ISO 13485:2016", "8.3", "不合格品控制"),
        ("ISO 13485:2016", "7.4.1", "采购过程"),
        ("ISO 13485:2016", "7.4.2", "采购信息"),
        ("ISO 13485:2016", "7.4.3", "采购产品的验证"),
        ("ISO 13485:2016", "7.1", "产品实现的策划"),
        ("ISO 13485:2016", "8.2.6", "产品的监视和测量"),
        ("ISO 13485:2016", "7.5.1", "生产和服务提供的控制"),
        ("ISO 14971:2019", "4.1", "风险管理过程"),
        ("ISO 14971:2019", "6", "风险评价"),
        ("ISO 14971:2019", "8", "总体残余风险评价"),
        ("ISO 14971:2019", "9", "风险管理评审"),
    ]
    return [
        StandardClause(
            standard=std,
            clause_id=cid,
            title=title,
            text=f"{title}的详细要求文本...",
            requirement_summary=f"{title}的要求摘要",
            expected_evidence=[f"{title}的期望证据"],
            search_terms=[title],
            source_path="test.pdf",
        )
        for std, cid, title in clause_defs
    ]


@pytest.fixture
def clause_store(tmp_path: Path, sample_clauses: list[StandardClause]) -> ClauseStore:
    """Create a clause store from sample clauses."""
    path = tmp_path / "clauses.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for clause in sample_clauses:
            f.write(clause.model_dump_json() + "\n")
    return ClauseStore.from_jsonl(path)


def test_all_topic_mappings_have_valid_clause_refs(clause_store: ClauseStore):
    """All clause_refs in TOPIC_CLAUSE_MAPPINGS should exist in the store."""
    for mapping in TOPIC_CLAUSE_MAPPINGS:
        for standard, clause_id in mapping.clause_refs:
            clause = clause_store.get_clause(standard, clause_id)
            assert clause is not None, (
                f"Topic '{mapping.topic_id}' references {standard} {clause_id}, "
                f"but it was not found in the clause store"
            )


def test_select_topics_and_clauses_broad_request(clause_store: ClauseStore):
    """Broad requests like '模拟审核' should return all topics."""
    mappings = select_topics_and_clauses("请进行ISO 13485模拟审核", clause_store)
    assert len(mappings) == len(TOPIC_CLAUSE_MAPPINGS)


def test_select_topics_and_clauses_specific_request(clause_store: ClauseStore):
    """Specific requests should return matching topics."""
    mappings = select_topics_and_clauses("请审查CAPA和内部审核", clause_store)
    topic_ids = {m.topic_id for m in mappings}
    assert "capa" in topic_ids
    assert "internal_audit" in topic_ids


def test_select_topics_and_clauses_validates_clause_existence(tmp_path: Path):
    """Topics with missing clauses should be filtered out."""
    # Create a store with only one clause
    clause = StandardClause(
        standard="ISO 13485:2016",
        clause_id="4.2.4",
        title="文件控制",
        text="...",
        search_terms=["文件"],
        source_path="test.pdf",
    )
    path = tmp_path / "clauses.jsonl"
    path.write_text(clause.model_dump_json() + "\n", encoding="utf-8")
    store = ClauseStore.from_jsonl(path)

    mappings = select_topics_and_clauses("ISO 13485模拟审核", store)
    topic_ids = {m.topic_id for m in mappings}
    # Only document_control should survive (4.2.4 exists)
    assert "document_control" in topic_ids
    # CAPA should be filtered out (8.5.2, 8.5.3 don't exist)
    assert "capa" not in topic_ids


def test_select_clauses_directly_finds_ids(clause_store: ClauseStore):
    """Direct clause ID matching from request text."""
    clauses = select_clauses_directly("请审查4.2.4和8.5.2条款", clause_store)
    ids = {c.clause_id for c in clauses}
    assert "4.2.4" in ids
    assert "8.5.2" in ids


def test_select_clauses_directly_returns_empty_for_no_ids(clause_store: ClauseStore):
    """No clause IDs in text should return empty."""
    clauses = select_clauses_directly("请进行完整审核", clause_store)
    assert len(clauses) == 0


def test_select_clauses_directly_deduplicates(clause_store: ClauseStore):
    """Duplicate clause IDs should be deduplicated."""
    clauses = select_clauses_directly("审查4.2.4和4.2.4", clause_store)
    ids = [c.clause_id for c in clauses]
    assert ids.count("4.2.4") == 1

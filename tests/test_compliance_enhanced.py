"""Tests for enhanced compliance components: clause store, knowledge graph, skills, memory, and planner."""

import sys
from pathlib import Path
from typing import List, Optional, Dict, Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from open_deep_research.compliance.clause_store import ClauseStore, ClauseStatus
from open_deep_research.compliance.knowledge_graph import ComplianceKnowledgeGraph, build_initial_compliance_graph
from open_deep_research.compliance.schemas import (
    ClauseRelation,
    EvidenceSearchPlan,
    HumanFeedback,
    KnowledgeEdge,
    KnowledgeNode,
    ReviewFinding,
    ReviewRun,
    SkillPack,
    SkillStatus,
    StandardClause,
)
from open_deep_research.compliance.skill_loader import SkillLoader, save_skill_to_yaml, create_capa_skill
from open_deep_research.compliance.review_memory import ReviewMemory
from open_deep_research.compliance.evidence_planner import EvidencePlanner
from open_deep_research.compliance.review_topics import (
    get_topic_by_id,
    get_topic_by_alias,
    get_all_topics,
    get_topics_by_standard,
    select_review_topics,
)


# ============================================================================
# Clause Store Tests
# ============================================================================


def test_clause_store_status_filtering(tmp_path: Path):
    """Test that clause store can filter by status."""

    clause_path = tmp_path / "clauses.jsonl"
    clauses = [
        StandardClause(
            standard="ISO 13485:2016",
            clause_id="4.2.4",
            title="Document control",
            text="Documents shall be controlled.",
            source_path="ISO13485.pdf",
            extraction_status="approved",
        ),
        StandardClause(
            standard="ISO 13485:2016",
            clause_id="4.2.5",
            title="Record control",
            text="Records shall be controlled.",
            source_path="ISO13485.pdf",
            extraction_status="candidate",
        ),
        StandardClause(
            standard="ISO 13485:2016",
            clause_id="8.5.2",
            title="Corrective action",
            text="Corrective action shall be taken.",
            source_path="ISO13485.pdf",
            extraction_status="approved",
        ),
    ]
    clause_path.write_text(
        "\n".join(c.model_dump_json() for c in clauses) + "\n",
        encoding="utf-8",
    )

    store = ClauseStore.from_path(clause_path)

    assert len(store.get_approved()) == 2
    assert len(store.get_candidates()) == 1
    assert len(store.get_by_status(ClauseStatus.APPROVED)) == 2


def test_clause_store_update_status(tmp_path: Path):
    """Test that clause status can be updated."""

    clause_path = tmp_path / "clauses.jsonl"
    clause = StandardClause(
        standard="ISO 13485:2016",
        clause_id="4.2.4",
        title="Document control",
        text="Documents shall be controlled.",
        source_path="ISO13485.pdf",
        extraction_status="candidate",
    )
    clause_path.write_text(clause.model_dump_json() + "\n", encoding="utf-8")

    store = ClauseStore.from_path(clause_path)

    assert len(store.get_candidates()) == 1
    assert len(store.get_approved()) == 0

    success = store.update_status("ISO 13485:2016", "4.2.4", ClauseStatus.APPROVED)

    assert success is True
    assert len(store.get_candidates()) == 0
    assert len(store.get_approved()) == 1


def test_clause_store_search(tmp_path: Path):
    """Test clause search functionality."""

    clause_path = tmp_path / "clauses.jsonl"
    clauses = [
        StandardClause(
            standard="ISO 13485:2016",
            clause_id="4.2.4",
            title="Document control",
            text="Documents shall be controlled.",
            search_terms=["document", "control", "approval"],
            source_path="ISO13485.pdf",
        ),
        StandardClause(
            standard="ISO 13485:2016",
            clause_id="8.5.2",
            title="Corrective action",
            text="Corrective action shall be taken.",
            search_terms=["corrective", "action", "CAPA"],
            source_path="ISO13485.pdf",
        ),
    ]
    clause_path.write_text(
        "\n".join(c.model_dump_json() for c in clauses) + "\n",
        encoding="utf-8",
    )

    store = ClauseStore.from_path(clause_path)

    results = store.search_clauses("document control")
    assert len(results) == 1
    assert results[0].clause_id == "4.2.4"

    results = store.search_clauses("CAPA")
    assert len(results) == 1
    assert results[0].clause_id == "8.5.2"


def test_clause_store_statistics(tmp_path: Path):
    """Test clause store statistics."""

    clause_path = tmp_path / "clauses.jsonl"
    clauses = [
        StandardClause(
            standard="ISO 13485:2016",
            clause_id="4.2.4",
            title="Document control",
            text="Documents shall be controlled.",
            source_path="ISO13485.pdf",
            extraction_status="approved",
        ),
        StandardClause(
            standard="ISO 14971:2019",
            clause_id="4.1",
            title="Risk management",
            text="Risk management process.",
            source_path="ISO14971.pdf",
            extraction_status="candidate",
        ),
    ]
    clause_path.write_text(
        "\n".join(c.model_dump_json() for c in clauses) + "\n",
        encoding="utf-8",
    )

    store = ClauseStore.from_path(clause_path)
    stats = store.get_statistics()

    assert stats["total_clauses"] == 2
    assert stats["status_approved"] == 1
    assert stats["status_candidate"] == 1


# ============================================================================
# Knowledge Graph Tests
# ============================================================================


def test_knowledge_graph_node_operations():
    """Test knowledge graph node operations."""

    graph = ComplianceKnowledgeGraph()

    graph.nodes.append(KnowledgeNode(
        node_id="clause:ISO 13485:2016:4.2.4",
        node_type="clause",
        label="ISO 13485:2016 4.2.4 Document control",
    ))
    graph.nodes.append(KnowledgeNode(
        node_id="process:document_control",
        node_type="process",
        label="Document Control Process",
    ))

    graph.edges.append(KnowledgeEdge(
        source_id="clause:ISO 13485:2016:4.2.4",
        target_id="process:document_control",
        relation_type="applies_to",
    ))

    graph = ComplianceKnowledgeGraph(graph.nodes, graph.edges)

    node = graph.get_node("clause:ISO 13485:2016:4.2.4")
    assert node is not None
    assert node.label == "ISO 13485:2016 4.2.4 Document control"

    related = graph.get_related_nodes("clause:ISO 13485:2016:4.2.4", "applies_to", "outgoing")
    assert len(related) == 1
    assert related[0][0].node_id == "process:document_control"


def test_knowledge_graph_save_load(tmp_path: Path):
    """Test knowledge graph persistence."""

    graph = ComplianceKnowledgeGraph()
    graph.nodes.append(KnowledgeNode(
        node_id="test_node",
        node_type="process",
        label="Test Process",
    ))

    graph.save(tmp_path)

    loaded = ComplianceKnowledgeGraph.from_directory(tmp_path)

    assert len(loaded.nodes) == 1
    assert loaded.nodes[0].node_id == "test_node"


def test_build_initial_compliance_graph():
    """Test building the initial compliance graph."""

    graph = build_initial_compliance_graph()

    assert len(graph.nodes) > 0
    assert len(graph.edges) > 0

    capa_clause = graph.get_node("clause:ISO 13485:2016:8.5.2")
    assert capa_clause is not None

    processes = graph.get_clause_processes("ISO 13485:2016", "8.5.2")
    assert len(processes) > 0


def test_knowledge_graph_evidence_chain():
    """Test getting evidence chain from knowledge graph."""

    graph = build_initial_compliance_graph()

    chain = graph.get_evidence_chain("ISO 13485:2016", "8.5.2")

    assert "processes" in chain
    assert "procedures" in chain
    assert "records" in chain
    assert len(chain["processes"]) > 0


def test_knowledge_graph_statistics():
    """Test knowledge graph statistics."""

    graph = build_initial_compliance_graph()
    stats = graph.get_statistics()

    assert stats["total_nodes"] > 0
    assert stats["total_edges"] > 0
    assert stats["nodes_clause"] > 0
    assert stats["nodes_process"] > 0


# ============================================================================
# Skill Loader Tests
# ============================================================================


def test_skill_loader_loads_from_yaml(tmp_path: Path):
    """Test loading skills from YAML files."""

    skill = create_capa_skill()
    save_skill_to_yaml(skill, tmp_path)

    loader = SkillLoader.from_directory(tmp_path)

    assert len(loader.skills) == 1
    assert loader.skills[0].skill_id == "capa_review"


def test_skill_loader_filters_by_status(tmp_path: Path):
    """Test that skill loader filters by status."""

    skill = create_capa_skill()
    save_skill_to_yaml(skill, tmp_path)

    loader = SkillLoader.from_directory(tmp_path)

    approved = loader.get_approved_skills_for_topic("capa")
    assert len(approved) == 0

    draft = loader.get_draft_skills_for_topic("capa")
    assert len(draft) == 1


def test_skill_loader_approve_skill(tmp_path: Path):
    """Test approving a draft skill."""

    skill = create_capa_skill()
    save_skill_to_yaml(skill, tmp_path)

    loader = SkillLoader.from_directory(tmp_path)

    success = loader.approve_skill("capa_review", "Quality Manager")

    assert success is True
    assert len(loader.get_approved_skills_for_topic("capa")) == 1


def test_skill_loader_merge_insights(tmp_path: Path):
    """Test merging insights from skills."""

    skill = create_capa_skill()
    save_skill_to_yaml(skill, tmp_path)

    loader = SkillLoader.from_directory(tmp_path)
    loader.approve_skill("capa_review", "Quality Manager")

    merged = loader.merge_skill_insights("capa")

    assert len(merged["red_flags"]) > 0
    assert len(merged["review_checklist"]) > 0


def test_skill_loader_statistics(tmp_path: Path):
    """Test skill loader statistics."""

    skill = create_capa_skill()
    save_skill_to_yaml(skill, tmp_path)

    loader = SkillLoader.from_directory(tmp_path)
    stats = loader.get_statistics()

    assert stats["total_skills"] == 1
    assert stats["draft"] == 1
    assert stats["topics_covered"] == 1


# ============================================================================
# Review Memory Tests
# ============================================================================


def test_review_memory_save_and_get_run(tmp_path: Path):
    """Test saving and retrieving review runs."""

    memory = ReviewMemory(tmp_path)

    run = ReviewRun(
        run_id="test-run-1",
        review_request="Review CAPA",
        topics_reviewed=["capa"],
        overall_risk_level="中",
    )

    memory.save_run(run)

    loaded = memory.get_run("test-run-1")

    assert loaded is not None
    assert loaded.review_request == "Review CAPA"
    assert loaded.topics_reviewed == ["capa"]


def test_review_memory_save_feedback(tmp_path: Path):
    """Test saving human feedback."""

    memory = ReviewMemory(tmp_path)

    run = ReviewRun(
        run_id="test-run-1",
        review_request="Review CAPA",
        topics_reviewed=["capa"],
    )
    memory.save_run(run)

    feedback = HumanFeedback(
        run_id="test-run-1",
        finding_id="finding-1",
        action="accept",
        original_status="需澄清",
        comment="Confirmed by QA team",
        approved_by="Quality Manager",
    )

    memory.save_feedback(feedback)

    feedbacks = memory.get_feedback_for_run("test-run-1")

    assert len(feedbacks) == 1
    assert feedbacks[0].action == "accept"


def test_review_memory_action_followup(tmp_path: Path):
    """Test action followup tracking."""

    memory = ReviewMemory(tmp_path)

    followup_id = memory.save_action_followup(
        run_id="test-run-1",
        finding_id="finding-1",
        action_description="Update CAPA procedure",
        responsible_person="QA Team",
        due_date="2026-06-15",
    )

    open_followups = memory.get_open_followups()
    assert len(open_followups) == 1

    memory.close_action_followup(followup_id, closure_evidence="Procedure updated")

    open_followups = memory.get_open_followups()
    assert len(open_followups) == 0


def test_review_memory_statistics(tmp_path: Path):
    """Test memory statistics."""

    memory = ReviewMemory(tmp_path)

    run = ReviewRun(run_id="test-run-1", review_request="Test")
    memory.save_run(run)

    stats = memory.get_statistics()

    assert stats["total_runs"] == 1


# ============================================================================
# Evidence Planner Tests
# ============================================================================


def test_evidence_planner_creates_plan(tmp_path: Path):
    """Test evidence planner creates search plan."""

    clause_path = tmp_path / "clauses.jsonl"
    clause = StandardClause(
        standard="ISO 13485:2016",
        clause_id="8.5.2",
        title="Corrective action",
        text="Corrective action shall be taken.",
        search_terms=["corrective", "action", "CAPA"],
        expected_evidence=["CAPA report", "root cause analysis"],
        source_path="ISO13485.pdf",
    )
    clause_path.write_text(clause.model_dump_json() + "\n", encoding="utf-8")

    planner = EvidencePlanner(
        clause_store=ClauseStore.from_path(clause_path),
    )

    from open_deep_research.compliance.review_topics import get_topic_by_id
    topic = get_topic_by_id("capa")

    plan = planner.plan_evidence_search(topic)

    assert plan.topic_id == "capa"
    assert len(plan.clause_search_terms) > 0


def test_evidence_planner_build_package():
    """Test evidence planner builds evidence package."""

    planner = EvidencePlanner()

    from open_deep_research.compliance.review_topics import get_topic_by_id
    topic = get_topic_by_id("capa")

    package = planner.build_evidence_package(
        topic=topic,
        standard_evidence=[{"file_name": "ISO13485.pdf"}],
        internal_evidence=[{"file_name": "CAPA.docx"}],
        standard_clauses=[{"clause_id": "8.5.2"}],
    )

    assert package["topic_id"] == "capa"
    assert len(package["standard_evidence"]) == 1
    assert len(package["internal_evidence"]) == 1


# ============================================================================
# Review Topics Tests
# ============================================================================


def test_get_topic_by_id():
    """Test getting topic by ID."""

    topic = get_topic_by_id("capa")

    assert topic is not None
    assert topic.topic_id == "capa"
    assert topic.title == "CAPA 与纠正预防措施"


def test_get_topic_by_alias():
    """Test getting topic by alias."""

    topic = get_topic_by_alias("纠正")

    assert topic is not None
    assert topic.topic_id == "capa"


def test_get_all_topics():
    """Test getting all topics."""

    topics = get_all_topics()

    assert len(topics) >= 10


def test_get_topics_by_standard():
    """Test getting topics by standard."""

    topics = get_topics_by_standard("ISO 13485:2016")

    assert len(topics) > 0


def test_select_review_topics_expands_related():
    """Test that topic selection expands to related topics."""

    topics = select_review_topics("Review CAPA")

    topic_ids = {t.topic_id for t in topics}

    assert "capa" in topic_ids
    assert "internal_audit" in topic_ids or "nonconforming_product" in topic_ids

"""Test script to verify all imports work correctly."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

def main():
    print("Testing imports...")

    try:
        from open_deep_research.compliance.schemas import (
            StandardClause,
            ClauseAssessment,
            ComplianceReviewReport,
            EvidencePackage,
            ReviewFinding,
            ReviewRun,
            HumanFeedback,
            KnowledgeNode,
            KnowledgeEdge,
            SkillPack,
            SkillStatus,
            EvidenceSearchPlan,
        )
        print("[OK] schemas.py imports successful")
    except Exception as e:
        print(f"[FAIL] schemas.py import failed: {e}")
        return 1

    try:
        from open_deep_research.compliance.clause_store import ClauseStore, ClauseStatus
        print("[OK] clause_store.py imports successful")
    except Exception as e:
        print(f"[FAIL] clause_store.py import failed: {e}")
        return 1

    try:
        from open_deep_research.compliance.knowledge_graph import ComplianceKnowledgeGraph, build_initial_compliance_graph
        print("[OK] knowledge_graph.py imports successful")
    except Exception as e:
        print(f"[FAIL] knowledge_graph.py import failed: {e}")
        return 1

    try:
        from open_deep_research.compliance.skill_loader import SkillLoader, save_skill_to_yaml, create_capa_skill
        print("[OK] skill_loader.py imports successful")
    except Exception as e:
        print(f"[FAIL] skill_loader.py import failed: {e}")
        return 1

    try:
        from open_deep_research.compliance.review_memory import ReviewMemory
        print("[OK] review_memory.py imports successful")
    except Exception as e:
        print(f"[FAIL] review_memory.py import failed: {e}")
        return 1

    try:
        from open_deep_research.compliance.evidence_planner import EvidencePlanner, create_evidence_planner
        print("[OK] evidence_planner.py imports successful")
    except Exception as e:
        print(f"[FAIL] evidence_planner.py import failed: {e}")
        return 1

    try:
        from open_deep_research.compliance.review_topics import (
            get_topic_by_id,
            get_topic_by_alias,
            get_all_topics,
            get_topics_by_standard,
            select_review_topics,
        )
        print("[OK] review_topics.py imports successful")
    except Exception as e:
        print(f"[FAIL] review_topics.py import failed: {e}")
        return 1

    print("\nTesting basic functionality...")

    try:
        topic = get_topic_by_id("capa")
        assert topic is not None
        assert topic.topic_id == "capa"
        print(f"[OK] get_topic_by_id('capa') = {topic.title}")
    except Exception as e:
        print(f"[FAIL] get_topic_by_id failed: {e}")
        return 1

    try:
        topic = get_topic_by_alias("纠正")
        assert topic is not None
        assert topic.topic_id == "capa"
        print(f"[OK] get_topic_by_alias('纠正') = {topic.title}")
    except Exception as e:
        print(f"[FAIL] get_topic_by_alias failed: {e}")
        return 1

    try:
        topics = get_all_topics()
        assert len(topics) >= 10
        print(f"[OK] get_all_topics() returned {len(topics)} topics")
    except Exception as e:
        print(f"[FAIL] get_all_topics failed: {e}")
        return 1

    try:
        topics = select_review_topics("Review CAPA")
        topic_ids = {t.topic_id for t in topics}
        assert "capa" in topic_ids
        print(f"[OK] select_review_topics('Review CAPA') = {topic_ids}")
    except Exception as e:
        print(f"[FAIL] select_review_topics failed: {e}")
        return 1

    try:
        graph = build_initial_compliance_graph()
        assert len(graph.nodes) > 0
        assert len(graph.edges) > 0
        print(f"[OK] build_initial_compliance_graph() = {len(graph.nodes)} nodes, {len(graph.edges)} edges")
    except Exception as e:
        print(f"[FAIL] build_initial_compliance_graph failed: {e}")
        return 1

    try:
        skill = create_capa_skill()
        assert skill.skill_id == "capa_review"
        assert skill.status == SkillStatus.DRAFT
        print(f"[OK] create_capa_skill() = {skill.skill_id}")
    except Exception as e:
        print(f"[FAIL] create_capa_skill failed: {e}")
        return 1

    print("\nAll tests passed!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

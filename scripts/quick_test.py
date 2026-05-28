"""Quick test script to verify the compliance assistant is working correctly."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

def main():
    print("=" * 50)
    print("  合规助手快速测试")
    print("=" * 50)
    print()

    # Test 1: Import check
    print("[测试 1] 检查模块导入...")
    try:
        from open_deep_research.compliance.schemas import StandardClause, ComplianceReviewReport
        from open_deep_research.compliance.clause_store import ClauseStore
        from open_deep_research.compliance.knowledge_graph import ComplianceKnowledgeGraph
        from open_deep_research.compliance.skill_loader import SkillLoader
        from open_deep_research.compliance.review_memory import ReviewMemory
        from open_deep_research.compliance.evidence_planner import EvidencePlanner
        from open_deep_research.compliance.review_topics import get_topic_by_id, select_review_topics
        print("[OK] 所有模块导入成功")
    except Exception as e:
        print(f"[FAIL] 模块导入失败: {e}")
        return 1
    print()

    # Test 2: Data files check
    print("[测试 2] 检查数据文件...")
    data_files = {
        "条款库": REPO_ROOT / "data" / "standard_clauses" / "clauses.jsonl",
        "证据索引": REPO_ROOT / "data" / "compliance_index" / "chunks.jsonl",
        "知识图谱节点": REPO_ROOT / "data" / "compliance_graph" / "nodes.jsonl",
        "知识图谱边": REPO_ROOT / "data" / "compliance_graph" / "edges.jsonl",
        "CAPA技能": REPO_ROOT / "data" / "skills" / "capa_review.skill.yaml",
        "内审技能": REPO_ROOT / "data" / "skills" / "internal_audit_review.skill.yaml",
    }

    for name, path in data_files.items():
        if path.exists():
            print(f"[OK] {name}: {path.name}")
        else:
            print(f"[MISSING] {name}: {path}")
    print()

    # Test 3: Topic selection
    print("[测试 3] 测试主题选择...")
    try:
        topics = select_review_topics("Review CAPA")
        topic_ids = [t.topic_id for t in topics]
        print(f"[OK] 选择的主题: {', '.join(topic_ids)}")

        capa_topic = get_topic_by_id("capa")
        if capa_topic:
            print(f"[OK] CAPA 主题标题: {capa_topic.title}")
            print(f"[OK] CAPA 标准条款: {', '.join([f'{s} {c}' for s, c in capa_topic.standard_clause_refs])}")
    except Exception as e:
        print(f"[FAIL] 主题选择失败: {e}")
    print()

    # Test 4: Knowledge graph
    print("[测试 4] 测试知识图谱...")
    try:
        graph = ComplianceKnowledgeGraph.from_directory(REPO_ROOT / "data" / "compliance_graph")
        print(f"[OK] 知识图谱加载成功: {len(graph.nodes)} 节点, {len(graph.edges)} 边")

        chain = graph.get_evidence_chain("ISO 13485:2016", "8.5.2")
        print(f"[OK] CAPA 证据链:")
        print(f"     - 流程: {[n.label for n in chain['processes']]}")
        print(f"     - 程序: {[n.label for n in chain['procedures']]}")
        print(f"     - 记录: {[n.label for n in chain['records']]}")
    except Exception as e:
        print(f"[FAIL] 知识图谱测试失败: {e}")
    print()

    # Test 5: Skill loader
    print("[测试 5] 测试技能包...")
    try:
        loader = SkillLoader.from_directory(REPO_ROOT / "data" / "skills")
        print(f"[OK] 技能包加载成功: {len(loader.skills)} 个技能")

        for skill in loader.skills:
            print(f"     - {skill.skill_id}: {skill.status.value} (适用于: {', '.join(skill.applies_to_topics)})")

        merged = loader.merge_skill_insights("capa", include_draft=True)
        print(f"[OK] CAPA 技能洞察:")
        print(f"     - 红旗指标: {len(merged['red_flags'])} 个")
        print(f"     - 检查清单: {len(merged['review_checklist'])} 个")
    except Exception as e:
        print(f"[FAIL] 技能包测试失败: {e}")
    print()

    # Test 6: Evidence planner
    print("[测试 6] 测试证据规划器...")
    try:
        clause_store = ClauseStore.from_path(REPO_ROOT / "data" / "standard_clauses" / "clauses.jsonl")
        graph = ComplianceKnowledgeGraph.from_directory(REPO_ROOT / "data" / "compliance_graph")
        loader = SkillLoader.from_directory(REPO_ROOT / "data" / "skills")

        planner = EvidencePlanner(
            clause_store=clause_store,
            knowledge_graph=graph,
            skill_loader=loader,
        )

        capa_topic = get_topic_by_id("capa")
        plan = planner.plan_evidence_search(capa_topic)

        print(f"[OK] 证据检索计划生成成功:")
        print(f"     - 主题: {plan.topic_id}")
        print(f"     - 基础查询: {plan.base_query[:50]}...")
        print(f"     - 条款搜索词: {len(plan.clause_search_terms)} 个")
        print(f"     - 知识图谱扩展词: {len(plan.kg_expanded_terms)} 个")
        print(f"     - 技能扩展词: {len(plan.skill_expanded_terms)} 个")
        print(f"     - 红旗指标: {len(plan.red_flags_to_check)} 个")
    except Exception as e:
        print(f"[FAIL] 证据规划器测试失败: {e}")
    print()

    # Test 7: Review memory
    print("[测试 7] 测试审查记忆...")
    try:
        memory = ReviewMemory(REPO_ROOT / "data" / "review_memory")
        stats = memory.get_statistics()
        print(f"[OK] 审查记忆系统初始化成功:")
        print(f"     - 历史运行: {stats['total_runs']} 次")
        print(f"     - 人工反馈: {stats['total_feedback']} 条")
        print(f"     - 行动跟踪: {stats['total_followups']} 个")
    except Exception as e:
        print(f"[FAIL] 审查记忆测试失败: {e}")
    print()

    print("=" * 50)
    print("  测试完成！")
    print("=" * 50)
    print()
    print("现在你可以运行以下命令来使用合规助手：")
    print()
    print("1. 预览证据检索：")
    print("   python scripts/preview_compliance_review.py --request 'Please review CAPA' --full")
    print()
    print("2. 生成审查报告：")
    print("   python scripts/run_compliance_review.py --request 'Please review CAPA' --output reports/capa_review.md")
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

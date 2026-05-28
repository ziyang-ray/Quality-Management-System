"""Demo script for advanced features: memory, streaming, and tool calling."""

import os
import sys
import asyncio
import json
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# Set environment variables
API_KEY = "tp-s7egar2qket67uqm1yb7u842lvtp7bmgcjyyticqcojigb1v"
BASE_URL = "https://token-plan-sgp.xiaomimimo.com/v1"

os.environ["OPENAI_API_KEY"] = API_KEY
os.environ["OPENAI_API_BASE"] = BASE_URL
os.environ["OPENAI_BASE_URL"] = BASE_URL
os.environ["PYTHONIOENCODING"] = "utf-8"

from openai import AsyncOpenAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

from open_deep_research.compliance.clause_store import ClauseStore
from open_deep_research.compliance.retrieval import ComplianceRetriever
from open_deep_research.compliance.review_memory import ReviewMemory
from open_deep_research.compliance.knowledge_graph import ComplianceKnowledgeGraph
from open_deep_research.compliance.schemas import ReviewRun, ReviewFinding, HumanFeedback


# ============================================================
# Part 1: Define Tools for Agent
# ============================================================

@tool
def search_clauses(query: str) -> str:
    """Search standard clauses by keyword. Returns matching clauses with their IDs and titles."""
    clause_store = ClauseStore.from_path(REPO_ROOT / "data" / "standard_clauses" / "clauses.jsonl")
    results = clause_store.search_clauses(query, limit=5)
    if not results:
        return f"No clauses found for query: {query}"
    output = []
    for clause in results:
        output.append(f"- {clause.standard} {clause.clause_id}: {clause.title}")
    return "\n".join(output)


@tool
def get_clause_detail(standard: str, clause_id: str) -> str:
    """Get detailed information about a specific clause by standard and clause ID."""
    clause_store = ClauseStore.from_path(REPO_ROOT / "data" / "standard_clauses" / "clauses.jsonl")
    clause = clause_store.get(standard, clause_id)
    if not clause:
        return f"Clause not found: {standard} {clause_id}"
    return f"""Standard: {clause.standard}
Clause ID: {clause.clause_id}
Title: {clause.title}
Requirement Summary: {clause.requirement_summary}
Expected Evidence: {', '.join(clause.expected_evidence)}
Search Terms: {', '.join(clause.search_terms[:5])}"""


@tool
def search_evidence(query: str, source_type: str = "internal") -> str:
    """Search for evidence in the compliance index. source_type can be 'internal' or 'standard'."""
    retriever = ComplianceRetriever.from_index_dir(REPO_ROOT / "data" / "compliance_index")
    results = retriever.search(query, source_type=source_type, top_k=3)
    if not results:
        return f"No {source_type} evidence found for: {query}"
    output = []
    for i, item in enumerate(results, 1):
        excerpt = item.excerpt[:200] + "..." if len(item.excerpt) > 200 else item.excerpt
        output.append(f"[{i}] {item.file_name} (score={item.score:.2f})\n    {excerpt}")
    return "\n\n".join(output)


@tool
def get_evidence_chain(standard: str, clause_id: str) -> str:
    """Get the evidence chain for a clause: processes -> procedures -> records from knowledge graph."""
    graph = ComplianceKnowledgeGraph.from_directory(REPO_ROOT / "data" / "compliance_graph")
    chain = graph.get_evidence_chain(standard, clause_id)
    output = []
    if chain["processes"]:
        output.append("Processes: " + ", ".join(n.label for n in chain["processes"]))
    if chain["procedures"]:
        output.append("Procedures: " + ", ".join(n.label for n in chain["procedures"]))
    if chain["records"]:
        output.append("Records: " + ", ".join(n.label for n in chain["records"]))
    return "\n".join(output) if output else "No evidence chain found"


@tool
def save_review_finding(
    clause_id: str,
    status: str,
    description: str,
    risk_level: str = "medium",
) -> str:
    """Save a review finding to memory. status: 符合/需澄清/缺乏证据/未提及. risk_level: low/medium/high."""
    return f"Finding saved: {clause_id} - {status} - {description[:50]}... (Risk: {risk_level})"


# Define tools list
tools = [search_clauses, get_clause_detail, search_evidence, get_evidence_chain, save_review_finding]


# ============================================================
# Part 2: Streaming Review with Tool Calling
# ============================================================

async def run_streaming_review(clause_id: str = "8.5.2"):
    """Run a streaming review with tool calling."""

    print("=" * 70)
    print("  功能演示：流式输出 + 工具调用")
    print("=" * 70)
    print()

    # Create agent with tools
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)
    model = ChatOpenAI(
        model="mimo-v2.5-pro",
        max_tokens=4000,
        client=client,
    )

    # Bind tools to model
    model_with_tools = model.bind_tools(tools)

    system_prompt = """你是一个专业的合规审查助手。你可以使用以下工具来帮助审查：

1. search_clauses(query) - 搜索标准条款
2. get_clause_detail(standard, clause_id) - 获取条款详情
3. search_evidence(query, source_type) - 检索证据（source_type: internal/standard）
4. get_evidence_chain(standard, clause_id) - 获取证据链
5. save_review_finding(clause_id, status, description, risk_level) - 保存审查发现

请用中文回答。在审查过程中，主动使用工具来获取信息和保存发现。
"""

    user_prompt = f"""请审查 ISO 13485:2016 的 8.5.2 条款（纠正措施）。

审查步骤：
1. 先获取条款详情
2. 检索相关证据
3. 获取证据链
4. 生成审查结论
5. 保存审查发现

请开始审查。
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    print("[流式输出] 正在调用 LLM...")
    print("-" * 70)

    # First call - LLM will decide to use tools
    tool_calls_info = []
    full_response = ""

    async for event in model_with_tools.astream_events(messages, version="v2"):
        kind = event["event"]
        if kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            if content:
                print(content, end="", flush=True)
                full_response += content
        elif kind == "on_tool_start":
            tool_name = event["name"]
            tool_input = event["data"].get("input", {})
            print(f"\n\n[工具调用] {tool_name}")
            print(f"  参数: {json.dumps(tool_input, ensure_ascii=False, indent=2)}")
            tool_calls_info.append({"name": tool_name, "input": tool_input})
        elif kind == "on_tool_end":
            tool_output = event["data"].get("output", "")
            print(f"  结果: {tool_output[:200]}...")
            print()

    print()
    print("-" * 70)
    print("[流式输出完成]")
    print()

    return tool_calls_info


# ============================================================
# Part 3: Memory System Demo
# ============================================================

async def demo_memory_system():
    """Demonstrate the memory system."""

    print("=" * 70)
    print("  功能演示：记忆系统")
    print("=" * 70)
    print()

    memory_dir = REPO_ROOT / "data" / "review_memory"
    memory = ReviewMemory(memory_dir)

    # 1. Save a review run
    print("[1/5] 保存审查运行记录...")

    run = ReviewRun(
        run_id=f"demo-run-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        review_request="审查 ISO 13485:2016 8.5.2 纠正措施",
        topics_reviewed=["capa"],
        findings=[
            ReviewFinding(
                finding_id="finding-001",
                topic_id="capa",
                clause_id="ISO 13485:2016 8.5.2",
                status="需澄清",
                risk_level="高",
                description="条款e)验证纠正措施未对安全和性能产生不利影响的证据缺失",
                evidence_ids=["evidence-001", "evidence-002"],
                recommendation="补充安全与性能影响验证步骤",
            ),
            ReviewFinding(
                finding_id="finding-002",
                topic_id="capa",
                clause_id="ISO 13485:2016 8.5.2",
                status="符合",
                risk_level="低",
                description="CAPA流程框架完整，包含Q-Gate审查机制",
                evidence_ids=["evidence-003"],
            ),
        ],
        overall_risk_level="高",
        created_at=datetime.now().isoformat(),
    )

    memory.save_run(run)
    print(f"  [OK] 保存审查运行: {run.run_id}")
    print(f"    - 发现数量: {len(run.findings)}")
    print(f"    - 总体风险: {run.overall_risk_level}")
    print()

    # 2. Save human feedback
    print("[2/5] 保存人工反馈...")

    feedback = HumanFeedback(
        feedback_id=f"feedback-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        run_id=run.run_id,
        finding_id="finding-001",
        action="accept",
        original_status="需澄清",
        comment="确认需要补充安全验证证据，已安排CAPA",
        approved_by="Quality Manager",
        created_at=datetime.now().isoformat(),
    )

    memory.save_feedback(feedback)
    print(f"  [OK] 保存人工反馈: {feedback.feedback_id}")
    print(f"    - 动作: {feedback.action}")
    print(f"    - 评论: {feedback.comment}")
    print()

    # 3. Save retrieval feedback
    print("[3/5] 保存检索反馈...")

    memory.save_retrieval_feedback(
        topic_id="capa",
        query="CAPA root cause analysis effectiveness",
        helpful_evidence_ids=["evidence-001", "evidence-003"],
        unhelpful_evidence_ids=["evidence-005"],
        comment="SCAR模板对CAPA审查很有帮助",
    )
    print("  [OK] 保存检索反馈")
    print()

    # 4. Save clause override
    print("[4/5] 保存条款覆盖...")

    memory.save_clause_override(
        standard="ISO 13485:2016",
        clause_id="8.5.2",
        original_status="符合",
        corrected_status="需澄清",
        reason="缺少安全验证证据",
        approved_by="Quality Manager",
    )
    print("  [OK] 保存条款覆盖")
    print()

    # 5. Save action followup
    print("[5/5] 保存行动跟踪...")

    followup_id = memory.save_action_followup(
        run_id=run.run_id,
        finding_id="finding-001",
        action_description="修订CAPA程序，增加安全验证步骤",
        responsible_person="Quality Department",
        due_date="2026-06-15",
    )
    print(f"  [OK] 保存行动跟踪: {followup_id}")
    print()

    # Query memory
    print("=" * 70)
    print("  查询记忆系统")
    print("=" * 70)
    print()

    # Get recent runs
    recent_runs = memory.get_recent_runs(limit=5)
    print(f"最近审查运行: {len(recent_runs)} 条")
    for r in recent_runs:
        print(f"  - {r.run_id}: {r.review_request[:30]}... (风险: {r.overall_risk_level})")
    print()

    # Get feedback for run
    feedbacks = memory.get_feedback_for_run(run.run_id)
    print(f"运行 {run.run_id} 的人工反馈: {len(feedbacks)} 条")
    for f in feedbacks:
        print(f"  - {f.action}: {f.comment}")
    print()

    # Get open followups
    open_followups = memory.get_open_followups()
    print(f"未关闭的行动跟踪: {len(open_followups)} 条")
    for f in open_followups:
        print(f"  - {f['action_description']} (责任人: {f['responsible_person']}, 截止: {f['due_date']})")
    print()

    # Get statistics
    stats = memory.get_statistics()
    print("记忆系统统计:")
    for key, value in stats.items():
        print(f"  - {key}: {value}")
    print()

    # Close followup
    print("关闭行动跟踪...")
    memory.close_action_followup(followup_id, closure_evidence="程序已修订，v2.0生效")
    print("  [OK] 已关闭")
    print()

    open_followups = memory.get_open_followups()
    print(f"关闭后未完成跟踪: {len(open_followups)} 条")
    print()


# ============================================================
# Main
# ============================================================

async def main():
    """Run all demos."""

    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "合规助手高级功能演示" + " " * 33 + "║")
    print("╚" + "═" * 68 + "╝")
    print()

    # Demo 1: Memory System
    await demo_memory_system()

    print()
    print("=" * 70)
    print()

    # Demo 2: Streaming + Tool Calling
    await run_streaming_review("8.5.2")

    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 20 + "演示完成！" + " " * 36 + "║")
    print("╚" + "═" * 68 + "╝")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

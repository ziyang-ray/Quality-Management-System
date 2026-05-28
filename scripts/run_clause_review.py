"""Run compliance review by specific clause."""

import os
import sys
import json
from pathlib import Path

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

import asyncio
from langchain_core.messages import HumanMessage
from open_deep_research.compliance.clause_store import ClauseStore
from open_deep_research.compliance.retrieval import ComplianceRetriever
from open_deep_research.compliance.prompts import format_evidence_block, format_clause_block
from open_deep_research.compliance.renderers import render_compliance_review_report
from open_deep_research.compliance.schemas import ComplianceReviewReport

from openai import AsyncOpenAI
from langchain_openai import ChatOpenAI


async def review_single_clause(standard: str, clause_id: str):
    """Review a single standard clause."""

    print("=" * 60)
    print(f"  条款审查: {standard} {clause_id}")
    print("=" * 60)
    print()

    # Load clause
    clause_store = ClauseStore.from_path(REPO_ROOT / "data" / "standard_clauses" / "clauses.jsonl")
    clause = clause_store.get(standard, clause_id)

    if not clause:
        print(f"Error: Clause {standard} {clause_id} not found")
        return

    print(f"条款标题: {clause.title}")
    print(f"要求摘要: {clause.requirement_summary[:100]}...")
    print(f"预期证据: {', '.join(clause.expected_evidence[:3])}...")
    print()

    # Retrieve evidence
    print("正在检索证据...")
    retriever = ComplianceRetriever.from_index_dir(REPO_ROOT / "data" / "compliance_index")

    # Search with clause-specific terms
    search_query = f"{standard} {clause_id} {clause.title} {' '.join(clause.search_terms[:5])}"
    standard_evidence = retriever.search(search_query, source_type="standard", top_k=3)
    internal_evidence = retriever.search(search_query, source_type="internal", top_k=5)

    print(f"  - 官方标准证据: {len(standard_evidence)} 条")
    print(f"  - 内部文件证据: {len(internal_evidence)} 条")
    print()

    # Format evidence for prompt
    clause_block = format_clause_block([clause.model_dump()])
    std_evidence_block = format_evidence_block([e.model_dump() for e in standard_evidence])
    int_evidence_block = format_evidence_block([e.model_dump() for e in internal_evidence])

    prompt = f"""你是一个质量管理体系合规审查助手。请根据以下条款要求和证据，生成符合性审查报告。

## 审查条款
{clause_block}

## 官方标准证据
{std_evidence_block}

## 内部文件证据
{int_evidence_block}

请生成结构化的审查报告，包括：
1. 条款要求摘要
2. 内部证据分析
3. 符合性判断（符合/需澄清/缺乏证据/未提及）
4. 风险评估
5. 改进建议

请用中文回答。
"""

    # Call LLM
    print("正在生成审查报告...")
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)
    model = ChatOpenAI(
        model="mimo-v2.5-pro",
        max_tokens=4000,
        client=client,
    )

    response = await model.ainvoke([HumanMessage(content=prompt)])
    report = response.content

    # Save report
    output_dir = REPO_ROOT / "reports"
    output_dir.mkdir(exist_ok=True)

    safe_clause_id = clause_id.replace(".", "_")
    report_path = output_dir / f"clause_{safe_clause_id}_review.md"
    report_path.write_text(f"# {standard} {clause_id} {clause.title} 审查报告\n\n{report}", encoding="utf-8")

    print()
    print("=" * 60)
    print("  审查报告")
    print("=" * 60)
    print()
    print(report)
    print()
    print("=" * 60)
    print(f"报告已保存到: {report_path}")
    print("=" * 60)


async def main():
    # Review ISO 13485:2016 8.5.2 Corrective Action
    await review_single_clause("ISO 13485:2016", "8.5.2")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

"""Demo script for multi-agent compliance review with streaming."""

import os
import sys
import asyncio
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

from open_deep_research.compliance.clause_store import ClauseStore
from open_deep_research.compliance.retrieval import ComplianceRetriever
from open_deep_research.compliance.prompts import format_evidence_block
from open_deep_research.compliance.compliance_orchestra import (
    REGULATORY_AUDITOR,
    INTERNAL_QMS_AUDITOR,
    RISK_REVIEWER,
    run_agent_review_streaming,
    run_director_review_streaming,
)


async def main():
    """Run multi-agent compliance review demo."""

    print("=" * 70)
    print("  多智能体协作合规审查演示")
    print("=" * 70)
    print()

    # Select clause to review
    standard = "ISO 13485:2016"
    clause_id = "8.5.2"

    print(f"审查条款: {standard} {clause_id}")
    print()

    # Load clause
    clause_store = ClauseStore.from_path(REPO_ROOT / "data" / "standard_clauses" / "clauses.jsonl")
    clause = clause_store.get(standard, clause_id)

    if not clause:
        print(f"Error: Clause {standard} {clause_id} not found")
        return

    print(f"条款标题: {clause.title}")
    print()

    # Retrieve evidence
    print("[步骤 1/4] 检索证据...")
    retriever = ComplianceRetriever.from_index_dir(REPO_ROOT / "data" / "compliance_index")

    search_query = f"{standard} {clause_id} {clause.title} {' '.join(clause.search_terms[:5])}"
    standard_evidence = retriever.search(search_query, source_type="standard", top_k=3)
    internal_evidence = retriever.search(search_query, source_type="internal", top_k=5)

    # Format evidence
    clause_text = f"""标准: {clause.standard}
条款号: {clause.clause_id}
标题: {clause.title}
要求摘要: {clause.requirement_summary}
条款原文: {clause.text[:500]}"""

    evidence = f"""## 官方标准证据
{format_evidence_block([e.model_dump() for e in standard_evidence])}

## 内部文件证据
{format_evidence_block([e.model_dump() for e in internal_evidence])}"""

    print(f"  - 官方标准证据: {len(standard_evidence)} 条")
    print(f"  - 内部文件证据: {len(internal_evidence)} 条")
    print()

    # Define agents
    agents = [
        REGULATORY_AUDITOR,
        INTERNAL_QMS_AUDITOR,
        RISK_REVIEWER,
    ]

    # Run agent reviews with streaming
    print("[步骤 2/4] 运行多智能体审查...")
    print()

    agent_outputs = []
    for agent in agents:
        print(f"  正在运行: {agent.name} ({agent.description})")
        agent_output = None
        async for evt in run_agent_review_streaming(
            role=agent,
            clause_text=clause_text,
            evidence=evidence,
            api_key=API_KEY,
            base_url=BASE_URL,
        ):
            if evt["type"] == "text":
                print(evt["content"], end="", flush=True)
            elif evt["type"] == "complete":
                agent_output = evt["output"]
        print()

        if agent_output:
            agent_outputs.append(agent_output)
            print(f"    - Findings: {len(agent_output.findings)}")
            print(f"    - Risk: {agent_output.risk_assessment[:50]}...")
            print(f"    - Confidence: {agent_output.confidence_level}")
            print()

    # Display individual agent findings
    print("[步骤 3/4] 各智能体发现汇总:")
    print()

    for output in agent_outputs:
        print(f"--- {output.role_name} ---")
        for finding in output.findings:
            status = finding.get('status', '未知')
            area = finding.get('area', '未知')
            desc = finding.get('description', '无描述')
            print(f"  [{status}] {area}: {desc[:80]}...")
        if output.evidence_gaps:
            print(f"  证据缺口: {', '.join(output.evidence_gaps)}")
        print()

    # Run director review with streaming
    print("[步骤 4/4] 审计总监汇总报告...")
    print()

    final_report = ""
    async for evt in run_director_review_streaming(
        clause_text=clause_text,
        agent_outputs=agent_outputs,
        api_key=API_KEY,
        base_url=BASE_URL,
    ):
        if evt["type"] == "text":
            print(evt["content"], end="", flush=True)
            final_report += evt["content"]
        elif evt["type"] == "complete":
            final_report = evt["report"]
    print()

    # Save report
    output_dir = REPO_ROOT / "reports"
    output_dir.mkdir(exist_ok=True)

    report_path = output_dir / "multi_agent_review_8_5_2.md"

    # Build full report
    full_report = f"""# 多智能体协作审查报告
## {standard} {clause_id} {clause.title}

---

## 一、审查概述

本次审查采用多智能体协作模式，由三位专业审核员从不同角度进行审查：

| 角色 | 关注重点 | 信心水平 |
|------|----------|----------|
| {REGULATORY_AUDITOR.name} | {', '.join(REGULATORY_AUDITOR.focus_areas[:2])} | {agent_outputs[0].confidence_level} |
| {INTERNAL_QMS_AUDITOR.name} | {', '.join(INTERNAL_QMS_AUDITOR.focus_areas[:2])} | {agent_outputs[1].confidence_level} |
| {RISK_REVIEWER.name} | {', '.join(RISK_REVIEWER.focus_areas[:2])} | {agent_outputs[2].confidence_level} |

---

## 二、各智能体详细发现

"""

    for output in agent_outputs:
        full_report += f"### {output.role_name}\n\n"
        full_report += "**发现清单：**\n\n"
        full_report += "| 领域 | 状态 | 描述 |\n"
        full_report += "|------|------|------|\n"
        for f in output.findings:
            full_report += f"| {f.get('area', '-')} | {f.get('status', '-')} | {f.get('description', '-')} |\n"
        full_report += f"\n**风险评估：** {output.risk_assessment}\n\n"
        full_report += f"**建议：**\n"
        for rec in output.recommendations:
            full_report += f"- {rec}\n"
        if output.evidence_gaps:
            full_report += f"\n**证据缺口：** {', '.join(output.evidence_gaps)}\n"
        full_report += "\n---\n\n"

    full_report += f"""## 三、审计总监综合报告

{final_report}

---

## 四、报告元数据

- 审查模式: 多智能体协作
- 参与智能体: {len(agent_outputs)} 个
- 审查条款: {standard} {clause_id}
- 生成时间: [自动生成]
"""

    report_path.write_text(full_report, encoding="utf-8")

    print("=" * 70)
    print("  最终报告")
    print("=" * 70)
    print()
    print(final_report[:2000])
    print("...")
    print()
    print("=" * 70)
    print(f"完整报告已保存到: {report_path}")
    print("=" * 70)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

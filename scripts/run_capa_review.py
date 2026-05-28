"""Run CAPA compliance review with proper environment setup."""

import os
import sys
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
os.environ["ANTHROPIC_BASE_URL"] = "https://token-plan-sgp.xiaomimimo.com/anthropic"
os.environ["ANTHROPIC_API_KEY"] = API_KEY
os.environ["ANTHROPIC_AUTH_TOKEN"] = API_KEY
os.environ["PYTHONIOENCODING"] = "utf-8"

# Force reload configuration
from open_deep_research.configuration import Configuration
config = Configuration()
config.final_report_model = "mimo-v2.5-pro"

import asyncio
from langchain_core.messages import HumanMessage
from open_deep_research.compliance_reviewer import compliance_reviewer


async def main():
    print("=" * 60)
    print("  合规助手 - CAPA 审查")
    print("=" * 60)
    print()

    request = "请审查CAPA（纠正预防措施），评估内部文件是否符合ISO 13485:2016的要求"

    print(f"审查请求: {request}")
    print()
    print("正在生成审查报告...")
    print()

    try:
        result = await compliance_reviewer.ainvoke(
            {"messages": [HumanMessage(content=request)]},
            {
                "configurable": {
                    "compliance_index_path": "data/compliance_index",
                    "knowledge_graph_dir": "data/compliance_graph",
                    "skills_dir": "data/skills",
                }
            },
        )

        report = result.get("final_report", "")
        structured_report = result.get("structured_report", {})

        # Save report
        report_path = REPO_ROOT / "reports" / "capa_review.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")

        # Save structured report
        import json
        structured_path = REPO_ROOT / "reports" / "capa_review_structured.json"
        structured_path.write_text(
            json.dumps(structured_report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print("=" * 60)
        print("  审查报告")
        print("=" * 60)
        print()
        print(report)
        print()
        print("=" * 60)
        print(f"报告已保存到: {report_path}")
        print(f"结构化报告已保存到: {structured_path}")
        print("=" * 60)

    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

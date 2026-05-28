"""Run the Compliance Reviewer graph from the command line."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Set environment variables for API
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "tp-s7egar2qket67uqm1yb7u842lvtp7bmgcjyyticqcojigb1v")
os.environ["OPENAI_API_BASE"] = os.environ.get("OPENAI_API_BASE", "https://token-plan-sgp.xiaomimimo.com/v1")
os.environ["OPENAI_BASE_URL"] = os.environ.get("OPENAI_BASE_URL", "https://token-plan-sgp.xiaomimimo.com/v1")

from langchain_core.messages import HumanMessage

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from open_deep_research.compliance_reviewer import compliance_reviewer, run_compliance_review_streaming
from open_deep_research.configuration import Configuration


async def main() -> int:
    config = Configuration()
    parser = argparse.ArgumentParser(description="Run an evidence-driven compliance review.")
    parser.add_argument(
        "--request",
        required=True,
        help="Review request, for example: Please review CAPA, internal audit, and DHR.",
    )
    parser.add_argument("--index-dir", default=config.compliance_index_path)
    parser.add_argument("--model", default=config.final_report_model)
    parser.add_argument("--output", default="", help="Optional markdown output path.")
    parser.add_argument(
        "--artifacts-dir",
        default="",
        help="Optional directory for evidence_package.json, structured_report.json, and report.md.",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Enable streaming output with real-time progress events.",
    )
    args = parser.parse_args()

    configurable = {
        "compliance_index_path": args.index_dir,
        "final_report_model": args.model,
    }

    try:
        if args.stream:
            result = None
            report_content = ""
            async for evt in run_compliance_review_streaming(
                [HumanMessage(content=args.request)],
                configurable,
            ):
                if evt["type"] == "node_start":
                    print(f"\n[Stage] {evt['node']}")
                elif evt["type"] == "progress":
                    print(evt["message"])
                elif evt["type"] == "report_chunk":
                    print(evt["content"], end="", flush=True)
                    report_content += evt["content"]
                elif evt["type"] == "complete":
                    result = evt["result"]
            print()

            if result:
                report = result.get("final_report") or report_content
            else:
                report = report_content
        else:
            result = await compliance_reviewer.ainvoke(
                {"messages": [HumanMessage(content=args.request)]},
                {"configurable": configurable},
            )
            report = result.get("final_report") or result.get("messages", [])[-1].content
    except Exception as exc:
        print("Compliance review failed.")
        print(f"Error: {type(exc).__name__}: {exc}")
        print(
            "\nIf this fails while importing torch/transformers in base Anaconda, run the project from a clean uv environment."
        )
        return 1

    if args.artifacts_dir and result:
        run_dir = _new_run_dir(Path(args.artifacts_dir), args.request)
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "evidence_package.json").write_text(
            json.dumps(result.get("topic_evidence", []), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (run_dir / "structured_report.json").write_text(
            json.dumps(result.get("structured_report", {}), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (run_dir / "report.md").write_text(str(report), encoding="utf-8")
        print(f"Wrote review artifacts to {run_dir.resolve()}")
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(str(report), encoding="utf-8")
        print(f"Wrote report to {output_path.resolve()}")
    elif not args.stream:
        print(report)
    return 0


def _new_run_dir(parent: Path, request: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = "".join(char.lower() if char.isalnum() else "_" for char in request[:48]).strip("_")
    return parent / f"{timestamp}_{slug or 'compliance_review'}"


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

"""Run the Compliance Reviewer graph from the command line."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from langchain_core.messages import HumanMessage

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from open_deep_research.compliance_reviewer import compliance_reviewer
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
    parser.add_argument("--clause-store", default=config.clause_store_path)
    parser.add_argument("--model", default=config.final_report_model)
    parser.add_argument("--output", default="", help="Optional markdown output path.")
    args = parser.parse_args()

    try:
        result = await compliance_reviewer.ainvoke(
            {"messages": [HumanMessage(content=args.request)]},
            {
                "configurable": {
                    "compliance_index_path": args.index_dir,
                    "clause_store_path": args.clause_store,
                    "final_report_model": args.model,
                }
            },
        )
    except Exception as exc:
        print("Compliance review failed.")
        print(f"Error: {type(exc).__name__}: {exc}")
        print(
            "\nIf this fails while importing torch/transformers in base Anaconda, run the project from a clean uv environment."
        )
        return 1

    report = result.get("final_report") or result.get("messages", [])[-1].content
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(str(report), encoding="utf-8")
        print(f"Wrote report to {output_path.resolve()}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))


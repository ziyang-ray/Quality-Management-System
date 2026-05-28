"""Evaluate clause and internal-evidence retrieval for the MVP compliance topics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from open_deep_research.compliance.clause_store import ClauseStore, clause_file_for_index
from open_deep_research.compliance.retrieval import ComplianceRetriever
from open_deep_research.compliance.review_topics import ISO_13485_MVP_TOPICS
from open_deep_research.configuration import Configuration


def main() -> int:
    config = Configuration()
    parser = argparse.ArgumentParser(description="Evaluate retrieval quality for compliance MVP topics.")
    parser.add_argument("--index-dir", default=config.compliance_index_path)
    parser.add_argument("--internal-top-k", type=int, default=5)
    parser.add_argument("--json-output", default="", help="Optional path for machine-readable evaluation results.")
    args = parser.parse_args()

    retriever = ComplianceRetriever.from_index_dir(args.index_dir)
    clause_store = ClauseStore.from_path(clause_file_for_index(args.index_dir))
    rows = []

    for topic in ISO_13485_MVP_TOPICS:
        clauses = clause_store.get_many(topic.standard_clause_refs)
        internal_results = retriever.search(
            topic.internal_query,
            source_type="internal",
            top_k=args.internal_top_k,
            preferred_terms=list(topic.preferred_internal_terms),
        )
        expected_clause_ids = [f"{standard} {clause_id}" for standard, clause_id in topic.standard_clause_refs]
        found_clause_ids = [f"{clause.standard} {clause.clause_id}" for clause in clauses]
        rows.append(
            {
                "topic_id": topic.topic_id,
                "title": topic.title,
                "expected_clause_ids": expected_clause_ids,
                "found_clause_ids": found_clause_ids,
                "clause_hit_count": len(found_clause_ids),
                "clause_expected_count": len(expected_clause_ids),
                "internal_result_count": len(internal_results),
                "top_internal_evidence": [
                    {
                        "evidence_id": item.evidence_id,
                        "file_name": item.file_name,
                        "page_number": item.page_number,
                        "sheet_name": item.sheet_name,
                        "row_range": item.row_range,
                        "score": item.score,
                    }
                    for item in internal_results[:3]
                ],
                "needs_attention": len(found_clause_ids) < len(expected_clause_ids) or not internal_results,
            }
        )

    print(_render_markdown(rows))
    if args.json_output:
        output_path = Path(args.json_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nWrote JSON evaluation to {output_path.resolve()}")
    return 0


def _render_markdown(rows: list[dict]) -> str:
    total = len(rows)
    clause_ok = sum(1 for row in rows if row["clause_hit_count"] >= row["clause_expected_count"])
    internal_ok = sum(1 for row in rows if row["internal_result_count"] > 0)
    lines = [
        "# Compliance Retrieval Evaluation",
        "",
        f"- Topics: {total}",
        f"- Clause coverage: {clause_ok}/{total}",
        f"- Internal evidence coverage: {internal_ok}/{total}",
        "",
        "| Topic | Clauses | Internal Evidence | Top Internal Files | Attention |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        top_files = "; ".join(
            f"[{item['evidence_id']}] {item['file_name']}" for item in row["top_internal_evidence"]
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    row["title"],
                    f"{row['clause_hit_count']}/{row['clause_expected_count']}",
                    str(row["internal_result_count"]),
                    top_files or "-",
                    "YES" if row["needs_attention"] else "NO",
                ]
            )
            + " |"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

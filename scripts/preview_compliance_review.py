"""Preview topic-level evidence retrieval before running the LLM reviewer."""

from __future__ import annotations

import argparse
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

from open_deep_research.compliance.retrieval import ComplianceRetriever
from open_deep_research.compliance.review_topics import select_review_topics
from open_deep_research.configuration import Configuration


def main() -> int:
    config = Configuration()
    parser = argparse.ArgumentParser(description="Preview compliance evidence grouped by review topic.")
    parser.add_argument("--index-dir", default=config.compliance_index_path)
    parser.add_argument(
        "--request",
        default="Run an ISO 13485 mock audit for the internal QMS documents.",
        help="Review request used to select topics.",
    )
    parser.add_argument("--standard-top-k", type=int, default=3)
    parser.add_argument("--internal-top-k", type=int, default=5)
    parser.add_argument("--full", action="store_true", help="Print excerpts instead of file-level summaries only.")
    args = parser.parse_args()

    retriever = ComplianceRetriever.from_index_dir(args.index_dir)
    topics = select_review_topics(args.request)
    print(f"Request: {args.request}")
    print(f"Selected topics: {len(topics)}")

    for topic in topics:
        print("\n" + "=" * 100)
        print(f"{topic.title} [{topic.topic_id}]")
        print(f"Expected evidence: {topic.expected_evidence}")
        _print_results(
            "Official standard evidence",
            retriever.search(topic.standard_query, source_type="standard", top_k=args.standard_top_k),
            args.full,
        )
        _print_results(
            "Internal QMS evidence",
            retriever.search(
                topic.internal_query,
                source_type="internal",
                top_k=args.internal_top_k,
                preferred_terms=list(topic.preferred_internal_terms),
            ),
            args.full,
        )

    return 0


def _print_results(title: str, results, full: bool) -> None:
    print(f"\n{title}: {len(results)} result(s)")
    if not results:
        print("- No evidence found.")
        return
    for index, item in enumerate(results, start=1):
        location = []
        if item.page_number:
            location.append(f"page {item.page_number}")
        if item.sheet_name:
            location.append(f"sheet {item.sheet_name}")
        if item.row_range:
            location.append(f"rows {item.row_range}")
        location_text = ", ".join(location) or "location unavailable"
        print(f"- {index}. {item.file_name} ({location_text}, score={item.score})")
        if full:
            print(f"  {item.excerpt[:700].replace(chr(10), ' ')}")


if __name__ == "__main__":
    raise SystemExit(main())

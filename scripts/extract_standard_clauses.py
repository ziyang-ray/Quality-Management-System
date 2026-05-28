"""Extract candidate standard clauses from official PDF files."""

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

from open_deep_research.compliance.clause_extraction import extract_standard_clauses
from open_deep_research.configuration import Configuration


DEFAULT_STANDARDS = (
    ("ISO 13485:2016", "ISO13485-2016中文版.pdf"),
    ("ISO 14971:2019", "EN-ISO-14971-2019-Application-of-risk-management.pdf"),
)


def main() -> int:
    config = Configuration()
    parser = argparse.ArgumentParser(description="Extract candidate clauses from official standard PDFs.")
    parser.add_argument("--official-docs", default=config.official_docs_path)
    parser.add_argument("--output-dir", default="data/standard_clauses")
    args = parser.parse_args()

    official_root = Path(args.official_docs)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_clauses = []
    for standard_name, file_name in DEFAULT_STANDARDS:
        path = official_root / file_name
        if not path.exists():
            print(f"Missing standard PDF: {path}")
            continue
        clauses = extract_standard_clauses(path, standard_name)
        all_clauses.extend(clauses)
        print(f"{standard_name}: extracted {len(clauses)} candidate clauses from {path.name}")

    jsonl_path = output_dir / "clauses.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as file:
        for clause in all_clauses:
            file.write(clause.model_dump_json(ensure_ascii=False) + "\n")

    review_path = output_dir / "clauses_review.md"
    review_path.write_text(_review_markdown(all_clauses), encoding="utf-8")
    print(f"Wrote {len(all_clauses)} clauses to {jsonl_path.resolve()}")
    print(f"Wrote review file to {review_path.resolve()}")
    return 0


def _review_markdown(clauses) -> str:
    lines = ["# Standard Clause Extraction Review", ""]
    for clause in clauses:
        lines.extend(
            [
                f"## {clause.standard} {clause.clause_id} {clause.title}",
                "",
                f"- Pages: {clause.page_start}-{clause.page_end}",
                f"- Status: {clause.extraction_status}",
                f"- Search terms: {', '.join(clause.search_terms[:10])}",
                f"- Expected evidence: {'; '.join(clause.expected_evidence) or 'TBD'}",
                "",
                "Summary:",
                "",
                clause.requirement_summary or "TBD",
                "",
            ]
        )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

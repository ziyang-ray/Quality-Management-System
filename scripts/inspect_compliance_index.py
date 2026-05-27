"""Inspect the local compliance index and optionally run a sample query."""

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

from open_deep_research.compliance.index_store import read_metadata
from open_deep_research.compliance.prompts import format_evidence_block
from open_deep_research.compliance.retrieval import ComplianceRetriever
from open_deep_research.configuration import Configuration


def main() -> int:
    config = Configuration()
    parser = argparse.ArgumentParser(description="Inspect a compliance evidence index.")
    parser.add_argument("--index-dir", default=config.compliance_index_path)
    parser.add_argument("--query", default="")
    parser.add_argument("--source-type", choices=["standard", "internal"], default=None)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    metadata = read_metadata(args.index_dir)
    print(f"Indexed files: {metadata.total_files_indexed}/{metadata.total_files_seen}")
    print(f"Chunks: {metadata.total_chunks}")
    print(f"Skipped files: {len(metadata.skipped_files)}")
    if metadata.skipped_files:
        print("First skipped files:")
        for item in metadata.skipped_files[:10]:
            print(f"- {item.get('path')}: {item.get('reason')}")

    if args.query:
        retriever = ComplianceRetriever.from_index_dir(args.index_dir)
        results = retriever.search(args.query, source_type=args.source_type, top_k=args.top_k)
        print("\nSearch results:")
        print(format_evidence_block(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

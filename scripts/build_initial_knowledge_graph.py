"""Build initial compliance knowledge graph with common ISO 13485 relationships."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from open_deep_research.compliance.knowledge_graph import ComplianceKnowledgeGraph, build_initial_compliance_graph


def main() -> int:
    """Build and save the initial compliance knowledge graph."""

    graph = build_initial_compliance_graph()

    output_dir = REPO_ROOT / "data" / "compliance_graph"
    graph.save(output_dir)

    stats = graph.get_statistics()
    print("Knowledge graph built successfully!")
    print(f"Output directory: {output_dir}")
    print(f"Statistics: {stats}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

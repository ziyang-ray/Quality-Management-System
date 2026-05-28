"""Run a multi-agent audit simulation."""

from __future__ import annotations

import argparse
import asyncio
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

from open_deep_research.compliance.agents.orchestrator import AuditOrchestrator
from open_deep_research.compliance.clause_store import ClauseStore
from open_deep_research.compliance.clause_topic_mapping import (
    select_clauses_directly,
    select_topics_and_clauses,
)
from open_deep_research.compliance.retrieval import ComplianceRetriever
from open_deep_research.configuration import Configuration


async def main() -> int:
    config = Configuration()
    parser = argparse.ArgumentParser(description="Run a multi-agent audit simulation.")
    parser.add_argument("--request", required=True, help="Audit request")
    parser.add_argument("--clause-store", default=config.clause_store_path)
    parser.add_argument("--index-dir", default=config.compliance_index_path)
    parser.add_argument("--model", default=config.final_report_model)
    parser.add_argument("--max-clauses", type=int, default=5, help="Max clauses to audit")
    parser.add_argument("--output", default="", help="Output file path")
    args = parser.parse_args()

    # Load clause store and retriever
    clause_store = ClauseStore.from_jsonl(args.clause_store)
    retriever = ComplianceRetriever.from_index_dir(args.index_dir)

    # Select clauses
    clauses = select_clauses_directly(args.request, clause_store)
    if not clauses:
        mappings = select_topics_and_clauses(args.request, clause_store)
        clause_refs = []
        for m in mappings:
            clause_refs.extend(m.clause_refs)
        clauses = clause_store.get_clauses_by_ids(clause_refs)

    # Limit clauses
    clauses = clauses[:args.max_clauses]

    if not clauses:
        print("No clauses selected for audit.")
        return 1

    print(f"Selected {len(clauses)} clauses for audit:")
    for c in clauses:
        print(f"  - {c.standard} {c.clause_id}: {c.title}")

    # Create orchestrator
    orchestrator = AuditOrchestrator(
        clause_store=clause_store,
        retriever=retriever,
        model_name=args.model,
    )

    # Conduct audit
    print("\nStarting multi-agent audit simulation...")
    session = await orchestrator.conduct_audit(
        scope=args.request,
        clauses=clauses,
        max_questions_per_clause=2,
    )

    # Output results
    print("\n" + "=" * 60)
    print("AUDIT SIMULATION COMPLETE")
    print("=" * 60)
    print(f"\nSession ID: {session.session_id}")
    print(f"Status: {session.status}")
    print(f"Clauses audited: {len(session.clauses_audited)}")

    # Print dialogue
    print("\n" + "=" * 60)
    print("DIALOGUE HISTORY")
    print("=" * 60)
    print(orchestrator.get_dialogue_history())

    # Print assessments
    print("\n" + "=" * 60)
    print("ASSESSMENTS")
    print("=" * 60)
    for assessment in session.assessments:
        print(f"\n{assessment['standard']} {assessment['clause_id']}: {assessment['status']}")
        print(f"  Rationale: {assessment['rationale'][:200]}...")

    # Save to file if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# Multi-Agent Audit Simulation Report\n\n")
            f.write(f"**Session ID**: {session.session_id}\n")
            f.write(f"**Scope**: {session.scope}\n")
            f.write(f"**Status**: {session.status}\n\n")

            f.write("## Dialogue History\n\n")
            f.write(orchestrator.get_dialogue_history())
            f.write("\n\n## Assessments\n\n")

            for assessment in session.assessments:
                f.write(f"### {assessment['standard']} {assessment['clause_id']}\n")
                f.write(f"**Status**: {assessment['status']}\n\n")
                f.write(f"**Rationale**: {assessment['rationale']}\n\n")

        print(f"\nReport saved to: {output_path.resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

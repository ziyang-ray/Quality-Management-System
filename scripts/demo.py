"""Demo script showcasing QMS Compliance Reviewer capabilities."""

import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


async def demo_memory_system():
    """Demo the memory system."""
    print("\n" + "=" * 60)
    print("DEMO: Memory System")
    print("=" * 60)

    from open_deep_research.compliance.memory import (
        ReviewHistory,
        ReviewSession,
        CAPATracker,
        QueryMemory,
    )
    from open_deep_research.compliance.schemas import ClauseAssessment

    # Create instances
    history = ReviewHistory("data/demo_memory/review_history.json")
    capa_tracker = CAPATracker("data/demo_memory/capa_tracker.json")
    query_memory = QueryMemory("data/demo_memory/query_memory.json")

    # Create a sample session
    session = ReviewSession(
        session_id="demo_session_001",
        timestamp="2026-05-28T10:00:00",
        request="Demo audit request",
        assessments=[],
    )

    # Create sample assessments
    assessments = [
        ClauseAssessment(
            standard="ISO 13485:2016",
            clause_id="8.5.2",
            requirement_summary="纠正措施",
            status="符合",
            rationale="有完整的CAPA流程",
        ),
        ClauseAssessment(
            standard="ISO 13485:2016",
            clause_id="7.4.1",
            requirement_summary="采购过程",
            status="缺乏证据",
            rationale="未找到供方评价记录",
        ),
    ]

    # Save to history
    history.save_session(session, assessments)
    print("✓ Saved review session to history")

    # Record query feedback
    query_memory.record_feedback(
        query="CAPA corrective action",
        clause_id="8.5.2",
        relevant=True,
        feedback="Found TP_020",
    )
    print("✓ Recorded query feedback")

    # Generate reports
    print("\n--- Review History Report ---")
    print(history.generate_summary_report())

    print("\n--- CAPA Report ---")
    print(capa_tracker.generate_report())

    print("\n--- Query Memory Report ---")
    print(query_memory.generate_report())


async def demo_multi_agent():
    """Demo the multi-agent system."""
    print("\n" + "=" * 60)
    print("DEMO: Multi-Agent System")
    print("=" * 60)

    from open_deep_research.compliance.agents.roles import AUDIT_PROFILES, AuditRole

    # Show all agent profiles
    print("\nAgent Profiles:")
    for role, profile in AUDIT_PROFILES.items():
        print(f"\n{profile.name} ({profile.title})")
        print(f"  Expertise: {', '.join(profile.expertise)}")
        print(f"  Personality: {profile.personality}")
        print(f"  Focus: {', '.join(profile.focus_areas)}")


async def demo_clause_store():
    """Demo the clause store."""
    print("\n" + "=" * 60)
    print("DEMO: Clause Store")
    print("=" * 60)

    from open_deep_research.compliance.clause_store import ClauseStore

    store = ClauseStore.from_jsonl("data/standard_clauses/clauses.jsonl")

    print(f"\nTotal clauses: {len(store)}")

    # Show some examples
    print("\nSample clauses:")
    for clause in store.get_all()[:5]:
        print(f"  - {clause.standard} {clause.clause_id}: {clause.title}")

    # Test search
    print("\nSearch for 'CAPA':")
    results = store.search_clauses("CAPA", top_k=3)
    for r in results:
        print(f"  - {r.clause_id}: {r.title}")


async def main():
    """Run all demos."""
    print("QMS Compliance Reviewer - Demo")
    print("=" * 60)

    await demo_clause_store()
    await demo_multi_agent()
    await demo_memory_system()

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

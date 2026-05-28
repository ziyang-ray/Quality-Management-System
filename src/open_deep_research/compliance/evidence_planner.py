"""Evidence retrieval planning enhanced by skills and knowledge graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from open_deep_research.compliance.clause_store import ClauseStore
from open_deep_research.compliance.knowledge_graph import ComplianceKnowledgeGraph
from open_deep_research.compliance.schemas import EvidenceSearchPlan, StandardClause
from open_deep_research.compliance.skill_loader import SkillLoader
from open_deep_research.compliance.review_topics import ReviewTopic


@dataclass
class EvidenceExpansion:
    """Expanded search terms from various sources."""

    base_terms: list[str] = field(default_factory=list)
    clause_terms: list[str] = field(default_factory=list)
    kg_terms: list[str] = field(default_factory=list)
    skill_terms: list[str] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)
    priority_files: list[str] = field(default_factory=list)


class EvidencePlanner:
    """Plan evidence retrieval by combining topic queries, clause terms, KG navigation, and skill insights.

    The planner creates an EvidenceSearchPlan that expands the base query with:
    - Standard clause search terms
    - Knowledge graph related files and processes
    - Skill pack preferred queries and red flags
    - Historical retrieval feedback

    This helps ensure comprehensive evidence collection before judgment.
    """

    def __init__(
        self,
        clause_store: ClauseStore | None = None,
        knowledge_graph: ComplianceKnowledgeGraph | None = None,
        skill_loader: SkillLoader | None = None,
    ):
        self.clause_store = clause_store
        self.knowledge_graph = knowledge_graph
        self.skill_loader = skill_loader

    def plan_evidence_search(
        self,
        topic: ReviewTopic,
        include_draft_skills: bool = False,
    ) -> EvidenceSearchPlan:
        """Create an evidence search plan for a review topic.

        Args:
            topic: The review topic to plan for
            include_draft_skills: Whether to include draft skills (for preview mode)

        Returns:
            An EvidenceSearchPlan with expanded search terms
        """

        expansion = EvidenceExpansion()
        expansion.base_terms = topic.standard_query.split()

        self._expand_from_clauses(topic, expansion)
        self._expand_from_knowledge_graph(topic, expansion)
        self._expand_from_skills(topic, expansion, include_draft_skills)

        all_terms = list(dict.fromkeys(
            expansion.base_terms
            + expansion.clause_terms
            + expansion.kg_terms
            + expansion.skill_terms
        ))

        return EvidenceSearchPlan(
            topic_id=topic.topic_id,
            base_query=topic.standard_query,
            clause_search_terms=expansion.clause_terms,
            kg_expanded_terms=expansion.kg_terms,
            skill_expanded_terms=expansion.skill_terms,
            red_flags_to_check=expansion.red_flags,
            priority_files=expansion.priority_files,
        )

    def plan_internal_evidence_search(
        self,
        topic: ReviewTopic,
        include_draft_skills: bool = False,
    ) -> EvidenceSearchPlan:
        """Create an evidence search plan for internal QMS evidence."""

        expansion = EvidenceExpansion()
        expansion.base_terms = topic.internal_query.split()

        self._expand_from_clauses(topic, expansion)
        self._expand_from_knowledge_graph(topic, expansion)
        self._expand_from_skills(topic, expansion, include_draft_skills)

        if topic.preferred_internal_terms:
            expansion.skill_terms.extend(topic.preferred_internal_terms)

        return EvidenceSearchPlan(
            topic_id=topic.topic_id,
            base_query=topic.internal_query,
            clause_search_terms=expansion.clause_terms,
            kg_expanded_terms=expansion.kg_terms,
            skill_expanded_terms=expansion.skill_terms,
            red_flags_to_check=expansion.red_flags,
            priority_files=expansion.priority_files,
        )

    def _expand_from_clauses(self, topic: ReviewTopic, expansion: EvidenceExpansion) -> None:
        """Expand search terms from standard clauses."""

        if not self.clause_store:
            return

        for standard, clause_id in topic.standard_clause_refs:
            clause = self.clause_store.get(standard, clause_id)
            if clause:
                expansion.clause_terms.extend(clause.search_terms)
                expansion.clause_terms.extend(clause.expected_evidence)

        expansion.clause_terms = list(dict.fromkeys(expansion.clause_terms))

    def _expand_from_knowledge_graph(self, topic: ReviewTopic, expansion: EvidenceExpansion) -> None:
        """Expand search terms from knowledge graph navigation."""

        if not self.knowledge_graph:
            return

        for standard, clause_id in topic.standard_clause_refs:
            evidence_chain = self.knowledge_graph.get_evidence_chain(standard, clause_id)

            for process in evidence_chain.get("processes", []):
                expansion.kg_terms.append(process.label)

            for procedure in evidence_chain.get("procedures", []):
                expansion.kg_terms.append(procedure.label)
                if "file_path" in procedure.metadata:
                    expansion.priority_files.append(procedure.metadata["file_path"])

            for record in evidence_chain.get("records", []):
                expansion.kg_terms.append(record.label)
                if "file_path" in record.metadata:
                    expansion.priority_files.append(record.metadata["file_path"])

        expansion.kg_terms = list(dict.fromkeys(expansion.kg_terms))
        expansion.priority_files = list(dict.fromkeys(expansion.priority_files))

    def _expand_from_skills(
        self,
        topic: ReviewTopic,
        expansion: EvidenceExpansion,
        include_draft: bool,
    ) -> None:
        """Expand search terms from skill packs."""

        if not self.skill_loader:
            return

        skills = self.skill_loader.get_approved_skills_for_topic(topic.topic_id)
        if include_draft:
            skills.extend(self.skill_loader.get_draft_skills_for_topic(topic.topic_id))

        for skill in skills:
            expansion.skill_terms.extend(skill.preferred_queries)
            expansion.red_flags.extend(skill.red_flags)

        expansion.skill_terms = list(dict.fromkeys(expansion.skill_terms))
        expansion.red_flags = list(dict.fromkeys(expansion.red_flags))

    def build_evidence_package(
        self,
        topic: ReviewTopic,
        standard_evidence: list[dict],
        internal_evidence: list[dict],
        standard_clauses: list[dict],
    ) -> dict:
        """Build a structured evidence package for a topic.

        This combines all evidence sources into a structured package
        that can be used by the compliance reviewer.
        """

        skill_insights: list[str] = []
        if self.skill_loader:
            merged = self.skill_loader.merge_skill_insights(
                topic.topic_id,
                include_draft=False,
            )
            skill_insights = merged.get("red_flags", []) + merged.get("review_checklist", [])

        kg_related_files: list[str] = []
        if self.knowledge_graph:
            for standard, clause_id in topic.standard_clause_refs:
                chain = self.knowledge_graph.get_evidence_chain(standard, clause_id)
                for proc in chain.get("procedures", []):
                    if "file_path" in proc.metadata:
                        kg_related_files.append(proc.metadata["file_path"])

        limitations: list[str] = []
        if not standard_evidence:
            limitations.append("未找到官方标准证据。")
        if not internal_evidence:
            limitations.append("未找到内部QMS证据。")
        if not standard_clauses:
            limitations.append("未找到结构化标准条款。")

        return {
            "topic_id": topic.topic_id,
            "topic_title": topic.title,
            "expected_evidence": topic.expected_evidence,
            "standard_clauses": standard_clauses,
            "standard_evidence": standard_evidence,
            "internal_evidence": internal_evidence,
            "skill_insights": skill_insights,
            "kg_related_files": kg_related_files,
            "limitations": limitations,
        }


def create_evidence_planner(
    clause_store_path: str | None = None,
    knowledge_graph_dir: str | None = None,
    skills_dir: str | None = None,
) -> EvidencePlanner:
    """Factory function to create an EvidencePlanner with optional components."""

    clause_store = None
    if clause_store_path:
        try:
            clause_store = ClauseStore.from_path(clause_store_path)
        except Exception:
            pass

    knowledge_graph = None
    if knowledge_graph_dir:
        try:
            knowledge_graph = ComplianceKnowledgeGraph.from_directory(knowledge_graph_dir)
        except Exception:
            pass

    skill_loader = None
    if skills_dir:
        try:
            skill_loader = SkillLoader.from_directory(skills_dir)
        except Exception:
            pass

    return EvidencePlanner(
        clause_store=clause_store,
        knowledge_graph=knowledge_graph,
        skill_loader=skill_loader,
    )

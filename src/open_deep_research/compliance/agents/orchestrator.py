"""Audit orchestrator for coordinating multi-agent audit simulation."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from open_deep_research.compliance.agents.department_rep import DepartmentRepAgent
from open_deep_research.compliance.agents.lead_auditor import LeadAuditorAgent
from open_deep_research.compliance.agents.roles import (
    AgentProfile,
    AuditRole,
    DialogueHistory,
    AUDIT_PROFILES,
)
from open_deep_research.compliance.clause_store import ClauseStore
from open_deep_research.compliance.memory import ReviewHistory, ReviewSession
from open_deep_research.compliance.retrieval import ComplianceRetriever
from open_deep_research.compliance.schemas import (
    ClauseAssessment,
    ComplianceReviewReport,
    EvidenceItem,
    StandardClause,
)


@dataclass
class AuditSession:
    """A complete audit session."""

    session_id: str
    scope: str
    start_time: str
    end_time: str = ""
    status: str = "in_progress"  # in_progress, completed, aborted
    clauses_audited: list[dict] = field(default_factory=list)
    assessments: list[dict] = field(default_factory=list)
    dialogue_history: list[dict] = field(default_factory=list)
    findings_summary: str = ""

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "scope": self.scope,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status,
            "clauses_audited": self.clauses_audited,
            "assessments": self.assessments,
            "dialogue_history": self.dialogue_history,
            "findings_summary": self.findings_summary,
        }


class AuditOrchestrator:
    """Orchestrator for multi-agent audit simulation."""

    def __init__(self, clause_store: ClauseStore,
                 retriever: ComplianceRetriever,
                 model_name: str = "anthropic:mimo-v2.5-pro"):
        self.clause_store = clause_store
        self.retriever = retriever
        self.model_name = model_name

        # Initialize agents
        self.lead_auditor = LeadAuditorAgent(model_name=model_name)
        self.department_rep = DepartmentRepAgent(model_name=model_name)

        # Dialogue tracking
        self.dialogue = DialogueHistory()

    async def conduct_audit(self, scope: str,
                           clauses: list[StandardClause],
                           max_questions_per_clause: int = 3) -> AuditSession:
        """Conduct a complete audit simulation."""
        session_id = f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now().isoformat()

        session = AuditSession(
            session_id=session_id,
            scope=scope,
            start_time=start_time,
        )

        # Step 1: Lead auditor creates audit plan
        self._add_dialogue(
            self.lead_auditor.profile.name,
            self.lead_auditor.profile.role,
            f"开始审核：{scope}\n需要审核{len(clauses)}个条款。"
        )

        plan = await self.lead_auditor.plan_audit(scope, clauses)

        self._add_dialogue(
            self.lead_auditor.profile.name,
            self.lead_auditor.profile.role,
            f"审核计划已制定，重点关注：{', '.join(plan.focus_areas)}"
        )

        # Step 2: Audit each clause
        assessments = []
        for clause in clauses:
            clause_assessment = await self._audit_single_clause(
                clause, max_questions_per_clause
            )
            assessments.append(clause_assessment)

            session.clauses_audited.append({
                "clause_id": clause.clause_id,
                "standard": clause.standard,
                "title": clause.title,
            })

        # Step 3: Lead auditor summarizes findings
        summary = await self.lead_auditor.summarize_findings(assessments)

        self._add_dialogue(
            self.lead_auditor.profile.name,
            self.lead_auditor.profile.role,
            f"审核总结：\n{summary}"
        )

        # Complete session
        session.end_time = datetime.now().isoformat()
        session.status = "completed"
        session.assessments = [a.model_dump() for a in assessments]
        session.dialogue_history = self.dialogue.to_dict()["entries"]
        session.findings_summary = summary

        return session

    async def _audit_single_clause(self, clause: StandardClause,
                                  max_questions: int) -> ClauseAssessment:
        """Audit a single clause with dialogue."""
        # Get evidence
        query = " ".join(clause.search_terms[:8])
        evidence = self.retriever.search(query, source_type="internal", top_k=5)

        # Set evidence for department rep
        self.department_rep.set_available_evidence(evidence)

        # Lead auditor introduces the clause
        self._add_dialogue(
            self.lead_auditor.profile.name,
            self.lead_auditor.profile.role,
            f"现在审核条款 {clause.standard} {clause.clause_id}: {clause.title}"
        )

        # Department rep introduces their process
        intro = await self.department_rep.introduce_process(clause)
        self._add_dialogue(
            self.department_rep.profile.name,
            self.department_rep.profile.role,
            intro
        )

        # Lead auditor asks questions
        questions = await self.lead_auditor.generate_questions(clause, evidence)

        for question in questions[:max_questions]:
            # Auditor asks
            self._add_dialogue(
                self.lead_auditor.profile.name,
                self.lead_auditor.profile.role,
                question.question
            )

            # Department rep responds
            response = await self.department_rep.respond_to_question(
                question.question, clause, evidence
            )
            self._add_dialogue(
                self.department_rep.profile.name,
                self.department_rep.profile.role,
                response.answer
            )

            # If follow-up needed
            if response.follow_up_needed:
                self._add_dialogue(
                    self.lead_auditor.profile.name,
                    self.lead_auditor.profile.role,
                    f"请补充说明：{response.follow_up_reason}"
                )

        # Lead auditor makes assessment
        assessment = await self.lead_auditor.review_evidence(clause, evidence)

        self._add_dialogue(
            self.lead_auditor.profile.name,
            self.lead_auditor.profile.role,
            f"条款 {clause.clause_id} 评估结果：{assessment.status}"
        )

        return assessment

    def _add_dialogue(self, speaker: str, role: AuditRole, content: str):
        """Add entry to dialogue history."""
        self.dialogue.add(
            speaker=speaker,
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(),
        )

    def get_dialogue_history(self) -> str:
        """Get formatted dialogue history."""
        return self.dialogue.get_formatted()

    def get_dialogue_dict(self) -> dict:
        """Get dialogue history as dictionary."""
        return self.dialogue.to_dict()

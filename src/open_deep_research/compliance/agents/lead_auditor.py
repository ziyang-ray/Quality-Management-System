"""Lead Auditor agent for compliance audit simulation."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage

from open_deep_research.compliance.agents.roles import (
    AgentProfile,
    AuditRole,
    DialogueHistory,
    AUDIT_PROFILES,
)
from open_deep_research.compliance.schemas import (
    ClauseAssessment,
    ComplianceReviewReport,
    EvidenceItem,
    StandardClause,
)


@dataclass
class AuditPlan:
    """Audit plan created by lead auditor."""

    scope: str
    clauses: list[dict]
    schedule: list[dict]
    focus_areas: list[str]
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "scope": self.scope,
            "clauses": self.clauses,
            "schedule": self.schedule,
            "focus_areas": self.focus_areas,
            "notes": self.notes,
        }


@dataclass
class AuditQuestion:
    """A question from the auditor."""

    question_id: str
    clause_id: str
    question: str
    context: str
    expected_answer_type: str  # process, evidence, explanation

    def to_dict(self) -> dict:
        return {
            "question_id": self.question_id,
            "clause_id": self.clause_id,
            "question": self.question,
            "context": self.context,
            "expected_answer_type": self.expected_answer_type,
        }


class LeadAuditorAgent:
    """Lead auditor agent for conducting compliance audits."""

    def __init__(self, profile: Optional[AgentProfile] = None, model_name: str = "anthropic:mimo-v2.5-pro"):
        self.profile = profile or AUDIT_PROFILES[AuditRole.LEAD_AUDITOR]
        self.model_name = model_name
        self.findings: list[dict] = []
        self.questions: list[AuditQuestion] = []
        self.dialogue = DialogueHistory()

    def _get_model(self):
        """Get the LLM model."""
        from langchain.chat_models import init_chat_model
        return init_chat_model(self.model_name)

    async def plan_audit(self, scope: str,
                        clauses: list[StandardClause]) -> AuditPlan:
        """Create an audit plan based on scope and clauses."""
        model = self._get_model()

        clause_list = "\n".join(
            f"- {c.standard} {c.clause_id}: {c.title}"
            for c in clauses
        )

        prompt = f"""作为主审核员，请为以下审核范围制定审核计划：

审核范围：{scope}

需要审核的条款：
{clause_list}

请制定审核计划，包括：
1. 审核重点
2. 时间安排（简化版）
3. 需要特别关注的领域

请用JSON格式返回。"""

        try:
            response = await model.ainvoke([
                SystemMessage(content=self.profile.get_system_prompt()),
                HumanMessage(content=prompt),
            ])

            # Parse response and create plan
            return AuditPlan(
                scope=scope,
                clauses=[c.to_dict() for c in clauses],
                schedule=[{"clause": c.clause_id, "estimated_time": "30min"} for c in clauses],
                focus_areas=self.profile.focus_areas,
                notes=response.content,
            )
        except Exception:
            # Fallback plan
            return AuditPlan(
                scope=scope,
                clauses=[c.to_dict() for c in clauses],
                schedule=[{"clause": c.clause_id, "estimated_time": "30min"} for c in clauses],
                focus_areas=self.profile.focus_areas,
            )

    async def generate_questions(self, clause: StandardClause,
                                evidence: list[EvidenceItem]) -> list[AuditQuestion]:
        """Generate audit questions for a clause."""
        model = self._get_model()

        evidence_summary = "\n".join(
            f"- {e.file_name}: {e.excerpt[:100]}..."
            for e in evidence[:3]
        )

        prompt = f"""作为主审核员，请为以下条款生成审核问题：

条款：{clause.standard} {clause.clause_id} - {clause.title}
要求摘要：{clause.requirement_summary}

现有证据：
{evidence_summary}

请生成3-5个审核问题，包括：
1. 流程相关问题
2. 证据相关问题
3. 解释性问题

请用JSON格式返回问题列表。"""

        try:
            response = await model.ainvoke([
                SystemMessage(content=self.profile.get_system_prompt()),
                HumanMessage(content=prompt),
            ])

            # Parse response and create questions
            questions = []
            for i, clause_id in enumerate([clause.clause_id] * 3):
                questions.append(AuditQuestion(
                    question_id=f"Q-{clause.clause_id}-{i+1}",
                    clause_id=clause.clause_id,
                    question=f"请说明{clause.title}的实施情况",
                    context=clause.requirement_summary,
                    expected_answer_type="explanation",
                ))

            return questions
        except Exception:
            return [AuditQuestion(
                question_id=f"Q-{clause.clause_id}-1",
                clause_id=clause.clause_id,
                question=f"请说明{clause.title}的实施情况",
                context=clause.requirement_summary,
                expected_answer_type="explanation",
            )]

    async def review_evidence(self, clause: StandardClause,
                             evidence: list[EvidenceItem]) -> ClauseAssessment:
        """Review evidence and make assessment."""
        model = self._get_model()

        evidence_text = "\n".join(
            f"[{i+1}] {e.file_name} (score={e.score}):\n{e.excerpt}"
            for i, e in enumerate(evidence)
        )

        prompt = f"""作为主审核员，请评估以下条款的符合性：

条款：{clause.standard} {clause.clause_id} - {clause.title}
要求：{clause.requirement_summary}

证据：
{evidence_text}

请评估：
1. 证据是否充分支持符合性
2. 是否存在不符合项
3. 风险和建议

请用以下状态之一：符合、需澄清、缺乏证据、未提及"""

        try:
            response = await model.ainvoke([
                SystemMessage(content=self.profile.get_system_prompt()),
                HumanMessage(content=prompt),
            ])

            # Determine status from response
            content = response.content
            status = "需澄清"
            if "符合" in content and "不符合" not in content:
                status = "符合"
            elif "缺乏证据" in content:
                status = "缺乏证据"
            elif "未提及" in content:
                status = "未提及"

            return ClauseAssessment(
                standard=clause.standard,
                clause_id=clause.clause_id,
                requirement_summary=clause.requirement_summary,
                status=status,
                rationale=content,
                evidence=evidence,
                risk="",
                recommendation="",
            )
        except Exception:
            return ClauseAssessment(
                standard=clause.standard,
                clause_id=clause.clause_id,
                requirement_summary=clause.requirement_summary,
                status="需澄清",
                rationale="无法完成评估",
                evidence=evidence,
                risk="",
                recommendation="",
            )

    async def summarize_findings(self, assessments: list[ClauseAssessment]) -> str:
        """Summarize audit findings."""
        model = self._get_model()

        findings_text = "\n".join(
            f"- {a.standard} {a.clause_id}: {a.status} - {a.rationale[:100]}..."
            for a in assessments
        )

        prompt = f"""作为主审核员，请总结以下审核发现：

{findings_text}

请提供：
1. 整体评价
2. 主要发现
3. 重大不符合项（如有）
4. 改进建议"""

        try:
            response = await model.ainvoke([
                SystemMessage(content=self.profile.get_system_prompt()),
                HumanMessage(content=prompt),
            ])
            return response.content
        except Exception:
            return "无法生成总结"

    def add_dialogue_entry(self, content: str):
        """Add entry to dialogue history."""
        self.dialogue.add(
            speaker=self.profile.name,
            role=self.profile.role,
            content=content,
            timestamp=datetime.now().isoformat(),
        )

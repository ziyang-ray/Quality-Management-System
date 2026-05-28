"""Department Representative agent for compliance audit simulation."""

from __future__ import annotations

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
from open_deep_research.compliance.schemas import EvidenceItem, StandardClause


@dataclass
class DepartmentResponse:
    """Response from department representative."""

    question_id: str
    answer: str
    evidence_provided: list[str]
    follow_up_needed: bool = False
    follow_up_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "question_id": self.question_id,
            "answer": self.answer,
            "evidence_provided": self.evidence_provided,
            "follow_up_needed": self.follow_up_needed,
            "follow_up_reason": self.follow_up_reason,
        }


class DepartmentRepAgent:
    """Department representative agent for responding to audit questions."""

    def __init__(self, profile: Optional[AgentProfile] = None,
                 model_name: str = "anthropic:mimo-v2.5-pro"):
        self.profile = profile or AUDIT_PROFILES[AuditRole.DEPARTMENT_REP]
        self.model_name = model_name
        self.dialogue = DialogueHistory()
        self.available_evidence: list[EvidenceItem] = []

    def _get_model(self):
        """Get the LLM model."""
        from langchain.chat_models import init_chat_model
        return init_chat_model(self.model_name)

    def set_available_evidence(self, evidence: list[EvidenceItem]):
        """Set available evidence for responses."""
        self.available_evidence = evidence

    async def respond_to_question(self, question: str,
                                 clause: StandardClause,
                                 evidence: list[EvidenceItem]) -> DepartmentResponse:
        """Respond to an auditor's question."""
        model = self._get_model()

        evidence_text = "\n".join(
            f"- {e.file_name}: {e.excerpt[:200]}..."
            for e in evidence[:5]
        )

        prompt = f"""作为部门代表，请回答审核员的问题：

审核员问题：{question}

相关条款：{clause.standard} {clause.clause_id} - {clause.title}

可用证据：
{evidence_text}

请基于可用证据回答问题，说明：
1. 我们是如何执行的
2. 有哪些证据支持
3. 是否需要补充说明

请用中文回复，保持专业和配合的态度。"""

        try:
            response = await model.ainvoke([
                SystemMessage(content=self.profile.get_system_prompt()),
                HumanMessage(content=prompt),
            ])

            # Determine if follow-up is needed
            follow_up_needed = "需要补充" in response.content or "不完整" in response.content

            return DepartmentResponse(
                question_id=f"R-{clause.clause_id}-{datetime.now().strftime('%H%M%S')}",
                answer=response.content,
                evidence_provided=[e.file_name for e in evidence[:3]],
                follow_up_needed=follow_up_needed,
            )
        except Exception:
            return DepartmentResponse(
                question_id=f"R-{clause.clause_id}-{datetime.now().strftime('%H%M%S')}",
                answer="抱歉，我需要查看相关文件后才能回答这个问题。",
                evidence_provided=[],
                follow_up_needed=True,
                follow_up_reason="需要查看文件",
            )

    async def introduce_process(self, clause: StandardClause) -> str:
        """Introduce the department's process for a clause."""
        model = self._get_model()

        prompt = f"""作为部门代表，请介绍我们部门在以下方面的流程：

条款：{clause.standard} {clause.clause_id} - {clause.title}
要求：{clause.requirement_summary}

请简要介绍：
1. 我们的主要流程
2. 负责的人员/部门
3. 关键控制点

请用中文回复，保持专业和自信。"""

        try:
            response = await model.ainvoke([
                SystemMessage(content=self.profile.get_system_prompt()),
                HumanMessage(content=prompt),
            ])
            return response.content
        except Exception:
            return f"关于{clause.title}，我们有相应的流程和文件支持。"

    async def provide_evidence(self, requirement: str,
                              available_files: list[str]) -> list[str]:
        """Provide evidence files for a requirement."""
        # Match requirement with available files
        relevant_files = []
        requirement_lower = requirement.lower()

        for file_name in available_files:
            file_lower = file_name.lower()
            # Simple keyword matching
            if any(keyword in file_lower for keyword in requirement_lower.split()):
                relevant_files.append(file_name)

        # If no match, return first few files as potential evidence
        if not relevant_files and available_files:
            relevant_files = available_files[:3]

        return relevant_files

    def add_dialogue_entry(self, content: str):
        """Add entry to dialogue history."""
        self.dialogue.add(
            speaker=self.profile.name,
            role=self.profile.role,
            content=content,
            timestamp=datetime.now().isoformat(),
        )

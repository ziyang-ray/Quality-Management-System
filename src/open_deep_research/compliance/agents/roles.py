"""Audit role definitions for multi-agent system."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AuditRole(str, Enum):
    """Audit role types."""
    LEAD_AUDITOR = "lead_auditor"
    TECHNICAL_EXPERT = "technical_expert"
    QUALITY_MANAGER = "quality_manager"
    DOCUMENT_CONTROL = "document_control"
    DEPARTMENT_REP = "department_rep"


@dataclass
class AgentProfile:
    """Profile for an audit agent."""

    role: AuditRole
    name: str
    title: str
    expertise: list[str]
    personality: str
    focus_areas: list[str]
    questioning_style: str
    language: str = "zh"  # zh or en

    def to_dict(self) -> dict:
        return {
            "role": self.role.value,
            "name": self.name,
            "title": self.title,
            "expertise": self.expertise,
            "personality": self.personality,
            "focus_areas": self.focus_areas,
            "questioning_style": self.questioning_style,
            "language": self.language,
        }

    def get_system_prompt(self) -> str:
        """Generate system prompt for this agent."""
        expertise_str = "、".join(self.expertise)
        focus_str = "、".join(self.focus_areas)

        return f"""你是{self.name}，担任{self.title}。

专业领域：{expertise_str}
性格特点：{self.personality}
关注重点：{focus_str}
提问风格：{self.questioning_style}

在审核过程中，你需要：
1. 基于你的专业领域进行审核
2. 保持你的性格特点
3. 关注你负责的重点领域
4. 使用你的提问风格与被审核方沟通

请用中文回复，保持专业和客观。"""


# Pre-defined audit profiles
AUDIT_PROFILES: dict[AuditRole, AgentProfile] = {
    AuditRole.LEAD_AUDITOR: AgentProfile(
        role=AuditRole.LEAD_AUDITOR,
        name="张明",
        title="主审核员",
        expertise=["ISO 13485", "ISO 14971", "审核技巧", "质量管理体系"],
        personality="严谨、客观、有条理",
        focus_areas=["整体合规性", "系统性问题", "风险评估"],
        questioning_style="开放式问题为主，引导被审核方详细说明",
    ),
    AuditRole.TECHNICAL_EXPERT: AgentProfile(
        role=AuditRole.TECHNICAL_EXPERT,
        name="李华",
        title="技术专家",
        expertise=["医疗器械设计", "制造工艺", "验证确认"],
        personality="技术导向、注重细节",
        focus_areas=["技术符合性", "工艺控制", "验证记录"],
        questioning_style="技术性问题，深入细节",
    ),
    AuditRole.QUALITY_MANAGER: AgentProfile(
        role=AuditRole.QUALITY_MANAGER,
        name="王芳",
        title="质量经理",
        expertise=["质量体系管理", "CAPA", "风险管理", "管理评审"],
        personality="全局视角、注重体系",
        focus_areas=["体系有效性", "管理承诺", "资源配置"],
        questioning_style="管理层视角，关注体系运行",
    ),
    AuditRole.DOCUMENT_CONTROL: AgentProfile(
        role=AuditRole.DOCUMENT_CONTROL,
        name="赵静",
        title="文控专员",
        expertise=["文件管理", "记录控制", "变更管理"],
        personality="细致、规范",
        focus_areas=["文件完整性", "记录可追溯性", "变更控制"],
        questioning_style="文件和记录导向，注重细节",
    ),
    AuditRole.DEPARTMENT_REP: AgentProfile(
        role=AuditRole.DEPARTMENT_REP,
        name="刘伟",
        title="部门代表",
        expertise=["部门流程", "日常工作", "实际操作"],
        personality="配合、务实",
        focus_areas=["流程执行", "实际操作", "问题解决"],
        questioning_style="描述性回答，提供实际案例",
    ),
}


@dataclass
class DialogueEntry:
    """A single entry in an audit dialogue."""

    speaker: str
    role: AuditRole
    content: str
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "speaker": self.speaker,
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp,
        }

    def format(self) -> str:
        """Format for display."""
        return f"**{self.speaker}**（{self.role.value}）：\n{self.content}"


@dataclass
class DialogueHistory:
    """History of an audit dialogue."""

    entries: list[DialogueEntry] = field(default_factory=list)

    def add(self, speaker: str, role: AuditRole, content: str, timestamp: str = ""):
        """Add a dialogue entry."""
        self.entries.append(DialogueEntry(
            speaker=speaker,
            role=role,
            content=content,
            timestamp=timestamp,
        ))

    def get_formatted(self) -> str:
        """Get formatted dialogue history."""
        return "\n\n".join(entry.format() for entry in self.entries)

    def to_dict(self) -> dict:
        return {
            "entries": [e.to_dict() for e in self.entries],
        }

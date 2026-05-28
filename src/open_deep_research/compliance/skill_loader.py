"""Load and manage department skill packs for compliance review enhancement."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from open_deep_research.compliance.schemas import SkillPack, SkillStatus


DEFAULT_SKILLS_DIR = Path("data/skills")


class SkillLoader:
    """Load and manage department skill packs from YAML files.

    Skill packs enhance compliance review by providing:
    - Review checklists from experienced auditors
    - Preferred search queries for specific topics
    - Red flags and common false positives to watch for
    - Sample questions for deeper investigation

    Only approved skills are used in formal reviews.
    Draft skills can be used in preview/debug mode.
    """

    def __init__(self, skills: list[SkillPack] | None = None):
        self.skills = skills or []
        self._by_id: dict[str, SkillPack] = {s.skill_id: s for s in self.skills}
        self._by_topic: dict[str, list[SkillPack]] = {}

        for skill in self.skills:
            for topic_id in skill.applies_to_topics:
                if topic_id not in self._by_topic:
                    self._by_topic[topic_id] = []
                self._by_topic[topic_id].append(skill)

    @classmethod
    def from_directory(cls, directory: str | Path | None = None) -> SkillLoader:
        """Load all skill packs from a directory containing .skill.yaml files."""

        skills_dir = Path(directory) if directory else DEFAULT_SKILLS_DIR
        if not skills_dir.exists():
            return cls([])

        skills: list[SkillPack] = []
        for skill_file in skills_dir.glob("*.skill.yaml"):
            try:
                skill = _load_skill_from_yaml(skill_file)
                if skill:
                    skills.append(skill)
            except Exception:
                continue

        return cls(skills)

    def get_skill(self, skill_id: str) -> Optional[SkillPack]:
        """Get a skill by its ID."""

        return self._by_id.get(skill_id)

    def get_skills_for_topic(
        self,
        topic_id: str,
        status_filter: SkillStatus | None = None,
    ) -> list[SkillPack]:
        """Get all skills applicable to a topic.

        Args:
            topic_id: The topic to find skills for
            status_filter: If provided, only return skills with this status.
                          If None, return approved skills by default.
        """

        skills = self._by_topic.get(topic_id, [])
        if status_filter is None:
            status_filter = SkillStatus.APPROVED

        return [s for s in skills if s.status == status_filter]

    def get_approved_skills_for_topic(self, topic_id: str) -> list[SkillPack]:
        """Get approved skills for a topic (used in formal reviews)."""

        return self.get_skills_for_topic(topic_id, SkillStatus.APPROVED)

    def get_draft_skills_for_topic(self, topic_id: str) -> list[SkillPack]:
        """Get draft skills for a topic (used in preview/debug mode)."""

        return self.get_skills_for_topic(topic_id, SkillStatus.DRAFT)

    def get_all_approved(self) -> list[SkillPack]:
        """Get all approved skills."""

        return [s for s in self.skills if s.status == SkillStatus.APPROVED]

    def get_all_draft(self) -> list[SkillPack]:
        """Get all draft skills."""

        return [s for s in self.skills if s.status == SkillStatus.DRAFT]

    def merge_skill_insights(
        self,
        topic_id: str,
        include_draft: bool = False,
    ) -> dict[str, list[str]]:
        """Merge insights from all applicable skills for a topic.

        Returns a dictionary with merged lists of:
        - review_checklist
        - preferred_queries
        - expected_evidence
        - red_flags
        - common_false_positives
        - sample_questions
        """

        skills = self.get_approved_skills_for_topic(topic_id)
        if include_draft:
            skills.extend(self.get_draft_skills_for_topic(topic_id))

        merged = {
            "review_checklist": [],
            "preferred_queries": [],
            "expected_evidence": [],
            "red_flags": [],
            "common_false_positives": [],
            "sample_questions": [],
        }

        for skill in skills:
            for key in merged:
                items = getattr(skill, key, [])
                merged[key].extend(items)

        for key in merged:
            merged[key] = list(dict.fromkeys(merged[key]))

        return merged

    def approve_skill(self, skill_id: str, approved_by: str) -> bool:
        """Approve a draft skill. Returns True if successful."""

        skill = self.get_skill(skill_id)
        if not skill or skill.status != SkillStatus.DRAFT:
            return False

        skill.status = SkillStatus.APPROVED
        skill.approved_by = approved_by
        return True

    def deprecate_skill(self, skill_id: str) -> bool:
        """Deprecate a skill. Returns True if successful."""

        skill = self.get_skill(skill_id)
        if not skill:
            return False

        skill.status = SkillStatus.DEPRECATED
        return True

    def get_statistics(self) -> dict[str, int]:
        """Get statistics about loaded skills."""

        stats = {
            "total_skills": len(self.skills),
            "approved": len(self.get_all_approved()),
            "draft": len(self.get_all_draft()),
            "deprecated": len([s for s in self.skills if s.status == SkillStatus.DEPRECATED]),
        }

        topics_covered = set()
        for skill in self.skills:
            topics_covered.update(skill.applies_to_topics)
        stats["topics_covered"] = len(topics_covered)

        return stats


def _load_skill_from_yaml(path: Path) -> Optional[SkillPack]:
    """Load a skill pack from a YAML file."""

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or not isinstance(data, dict):
        return None

    required_fields = ["skill_id", "owner", "department"]
    for field in required_fields:
        if field not in data:
            return None

    status_str = data.get("status", "draft")
    try:
        status = SkillStatus(status_str)
    except ValueError:
        status = SkillStatus.DRAFT

    return SkillPack(
        skill_id=data["skill_id"],
        owner=data["owner"],
        department=data["department"],
        version=data.get("version", "1.0"),
        status=status,
        applies_to_topics=data.get("applies_to_topics", []),
        review_checklist=data.get("review_checklist", []),
        preferred_queries=data.get("preferred_queries", []),
        expected_evidence=data.get("expected_evidence", []),
        red_flags=data.get("red_flags", []),
        common_false_positives=data.get("common_false_positives", []),
        sample_questions=data.get("sample_questions", []),
        approved_by=data.get("approved_by"),
        updated_at=data.get("updated_at", ""),
    )


def save_skill_to_yaml(skill: SkillPack, directory: str | Path | None = None) -> Path:
    """Save a skill pack to a YAML file."""

    skills_dir = Path(directory) if directory else DEFAULT_SKILLS_DIR
    skills_dir.mkdir(parents=True, exist_ok=True)

    file_path = skills_dir / f"{skill.skill_id}.skill.yaml"

    data = skill.model_dump()
    data["status"] = skill.status.value

    with file_path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    return file_path


def create_capa_skill() -> SkillPack:
    """Create a sample CAPA review skill pack based on common audit experience."""

    return SkillPack(
        skill_id="capa_review",
        owner="Quality Department",
        department="Quality Assurance",
        version="1.0",
        status=SkillStatus.DRAFT,
        applies_to_topics=["capa"],
        review_checklist=[
            "检查CAPA程序是否定义了问题来源",
            "验证根因分析方法是否适当",
            "确认纠正/预防措施是否针对根本原因",
            "检查有效性验证的时间和方法",
            "确认CAPA关闭前的所有证据完整性",
            "检查是否有重复发生的类似问题",
            "验证CAPA的优先级和风险评估",
        ],
        preferred_queries=[
            "CAPA procedure root cause analysis",
            "CAPA effectiveness verification",
            "CAPA closure record",
            "Q-Gate CAPA review",
            "CAPA overdue status",
        ],
        expected_evidence=[
            "CAPA程序文件",
            "根因分析记录（如5-Why、鱼骨图）",
            "纠正/预防措施计划",
            "措施实施证据",
            "有效性验证记录",
            "CAPA关闭批准",
        ],
        red_flags=[
            "无根因分析或分析过于简单",
            "措施与根因不对应",
            "有效性验证缺失或形式化",
            "CAPA长期未关闭",
            "重复发生的同类问题",
            "无责任人或期限",
        ],
        common_false_positives=[
            "有CAPA程序不等于CAPA执行有效",
            "有root cause不等于有效性验证充分",
            "CAPA已关闭不等于问题真正解决",
        ],
        sample_questions=[
            "最近一次CAPA有效性验证是什么时候？",
            "是否有超过90天未关闭的CAPA？",
            "过去一年是否有重复发生的同类不符合项？",
            "CAPA的根因分析使用了什么方法？",
        ],
    )


def create_internal_audit_skill() -> SkillPack:
    """Create a sample internal audit review skill pack."""

    return SkillPack(
        skill_id="internal_audit_review",
        owner="Quality Department",
        department="Quality Assurance",
        version="1.0",
        status=SkillStatus.DRAFT,
        applies_to_topics=["internal_audit"],
        review_checklist=[
            "检查审核方案是否覆盖所有QMS过程",
            "验证审核频率是否符合要求",
            "确认审核员资质和独立性",
            "检查审核计划的完整性和审批",
            "验证审核报告的不符合项描述",
            "确认纠正措施的跟踪和验证",
            "检查管理评审的输入",
        ],
        preferred_queries=[
            "internal audit program plan",
            "audit schedule annual",
            "auditor qualification training",
            "audit report nonconformity",
            "corrective action verification",
        ],
        expected_evidence=[
            "年度审核方案",
            "审核计划",
            "审核员资质记录",
            "审核报告",
            "不符合项报告",
            "纠正措施验证记录",
        ],
        red_flags=[
            "审核方案未覆盖所有过程",
            "审核员审核自己的工作",
            "不符合项描述不具体",
            "纠正措施未验证有效性",
            "审核频率不足",
        ],
        common_false_positives=[
            "有审核方案不等于审核执行到位",
            "有审核报告不等于不符合项已关闭",
        ],
        sample_questions=[
            "本年度审核方案覆盖了哪些过程？",
            "审核员是否接受了审核培训？",
            "最近一次审核发现了多少不符合项？",
            "不符合项的关闭率是多少？",
        ],
    )

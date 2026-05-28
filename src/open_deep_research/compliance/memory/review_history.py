"""Review history memory for tracking audit sessions over time."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from open_deep_research.compliance.schemas import ClauseAssessment, ReviewStatus


@dataclass
class ReviewSession:
    """A single review session record."""

    session_id: str
    timestamp: str
    request: str
    assessments: list[dict]
    confirmed_by: Optional[str] = None
    notes: str = ""
    status: str = "pending"  # pending, confirmed, rejected

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> ReviewSession:
        return cls(**data)


@dataclass
class ClauseHistory:
    """History of assessments for a specific clause."""

    clause_id: str
    standard: str
    assessments: list[dict] = field(default_factory=list)

    def add_assessment(self, session_id: str, timestamp: str,
                      assessment: ClauseAssessment):
        """Add a new assessment to history."""
        self.assessments.append({
            "session_id": session_id,
            "timestamp": timestamp,
            "status": assessment.status,
            "rationale": assessment.rationale,
            "evidence_count": len(assessment.evidence),
            "risk": assessment.risk,
            "recommendation": assessment.recommendation,
        })

    def get_latest_status(self) -> Optional[ReviewStatus]:
        """Get the most recent assessment status."""
        if not self.assessments:
            return None
        return self.assessments[-1].get("status")

    def get_status_trend(self) -> str:
        """Analyze status trend over time."""
        if len(self.assessments) < 2:
            return "insufficient_data"

        statuses = [a["status"] for a in self.assessments]
        status_values = {
            "符合": 3,
            "需澄清": 2,
            "缺乏证据": 1,
            "未提及": 0,
        }

        values = [status_values.get(s, 0) for s in statuses]

        # Calculate trend
        if values[-1] > values[0]:
            return "improving"
        elif values[-1] < values[0]:
            return "declining"
        else:
            return "stable"


@dataclass
class TrendAnalysis:
    """Trend analysis for a clause."""

    clause_id: str
    standard: str
    total_assessments: int
    latest_status: Optional[str]
    trend: str  # improving, stable, declining, insufficient_data
    status_history: list[dict]
    improvement_notes: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


class ReviewHistory:
    """Review history memory for tracking audit sessions."""

    def __init__(self, storage_path: str | Path = "data/memory/review_history.json"):
        self.storage_path = Path(storage_path)
        self.sessions: list[ReviewSession] = []
        self.clause_histories: dict[str, ClauseHistory] = {}
        self._load()

    def _load(self):
        """Load history from storage."""
        if not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, encoding="utf-8") as f:
                data = json.load(f)

            # Load sessions
            for session_data in data.get("sessions", []):
                self.sessions.append(ReviewSession.from_dict(session_data))

            # Load clause histories
            for clause_id, history_data in data.get("clause_histories", {}).items():
                history = ClauseHistory(
                    clause_id=history_data["clause_id"],
                    standard=history_data["standard"],
                    assessments=history_data["assessments"],
                )
                self.clause_histories[clause_id] = history

        except (json.JSONDecodeError, KeyError):
            pass

    def _save(self):
        """Save history to storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "sessions": [s.to_dict() for s in self.sessions],
            "clause_histories": {
                cid: {
                    "clause_id": h.clause_id,
                    "standard": h.standard,
                    "assessments": h.assessments,
                }
                for cid, h in self.clause_histories.items()
            },
        }

        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def save_session(self, session: ReviewSession,
                    assessments: list[ClauseAssessment]):
        """Save a review session and update clause histories."""
        # Add session
        self.sessions.append(session)

        # Update clause histories
        for assessment in assessments:
            key = f"{assessment.standard}::{assessment.clause_id}"
            if key not in self.clause_histories:
                self.clause_histories[key] = ClauseHistory(
                    clause_id=assessment.clause_id,
                    standard=assessment.standard,
                )
            self.clause_histories[key].add_assessment(
                session.session_id,
                session.timestamp,
                assessment,
            )

        self._save()

    def get_clause_history(self, clause_id: str,
                          standard: str = "ISO 13485:2016") -> Optional[ClauseHistory]:
        """Get history for a specific clause."""
        key = f"{standard}::{clause_id}"
        return self.clause_histories.get(key)

    def get_clause_trend(self, clause_id: str,
                        standard: str = "ISO 13485:2016") -> TrendAnalysis:
        """Get trend analysis for a clause."""
        history = self.get_clause_history(clause_id, standard)

        if not history:
            return TrendAnalysis(
                clause_id=clause_id,
                standard=standard,
                total_assessments=0,
                latest_status=None,
                trend="no_history",
                status_history=[],
                improvement_notes=[],
            )

        return TrendAnalysis(
            clause_id=clause_id,
            standard=standard,
            total_assessments=len(history.assessments),
            latest_status=history.get_latest_status(),
            trend=history.get_status_trend(),
            status_history=history.assessments,
            improvement_notes=self._extract_improvement_notes(history),
        )

    def _extract_improvement_notes(self, history: ClauseHistory) -> list[str]:
        """Extract improvement notes from history."""
        notes = []
        for assessment in history.assessments:
            if assessment.get("recommendation"):
                notes.append(assessment["recommendation"])
        return notes[-5:]  # Return last 5 recommendations

    def get_recent_sessions(self, limit: int = 10) -> list[ReviewSession]:
        """Get recent review sessions."""
        return sorted(
            self.sessions,
            key=lambda s: s.timestamp,
            reverse=True
        )[:limit]

    def get_problematic_clauses(self, threshold: int = 2) -> list[dict]:
        """Get clauses that have been flagged multiple times."""
        problematic = []

        for key, history in self.clause_histories.items():
            non_compliant_count = sum(
                1 for a in history.assessments
                if a.get("status") in ("需澄清", "缺乏证据", "未提及")
            )

            if non_compliant_count >= threshold:
                problematic.append({
                    "clause_id": history.clause_id,
                    "standard": history.standard,
                    "non_compliant_count": non_compliant_count,
                    "latest_status": history.get_latest_status(),
                    "trend": history.get_status_trend(),
                })

        return sorted(
            problematic,
            key=lambda x: x["non_compliant_count"],
            reverse=True,
        )

    def generate_summary_report(self) -> str:
        """Generate a summary report of review history."""
        lines = ["# 审查历史总结报告", ""]
        lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Overall statistics
        lines.append("## 总体统计")
        lines.append(f"- 总审查会话数：{len(self.sessions)}")
        lines.append(f"- 跟踪条款数：{len(self.clause_histories)}")
        lines.append("")

        # Problematic clauses
        problematic = self.get_problematic_clauses()
        if problematic:
            lines.append("## 需要关注的条款")
            lines.append("| 条款 | 标准 | 不符合次数 | 最新状态 | 趋势 |")
            lines.append("|------|------|------------|----------|------|")
            for clause in problematic:
                lines.append(
                    f"| {clause['clause_id']} | {clause['standard']} | "
                    f"{clause['non_compliant_count']} | {clause['latest_status']} | "
                    f"{clause['trend']} |"
                )
            lines.append("")

        # Recent sessions
        recent = self.get_recent_sessions(5)
        if recent:
            lines.append("## 最近审查会话")
            for session in recent:
                lines.append(f"- {session.timestamp}: {session.request[:50]}...")
            lines.append("")

        return "\n".join(lines)

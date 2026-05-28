"""Audit memory system for compliance review persistence and learning."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from open_deep_research.compliance.schemas import (
    HumanFeedback,
    ReviewFinding,
    ReviewRun,
)


DEFAULT_MEMORY_DIR = Path("data/review_memory")


class ReviewMemory:
    """Persistent memory system for compliance review runs and human feedback.

    Stores:
    - Review runs with findings
    - Human feedback on findings (accept/reject/modify)
    - Retrieval feedback for query tuning
    - Clause overrides from human review
    - Action followups and closure status

    Important: Only human-approved memory can influence future reviews.
    Model outputs are not automatically stored as facts.
    """

    def __init__(self, memory_dir: str | Path | None = None):
        self.memory_dir = Path(memory_dir) if memory_dir else DEFAULT_MEMORY_DIR
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self.runs_file = self.memory_dir / "review_runs.jsonl"
        self.feedback_file = self.memory_dir / "human_feedback.jsonl"
        self.retrieval_feedback_file = self.memory_dir / "retrieval_feedback.jsonl"
        self.clause_overrides_file = self.memory_dir / "clause_overrides.jsonl"
        self.action_followups_file = self.memory_dir / "action_followups.jsonl"

    def save_run(self, run: ReviewRun) -> None:
        """Save a review run to memory."""

        if not run.run_id:
            run.run_id = str(uuid.uuid4())
        if not run.created_at:
            run.created_at = datetime.now().isoformat()

        _append_jsonl(self.runs_file, run.model_dump())

    def get_run(self, run_id: str) -> Optional[ReviewRun]:
        """Get a review run by ID."""

        for data in _read_jsonl(self.runs_file):
            if data.get("run_id") == run_id:
                return ReviewRun.model_validate(data)
        return None

    def get_recent_runs(self, limit: int = 10) -> list[ReviewRun]:
        """Get recent review runs."""

        runs = []
        for data in _read_jsonl(self.runs_file):
            try:
                runs.append(ReviewRun.model_validate(data))
            except Exception:
                continue

        runs.sort(key=lambda r: r.created_at, reverse=True)
        return runs[:limit]

    def get_runs_by_topic(self, topic_id: str) -> list[ReviewRun]:
        """Get all review runs that reviewed a specific topic."""

        runs = []
        for data in _read_jsonl(self.runs_file):
            try:
                run = ReviewRun.model_validate(data)
                if topic_id in run.topics_reviewed:
                    runs.append(run)
            except Exception:
                continue
        return runs

    def save_feedback(self, feedback: HumanFeedback) -> None:
        """Save human feedback on a finding."""

        if not feedback.feedback_id:
            feedback.feedback_id = str(uuid.uuid4())
        if not feedback.created_at:
            feedback.created_at = datetime.now().isoformat()

        _append_jsonl(self.feedback_file, feedback.model_dump())

    def get_feedback_for_run(self, run_id: str) -> list[HumanFeedback]:
        """Get all human feedback for a specific run."""

        feedbacks = []
        for data in _read_jsonl(self.feedback_file):
            if data.get("run_id") == run_id:
                try:
                    feedbacks.append(HumanFeedback.model_validate(data))
                except Exception:
                    continue
        return feedbacks

    def get_feedback_for_finding(self, finding_id: str) -> list[HumanFeedback]:
        """Get all human feedback for a specific finding."""

        feedbacks = []
        for data in _read_jsonl(self.feedback_file):
            if data.get("finding_id") == finding_id:
                try:
                    feedbacks.append(HumanFeedback.model_validate(data))
                except Exception:
                    continue
        return feedbacks

    def get_approved_findings_for_clause(
        self,
        standard: str,
        clause_id: str,
    ) -> list[tuple[ReviewFinding, HumanFeedback]]:
        """Get human-approved findings for a specific clause.

        Returns list of (finding, feedback) tuples where the feedback is an approval.
        """

        results: list[tuple[ReviewFinding, HumanFeedback]] = []

        for data in _read_jsonl(self.feedback_file):
            try:
                feedback = HumanFeedback.model_validate(data)
                if feedback.action != "accept":
                    continue

                run = self.get_run(feedback.run_id)
                if not run:
                    continue

                for finding in run.findings:
                    if finding.clause_id == f"{standard} {clause_id}":
                        results.append((finding, feedback))
            except Exception:
                continue

        return results

    def save_retrieval_feedback(
        self,
        topic_id: str,
        query: str,
        helpful_evidence_ids: list[str],
        unhelpful_evidence_ids: list[str],
        comment: str = "",
    ) -> None:
        """Save feedback on retrieval quality for query tuning."""

        data = {
            "feedback_id": str(uuid.uuid4()),
            "topic_id": topic_id,
            "query": query,
            "helpful_evidence_ids": helpful_evidence_ids,
            "unhelpful_evidence_ids": unhelpful_evidence_ids,
            "comment": comment,
            "created_at": datetime.now().isoformat(),
        }
        _append_jsonl(self.retrieval_feedback_file, data)

    def get_retrieval_feedback_for_topic(self, topic_id: str) -> list[dict]:
        """Get retrieval feedback for a specific topic."""

        feedbacks = []
        for data in _read_jsonl(self.retrieval_feedback_file):
            if data.get("topic_id") == topic_id:
                feedbacks.append(data)
        return feedbacks

    def save_clause_override(
        self,
        standard: str,
        clause_id: str,
        original_status: str,
        corrected_status: str,
        reason: str,
        approved_by: str,
    ) -> None:
        """Save a human override of a clause assessment."""

        data = {
            "override_id": str(uuid.uuid4()),
            "standard": standard,
            "clause_id": clause_id,
            "original_status": original_status,
            "corrected_status": corrected_status,
            "reason": reason,
            "approved_by": approved_by,
            "created_at": datetime.now().isoformat(),
        }
        _append_jsonl(self.clause_overrides_file, data)

    def get_clause_overrides(
        self,
        standard: str | None = None,
        clause_id: str | None = None,
    ) -> list[dict]:
        """Get clause overrides, optionally filtered."""

        overrides = []
        for data in _read_jsonl(self.clause_overrides_file):
            if standard and data.get("standard") != standard:
                continue
            if clause_id and data.get("clause_id") != clause_id:
                continue
            overrides.append(data)
        return overrides

    def save_action_followup(
        self,
        run_id: str,
        finding_id: str,
        action_description: str,
        responsible_person: str,
        due_date: str,
    ) -> str:
        """Save an action followup for tracking."""

        followup_id = str(uuid.uuid4())
        data = {
            "followup_id": followup_id,
            "run_id": run_id,
            "finding_id": finding_id,
            "action_description": action_description,
            "responsible_person": responsible_person,
            "due_date": due_date,
            "status": "open",
            "created_at": datetime.now().isoformat(),
            "closed_at": None,
            "closure_evidence": None,
        }
        _append_jsonl(self.action_followups_file, data)
        return followup_id

    def close_action_followup(
        self,
        followup_id: str,
        closure_evidence: str = "",
    ) -> bool:
        """Close an action followup."""

        followups = list(_read_jsonl(self.action_followups_file))
        updated = False

        for data in followups:
            if data.get("followup_id") == followup_id:
                data["status"] = "closed"
                data["closed_at"] = datetime.now().isoformat()
                data["closure_evidence"] = closure_evidence
                updated = True
                break

        if updated:
            _write_jsonl(self.action_followups_file, followups)

        return updated

    def get_open_followups(self, run_id: str | None = None) -> list[dict]:
        """Get open action followups."""

        followups = []
        for data in _read_jsonl(self.action_followups_file):
            if data.get("status") != "open":
                continue
            if run_id and data.get("run_id") != run_id:
                continue
            followups.append(data)
        return followups

    def get_similar_findings(
        self,
        topic_id: str,
        limit: int = 5,
    ) -> list[ReviewFinding]:
        """Get similar past findings for a topic (for reference, not auto-approval)."""

        findings: list[ReviewFinding] = []
        for run in self.get_runs_by_topic(topic_id):
            for finding in run.findings:
                if finding.topic_id == topic_id:
                    findings.append(finding)

        return findings[:limit]

    def get_statistics(self) -> dict[str, int]:
        """Get statistics about the memory store."""

        stats = {
            "total_runs": sum(1 for _ in _read_jsonl(self.runs_file)),
            "total_feedback": sum(1 for _ in _read_jsonl(self.feedback_file)),
            "total_retrieval_feedback": sum(1 for _ in _read_jsonl(self.retrieval_feedback_file)),
            "total_overrides": sum(1 for _ in _read_jsonl(self.clause_overrides_file)),
            "total_followups": sum(1 for _ in _read_jsonl(self.action_followups_file)),
            "open_followups": sum(
                1 for data in _read_jsonl(self.action_followups_file)
                if data.get("status") == "open"
            ),
        }
        return stats


def _append_jsonl(path: Path, data: dict) -> None:
    """Append a JSON object to a JSONL file."""

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    """Read all objects from a JSONL file."""

    if not path.exists():
        return []

    objects = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    objects.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return objects


def _write_jsonl(path: Path, objects: list[dict]) -> None:
    """Write objects to a JSONL file (overwrite)."""

    with path.open("w", encoding="utf-8") as f:
        for obj in objects:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

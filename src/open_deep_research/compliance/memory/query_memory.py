"""Query optimization memory for improving retrieval quality over time."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class QueryFeedback:
    """Feedback on a query's effectiveness."""

    query: str
    clause_id: str
    relevant: bool
    feedback: str
    timestamp: str
    retrieved_files: list[str] = field(default_factory=list)
    expected_files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> QueryFeedback:
        return cls(**data)


@dataclass
class ClauseQueryProfile:
    """Optimized query profile for a clause."""

    clause_id: str
    standard: str
    optimized_queries: list[str] = field(default_factory=list)
    synonyms: dict[str, list[str]] = field(default_factory=dict)
    negative_terms: list[str] = field(default_factory=list)
    feedback_history: list[dict] = field(default_factory=list)
    success_rate: float = 0.0
    last_updated: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> ClauseQueryProfile:
        return cls(**data)


class QueryMemory:
    """Query optimization memory for improving retrieval quality."""

    def __init__(self, storage_path: str | Path = "data/memory/query_memory.json"):
        self.storage_path = Path(storage_path)
        self.clause_profiles: dict[str, ClauseQueryProfile] = {}
        self.global_synonyms: dict[str, list[str]] = {}
        self._load()

    def _load(self):
        """Load query memory from storage."""
        if not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, encoding="utf-8") as f:
                data = json.load(f)

            # Load clause profiles
            for clause_id, profile_data in data.get("clause_profiles", {}).items():
                self.clause_profiles[clause_id] = ClauseQueryProfile.from_dict(
                    profile_data
                )

            # Load global synonyms
            self.global_synonyms = data.get("global_synonyms", {})

        except (json.JSONDecodeError, KeyError):
            pass

    def _save(self):
        """Save query memory to storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "clause_profiles": {
                cid: profile.to_dict()
                for cid, profile in self.clause_profiles.items()
            },
            "global_synonyms": self.global_synonyms,
        }

        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _get_or_create_profile(self, clause_id: str,
                              standard: str = "ISO 13485:2016") -> ClauseQueryProfile:
        """Get or create a clause query profile."""
        if clause_id not in self.clause_profiles:
            self.clause_profiles[clause_id] = ClauseQueryProfile(
                clause_id=clause_id,
                standard=standard,
            )
        return self.clause_profiles[clause_id]

    def record_feedback(self, query: str, clause_id: str,
                       relevant: bool, feedback: str = "",
                       retrieved_files: list[str] = None,
                       expected_files: list[str] = None,
                       standard: str = "ISO 13485:2016"):
        """Record feedback on a query's effectiveness."""
        profile = self._get_or_create_profile(clause_id, standard)

        feedback_record = QueryFeedback(
            query=query,
            clause_id=clause_id,
            relevant=relevant,
            feedback=feedback,
            timestamp=datetime.now().isoformat(),
            retrieved_files=retrieved_files or [],
            expected_files=expected_files or [],
        )

        profile.feedback_history.append(feedback_record.to_dict())
        profile.last_updated = datetime.now().isoformat()

        # Update success rate
        total = len(profile.feedback_history)
        successful = sum(1 for f in profile.feedback_history if f.get("relevant"))
        profile.success_rate = successful / total if total > 0 else 0.0

        # If query was successful, add to optimized queries
        if relevant and query not in profile.optimized_queries:
            profile.optimized_queries.append(query)

        # Extract synonyms from feedback
        if not relevant and expected_files:
            self._extract_synonyms_from_feedback(profile, query, expected_files)

        self._save()

    def _extract_synonyms_from_feedback(self, profile: ClauseQueryProfile,
                                        query: str,
                                        expected_files: list[str]):
        """Extract potential synonyms from negative feedback."""
        # This is a simplified version - in production, you might use
        # more sophisticated NLP techniques
        query_terms = set(query.lower().split())

        # Look for terms in expected files that might be related
        for file_name in expected_files:
            file_terms = set(file_name.lower().replace("_", " ").split())
            new_terms = file_terms - query_terms

            for term in new_terms:
                if len(term) > 2:  # Skip short terms
                    if term not in profile.synonyms:
                        profile.synonyms[term] = []
                    if query not in profile.synonyms[term]:
                        profile.synonyms[term].append(query)

    def get_optimized_query(self, clause_id: str,
                           base_query: str = "") -> str:
        """Get optimized query for a clause."""
        profile = self.clause_profiles.get(clause_id)
        if not profile:
            return base_query

        # If we have optimized queries, use the best one
        if profile.optimized_queries:
            # Return the most recent optimized query
            return profile.optimized_queries[-1]

        # Otherwise, enhance base query with synonyms
        if base_query:
            enhanced_terms = [base_query]
            for term, synonyms in profile.synonyms.items():
                if term in base_query.lower():
                    enhanced_terms.extend(synonyms[:2])  # Add top 2 synonyms
            return " ".join(enhanced_terms)

        return base_query

    def get_synonyms(self, term: str,
                    clause_id: str = None) -> list[str]:
        """Get synonyms for a term."""
        synonyms = set()

        # Check clause-specific synonyms
        if clause_id:
            profile = self.clause_profiles.get(clause_id)
            if profile and term in profile.synonyms:
                synonyms.update(profile.synonyms[term])

        # Check global synonyms
        if term in self.global_synonyms:
            synonyms.update(self.global_synonyms[term])

        return list(synonyms)

    def add_global_synonym(self, term: str, synonym: str):
        """Add a global synonym mapping."""
        if term not in self.global_synonyms:
            self.global_synonyms[term] = []
        if synonym not in self.global_synonyms[term]:
            self.global_synonyms[term].append(synonym)
        self._save()

    def get_clause_statistics(self, clause_id: str) -> dict:
        """Get statistics for a clause's query performance."""
        profile = self.clause_profiles.get(clause_id)
        if not profile:
            return {"clause_id": clause_id, "no_data": True}

        return {
            "clause_id": clause_id,
            "standard": profile.standard,
            "total_queries": len(profile.feedback_history),
            "success_rate": profile.success_rate,
            "optimized_queries_count": len(profile.optimized_queries),
            "synonyms_count": len(profile.synonyms),
            "last_updated": profile.last_updated,
        }

    def get_problematic_queries(self, threshold: float = 0.5) -> list[dict]:
        """Get queries with low success rate."""
        problematic = []

        for clause_id, profile in self.clause_profiles.items():
            if (len(profile.feedback_history) >= 3 and
                profile.success_rate < threshold):
                problematic.append({
                    "clause_id": clause_id,
                    "standard": profile.standard,
                    "success_rate": profile.success_rate,
                    "total_queries": len(profile.feedback_history),
                    "suggestion": self._generate_improvement_suggestion(profile),
                })

        return sorted(problematic, key=lambda x: x["success_rate"])

    def _generate_improvement_suggestion(self,
                                        profile: ClauseQueryProfile) -> str:
        """Generate improvement suggestion for a clause."""
        suggestions = []

        if not profile.optimized_queries:
            suggestions.append("需要添加优化后的查询")

        if not profile.synonyms:
            suggestions.append("需要添加术语同义词")

        # Analyze feedback for patterns
        negative_feedback = [
            f for f in profile.feedback_history
            if not f.get("relevant")
        ]
        if negative_feedback:
            suggestions.append(f"有{len(negative_feedback)}次无效查询需要分析")

        return "; ".join(suggestions) if suggestions else "需要更多反馈数据"

    def generate_report(self) -> str:
        """Generate query memory report."""
        lines = ["# 查询优化记忆报告", ""]
        lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Overall statistics
        total_clauses = len(self.clause_profiles)
        total_queries = sum(
            len(p.feedback_history) for p in self.clause_profiles.values()
        )
        avg_success = 0
        if total_clauses > 0:
            avg_success = sum(
                p.success_rate for p in self.clause_profiles.values()
            ) / total_clauses

        lines.append("## 总体统计")
        lines.append(f"- 跟踪条款数：{total_clauses}")
        lines.append(f"- 总查询数：{total_queries}")
        lines.append(f"- 平均成功率：{avg_success:.1%}")
        lines.append("")

        # Problematic queries
        problematic = self.get_problematic_queries()
        if problematic:
            lines.append("## 需要优化的查询")
            lines.append("| 条款 | 成功率 | 查询次数 | 建议 |")
            lines.append("|------|--------|----------|------|")
            for item in problematic:
                lines.append(
                    f"| {item['clause_id']} | {item['success_rate']:.1%} | "
                    f"{item['total_queries']} | {item['suggestion']} |"
                )
            lines.append("")

        # Top performing clauses
        top_clauses = sorted(
            self.clause_profiles.values(),
            key=lambda p: p.success_rate,
            reverse=True
        )[:5]
        if top_clauses:
            lines.append("## 表现最好的条款")
            lines.append("| 条款 | 成功率 | 优化查询数 | 同义词数 |")
            lines.append("|------|--------|------------|----------|")
            for profile in top_clauses:
                lines.append(
                    f"| {profile.clause_id} | {profile.success_rate:.1%} | "
                    f"{len(profile.optimized_queries)} | {len(profile.synonyms)} |"
                )
            lines.append("")

        return "\n".join(lines)

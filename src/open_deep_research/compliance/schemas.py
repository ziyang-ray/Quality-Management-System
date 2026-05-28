"""Schemas for compliance document indexing and review outputs."""

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


SourceType = Literal["standard", "internal", "unknown"]
ReviewStatus = Literal["符合", "需澄清", "缺乏证据", "未提及"]


class ParsedDocumentElement(BaseModel):
    """A text-bearing unit extracted from a source document."""

    source_type: SourceType = "unknown"
    path: str
    file_name: str
    extension: str
    text: str
    page_number: Optional[int] = None
    sheet_name: Optional[str] = None
    row_range: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentChunk(BaseModel):
    """A searchable chunk with traceable source metadata."""

    chunk_id: str
    source_type: SourceType
    path: str
    file_name: str
    extension: str
    text: str
    page_number: Optional[int] = None
    sheet_name: Optional[str] = None
    row_range: Optional[str] = None
    section_hint: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IndexMetadata(BaseModel):
    """Summary of a built compliance index."""

    total_files_seen: int = 0
    total_files_indexed: int = 0
    total_chunks: int = 0
    skipped_files: list[dict[str, str]] = Field(default_factory=list)
    source_roots: dict[str, str] = Field(default_factory=dict)


class EvidenceItem(BaseModel):
    """A source excerpt used as evidence for a compliance judgment."""

    evidence_id: str = ""
    file_name: str = ""
    path: str = ""
    excerpt: str = ""
    source_type: SourceType = "unknown"
    page_number: Optional[int] = None
    sheet_name: Optional[str] = None
    row_range: Optional[str] = None
    score: Optional[float] = None


class StandardClause(BaseModel):
    """A structured standard clause extracted from an official standard."""

    standard: str
    clause_id: str
    title: str
    text: str
    requirement_summary: str = ""
    expected_evidence: list[str] = Field(default_factory=list)
    search_terms: list[str] = Field(default_factory=list)
    source_path: str
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    extraction_status: str = "candidate"


class ClauseAssessment(BaseModel):
    """Assessment of one standard requirement against internal evidence."""

    topic_id: str = ""
    topic_title: str = ""
    standard: str
    clause_id: str
    requirement_summary: str
    status: ReviewStatus
    rationale: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    risk: str = ""
    recommendation: str = ""


class ComplianceReviewReport(BaseModel):
    """Structured final report for a compliance review run."""

    review_scope: str
    overall_risk_level: Literal["低", "中", "高", "证据不足"] = "证据不足"
    overall_summary: str
    assessments: list[ClauseAssessment] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class EvidencePackage(BaseModel):
    """Structured evidence package for a review topic."""

    topic_id: str
    topic_title: str
    expected_evidence: str
    standard_clauses: list[StandardClause] = Field(default_factory=list)
    internal_evidence: list[EvidenceItem] = Field(default_factory=list)
    standard_evidence: list[EvidenceItem] = Field(default_factory=list)
    skill_insights: list[str] = Field(default_factory=list)
    kg_related_files: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ReviewFinding(BaseModel):
    """A specific finding from a compliance review."""

    finding_id: str = ""
    topic_id: str = ""
    clause_id: str = ""
    status: ReviewStatus
    risk_level: Literal["低", "中", "高"] = "中"
    description: str
    evidence_ids: list[str] = Field(default_factory=list)
    recommendation: str = ""
    human_feedback: Optional[str] = None
    human_approved: bool = False


class ReviewRun(BaseModel):
    """Metadata for a compliance review run."""

    run_id: str
    review_request: str
    topics_reviewed: list[str] = Field(default_factory=list)
    findings: list[ReviewFinding] = Field(default_factory=list)
    overall_risk_level: str = "证据不足"
    human_feedback: Optional[str] = None
    created_at: str = ""
    completed_at: Optional[str] = None


class HumanFeedback(BaseModel):
    """Human feedback on a review finding."""

    feedback_id: str = ""
    run_id: str
    finding_id: str
    action: Literal["accept", "reject", "modify"] = "accept"
    original_status: ReviewStatus
    corrected_status: Optional[ReviewStatus] = None
    comment: str = ""
    approved_by: str = ""
    created_at: str = ""


class KnowledgeNode(BaseModel):
    """A node in the compliance knowledge graph."""

    node_id: str
    node_type: Literal["clause", "process", "procedure", "record", "department", "risk", "control"]
    label: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeEdge(BaseModel):
    """An edge in the compliance knowledge graph."""

    edge_id: str = ""
    source_id: str
    target_id: str
    relation_type: str  # requires, applies_to, controlled_by, produces, owned_by, mitigated_by, supports
    metadata: dict[str, Any] = Field(default_factory=dict)


class SkillStatus(str, Enum):
    """Status of a department skill pack."""

    DRAFT = "draft"
    APPROVED = "approved"
    DEPRECATED = "deprecated"


class SkillPack(BaseModel):
    """A department skill pack for enhancing compliance review."""

    skill_id: str
    owner: str
    department: str
    version: str = "1.0"
    status: SkillStatus = SkillStatus.DRAFT
    applies_to_topics: list[str] = Field(default_factory=list)
    review_checklist: list[str] = Field(default_factory=list)
    preferred_queries: list[str] = Field(default_factory=list)
    expected_evidence: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    common_false_positives: list[str] = Field(default_factory=list)
    sample_questions: list[str] = Field(default_factory=list)
    approved_by: Optional[str] = None
    updated_at: str = ""


class EvidenceSearchPlan(BaseModel):
    """A plan for evidence retrieval enhanced by skills and knowledge graph."""

    topic_id: str
    base_query: str
    clause_search_terms: list[str] = Field(default_factory=list)
    kg_expanded_terms: list[str] = Field(default_factory=list)
    skill_expanded_terms: list[str] = Field(default_factory=list)
    red_flags_to_check: list[str] = Field(default_factory=list)
    priority_files: list[str] = Field(default_factory=list)

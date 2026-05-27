"""Schemas for compliance document indexing and review outputs."""

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

    file_name: str
    path: str
    excerpt: str
    source_type: SourceType
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
    overall_summary: str
    assessments: list[ClauseAssessment] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

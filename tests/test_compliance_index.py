from pathlib import Path

from langchain_core.messages import HumanMessage

from open_deep_research.compliance.chunking import chunk_elements
from open_deep_research.compliance.clause_store import ClauseStore, clause_file_for_index
from open_deep_research.compliance.document_loader import iter_source_files
from open_deep_research.compliance.index_store import read_chunks, write_index
from open_deep_research.compliance.prompts import format_evidence_block
from open_deep_research.compliance.renderers import render_compliance_review_report
from open_deep_research.compliance.retrieval import ComplianceRetriever
from open_deep_research.compliance.review_topics import select_review_topics
from open_deep_research.compliance.schemas import (
    ClauseAssessment,
    ComplianceReviewReport,
    EvidenceItem,
    IndexMetadata,
    ParsedDocumentElement,
    StandardClause,
)
from open_deep_research.compliance_reviewer import (
    _enforce_report_guardrails,
    prepare_review_request,
    retrieve_evidence,
)


def test_iter_source_files_filters_supported_extensions(tmp_path: Path):
    (tmp_path / "a.pdf").write_text("pdf", encoding="utf-8")
    (tmp_path / "b.docx").write_text("docx", encoding="utf-8")
    (tmp_path / "c.txt").write_text("txt", encoding="utf-8")

    names = {path.name for path in iter_source_files(tmp_path)}

    assert names == {"a.pdf", "b.docx"}


def test_chunk_index_and_retrieve_internal_evidence(tmp_path: Path):
    elements = [
        ParsedDocumentElement(
            source_type="internal",
            path=str(tmp_path / "CAPA.docx"),
            file_name="CAPA.docx",
            extension=".docx",
            text="CAPA procedure requires root cause analysis, correction, corrective action, and effectiveness check.",
        ),
        ParsedDocumentElement(
            source_type="standard",
            path=str(tmp_path / "ISO13485.pdf"),
            file_name="ISO13485.pdf",
            extension=".pdf",
            text="The organization shall document procedures for corrective action.",
            page_number=8,
        ),
    ]
    chunks = chunk_elements(elements)
    metadata = IndexMetadata(total_files_seen=2, total_files_indexed=2, total_chunks=len(chunks))
    write_index(tmp_path / "index", chunks, metadata)

    loaded = read_chunks(tmp_path / "index")
    retriever = ComplianceRetriever(loaded)
    results = retriever.search("corrective action effectiveness", source_type="internal", top_k=1)

    assert len(loaded) == 2
    assert results
    assert results[0].evidence_id
    assert results[0].file_name == "CAPA.docx"
    assert "effectiveness" in results[0].excerpt


def test_select_review_topics_can_focus_on_user_scope():
    topics = select_review_topics("Please review CAPA, internal audit, and DHR.")
    topic_ids = {topic.topic_id for topic in topics}

    assert topic_ids == {"capa", "internal_audit", "product_release_dhr"}


def test_select_review_topics_defaults_to_iso_13485_mvp_scope():
    topics = select_review_topics("Run an ISO 13485 mock audit.")

    assert len(topics) >= 8
    assert topics[0].topic_id == "document_control"


def test_format_evidence_block_accepts_serialized_dict():
    block = format_evidence_block(
        [
            {
                "file_name": "CAPA.docx",
                "evidence_id": "abc123",
                "path": "CAPA.docx",
                "excerpt": "effectiveness check",
                "source_type": "internal",
                "page_number": None,
                "sheet_name": None,
                "row_range": None,
                "score": 1.2,
            }
        ]
    )

    assert "CAPA.docx" in block
    assert "Evidence ID: abc123" in block
    assert "effectiveness check" in block


def test_clause_store_loads_structured_standard_clauses(tmp_path: Path):
    clause_dir = tmp_path / "standard_clauses"
    clause_dir.mkdir()
    clause_path = clause_dir / "clauses.jsonl"
    clause = StandardClause(
        standard="ISO 13485:2016",
        clause_id="8.5.2",
        title="Corrective action",
        text="The organization shall take action to eliminate the cause of nonconformities.",
        source_path="ISO13485.pdf",
        page_start=33,
        page_end=33,
    )
    clause_path.write_text(clause.model_dump_json() + "\n", encoding="utf-8")

    store = ClauseStore.from_path(clause_path)

    assert store.get("ISO 13485:2016", "8.5.2").title == "Corrective action"


def test_retrieve_evidence_groups_serialized_results_by_topic(tmp_path: Path):
    elements = [
        ParsedDocumentElement(
            source_type="standard",
            path=str(tmp_path / "ISO13485.pdf"),
            file_name="ISO13485.pdf",
            extension=".pdf",
            text="ISO 13485 8.5.2 corrective action requires root cause and effectiveness verification.",
        ),
        ParsedDocumentElement(
            source_type="internal",
            path=str(tmp_path / "CAPA.docx"),
            file_name="CAPA.docx",
            extension=".docx",
            text="CAPA procedure covers root cause analysis and corrective action effectiveness check.",
        ),
    ]
    chunks = chunk_elements(elements)
    index_dir = tmp_path / "compliance_index"
    write_index(index_dir, chunks, IndexMetadata(total_files_seen=2, total_files_indexed=2, total_chunks=len(chunks)))
    clause_dir = tmp_path / "standard_clauses"
    clause_dir.mkdir()
    clause_path = clause_file_for_index(index_dir)
    clause_path.write_text(
        StandardClause(
            standard="ISO 13485:2016",
            clause_id="8.5.2",
            title="Corrective action",
            text="The organization shall document corrective action procedures.",
            source_path="ISO13485.pdf",
            page_start=33,
        ).model_dump_json()
        + "\n",
        encoding="utf-8",
    )

    request_state = {"messages": [HumanMessage(content="Please review CAPA")]}
    review_request = prepare_review_request(request_state, {})["review_request"]
    result = retrieve_evidence(
        {"messages": request_state["messages"], "review_request": review_request},
        {"configurable": {"compliance_index_path": str(index_dir)}},
    )

    assert result["review_topics"][0]["topic_id"] == "capa"
    assert result["topic_evidence"][0]["standard_clauses"][0]["clause_id"] == "8.5.2"
    assert result["topic_evidence"][0]["standard_evidence"][0]["file_name"] == "ISO13485.pdf"
    assert result["topic_evidence"][0]["internal_evidence"][0]["file_name"] == "CAPA.docx"


def test_render_compliance_review_report_outputs_matrix():
    report = ComplianceReviewReport(
        review_scope="CAPA pre-audit review",
        overall_risk_level="中",
        overall_summary="CAPA procedure evidence is present but effectiveness evidence needs confirmation.",
        assessments=[
            ClauseAssessment(
                topic_id="capa",
                topic_title="CAPA",
                standard="ISO 13485:2016",
                clause_id="8.5.2",
                requirement_summary="The organization shall document corrective action procedures.",
                status="需澄清",
                rationale="Procedure exists, but sampled effectiveness records were not confirmed.",
                evidence=[
                    EvidenceItem(
                        file_name="CAPA.docx",
                        evidence_id="abc123",
                        path="CAPA.docx",
                        excerpt="CAPA procedure covers root cause analysis and effectiveness check.",
                        source_type="internal",
                    )
                ],
                risk="Effectiveness verification may be incomplete.",
                recommendation="Sample closed CAPA records and verify effectiveness evidence.",
            )
        ],
        limitations=["Only indexed files were reviewed."],
    )

    rendered = render_compliance_review_report(report)

    assert "| 条款/主题 | 要求摘要 | 内部证据 | 判断 | 风险 | 建议 |" in rendered
    assert "abc123" in rendered
    assert "CAPA.docx" in rendered
    assert "需澄清" in rendered


def test_report_guardrail_downgrades_compliant_assessment_without_internal_evidence():
    report = ComplianceReviewReport(
        review_scope="Document control",
        overall_risk_level="低",
        overall_summary="Looks compliant.",
        assessments=[
            ClauseAssessment(
                standard="ISO 13485:2016",
                clause_id="4.2.4",
                requirement_summary="Documents shall be controlled.",
                status="符合",
                rationale="Model claimed compliance without cited evidence.",
            )
        ],
    )

    guarded = _enforce_report_guardrails(report)

    assert guarded.assessments[0].status == "缺乏证据"
    assert guarded.overall_risk_level == "证据不足"
    assert "降级" in guarded.limitations[0]


def test_report_guardrail_hydrates_only_traceable_internal_evidence():
    report = ComplianceReviewReport(
        review_scope="CAPA",
        overall_risk_level="低",
        overall_summary="Traceable evidence cited.",
        assessments=[
            ClauseAssessment(
                standard="ISO 13485:2016",
                clause_id="8.5.2",
                requirement_summary="Corrective action shall be documented.",
                status="符合",
                rationale="Cites one real evidence ID and one fake ID.",
                evidence=[
                    EvidenceItem(evidence_id="real-id", file_name="hallucinated.docx", source_type="internal"),
                    EvidenceItem(evidence_id="fake-id", file_name="fake.docx", source_type="internal"),
                ],
            )
        ],
    )
    topic_evidence = [
        {
            "internal_evidence": [
                {
                    "evidence_id": "real-id",
                    "file_name": "CAPA.docx",
                    "path": "CAPA.docx",
                    "excerpt": "Approved CAPA procedure.",
                    "source_type": "internal",
                }
            ]
        }
    ]

    guarded = _enforce_report_guardrails(report, topic_evidence)

    assert guarded.assessments[0].status == "符合"
    assert guarded.assessments[0].evidence[0].file_name == "CAPA.docx"
    assert len(guarded.assessments[0].evidence) == 1
    assert "fake-id" in guarded.limitations[0]

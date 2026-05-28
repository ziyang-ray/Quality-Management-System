from pathlib import Path

from langchain_core.messages import HumanMessage

from open_deep_research.compliance.chunking import chunk_elements
from open_deep_research.compliance.document_loader import iter_source_files
from open_deep_research.compliance.index_store import read_chunks, write_index
from open_deep_research.compliance.prompts import format_evidence_block
from open_deep_research.compliance.retrieval import ComplianceRetriever
from open_deep_research.compliance.review_topics import select_review_topics
from open_deep_research.compliance.schemas import IndexMetadata, ParsedDocumentElement
from open_deep_research.compliance_reviewer import prepare_review_request, retrieve_evidence


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
    assert "effectiveness check" in block


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
    index_dir = tmp_path / "index"
    write_index(index_dir, chunks, IndexMetadata(total_files_seen=2, total_files_indexed=2, total_chunks=len(chunks)))

    request_state = {"messages": [HumanMessage(content="Please review CAPA")]}
    review_request = prepare_review_request(request_state, {})["review_request"]
    result = retrieve_evidence(
        {"messages": request_state["messages"], "review_request": review_request},
        {"configurable": {"compliance_index_path": str(index_dir)}},
    )

    assert result["review_topics"][0]["topic_id"] == "capa"
    assert result["topic_evidence"][0]["standard_evidence"][0]["file_name"] == "ISO13485.pdf"
    assert result["topic_evidence"][0]["internal_evidence"][0]["file_name"] == "CAPA.docx"

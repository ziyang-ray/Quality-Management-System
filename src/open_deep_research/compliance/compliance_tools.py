"""LangChain tools for local compliance evidence retrieval."""

from pathlib import Path
from typing import Annotated

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool

from open_deep_research.compliance.index_store import read_metadata
from open_deep_research.compliance.prompts import format_evidence_block
from open_deep_research.compliance.retrieval import ComplianceRetriever
from open_deep_research.configuration import Configuration


def _index_path(config: RunnableConfig | None) -> Path:
    configurable = Configuration.from_runnable_config(config)
    return Path(configurable.compliance_index_path)


@tool(description="Search official standard excerpts such as ISO 13485 and ISO 14971 from the local compliance index.")
def search_standard_clauses(
    query: str,
    top_k: int = 8,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,
) -> str:
    """Search official standard chunks in the local compliance index."""

    retriever = ComplianceRetriever.from_index_dir(_index_path(config))
    return format_evidence_block(retriever.search(query, source_type="standard", top_k=top_k))


@tool(description="Search Siemens Healthineers internal QMS document excerpts from the local compliance index.")
def search_internal_qms_documents(
    query: str,
    top_k: int = 12,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,
) -> str:
    """Search internal QMS chunks in the local compliance index."""

    retriever = ComplianceRetriever.from_index_dir(_index_path(config))
    return format_evidence_block(retriever.search(query, source_type="internal", top_k=top_k))


@tool(description="Summarize the local compliance index status, including indexed and skipped files.")
def get_compliance_index_summary(
    config: Annotated[RunnableConfig, InjectedToolArg] = None,
) -> str:
    """Return index metadata for troubleshooting."""

    metadata = read_metadata(_index_path(config))
    skipped = "\n".join(
        f"- {item.get('path')}: {item.get('reason')}" for item in metadata.skipped_files[:20]
    )
    return (
        f"Indexed files: {metadata.total_files_indexed}/{metadata.total_files_seen}\n"
        f"Chunks: {metadata.total_chunks}\n"
        f"Source roots: {metadata.source_roots}\n"
        f"Skipped files:\n{skipped or 'None'}"
    )


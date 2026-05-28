"""Clause-driven compliance reviewer backed by local QMS evidence retrieval."""

import asyncio
import os
from collections import Counter
from typing import Annotated

from langchain_core.messages import AIMessage, HumanMessage, get_buffer_string
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from open_deep_research.compliance.clause_store import ClauseStore
from open_deep_research.compliance.clause_topic_mapping import (
    select_clauses_directly,
    select_topics_and_clauses,
)
from open_deep_research.compliance.prompts import (
    CLAUSE_ASSESSMENT_PROMPT,
    REPORT_AGGREGATION_PROMPT,
    format_clause_evidence,
    format_evidence_block,
)
from open_deep_research.compliance.retrieval import ComplianceRetriever
from open_deep_research.compliance.schemas import (
    ClauseAssessment,
    ComplianceReviewReport,
    EvidenceItem,
    StandardClause,
)
from open_deep_research.configuration import Configuration


# --- State definitions ---

class ClauseDrivenReviewerState(MessagesState):
    """State for the clause-driven compliance reviewer workflow."""

    review_request: str
    selected_clause_ids: list[tuple[str, str]]  # (standard, clause_id)
    clause_evidence: dict  # "standard::clause_id" -> {standard_evidence, internal_evidence}
    assessments: list[dict]  # ClauseAssessment.model_dump() list
    final_report: str


class EvidenceRetrievalState(TypedDict):
    """Internal update shape for evidence retrieval."""

    messages: Annotated[list, add_messages]
    review_request: str
    selected_clause_ids: list[tuple[str, str]]
    clause_evidence: dict


# --- Helper functions ---

_clause_store_cache: dict[str, ClauseStore] = {}


def _load_clause_store(config: RunnableConfig) -> ClauseStore:
    """Load clause store from configured path with simple caching."""
    configurable = Configuration.from_runnable_config(config)
    path = configurable.clause_store_path
    if path not in _clause_store_cache:
        _clause_store_cache[path] = ClauseStore.from_jsonl(path)
    return _clause_store_cache[path]


def _merge_evidence(
    primary: list[EvidenceItem],
    secondary: list[EvidenceItem],
) -> list[EvidenceItem]:
    """Merge two rounds of retrieval results, dedup by file_name+excerpt, keep higher score."""
    seen: dict[str, EvidenceItem] = {}
    for item in primary:
        key = f"{item.file_name}::{item.excerpt[:100]}"
        seen[key] = item
    for item in secondary:
        key = f"{item.file_name}::{item.excerpt[:100]}"
        if key not in seen or (item.score or 0) > (seen[key].score or 0):
            seen[key] = item
    return list(seen.values())


def _report_to_markdown(report: ComplianceReviewReport) -> str:
    """Convert structured report to Markdown for display."""
    lines = [
        "# 合规审查报告",
        "",
        "## 1. 审查范围",
        report.review_scope,
        "",
        "## 2. 总体结论",
        report.overall_summary,
        "",
        "## 3. 条款符合性矩阵",
        "",
        "| 条款 | 状态 | 要求摘要 | 风险 | 建议 |",
        "|------|------|----------|------|------|",
    ]

    for a in report.assessments:
        lines.append(
            f"| {a.standard} {a.clause_id} | {a.status} | {a.requirement_summary[:50]}... | {a.risk[:30]}... | {a.recommendation[:30]}... |"
        )

    lines.extend([
        "",
        "## 4. 潜在不符合项与风险",
    ])
    risk_items = [a for a in report.assessments if a.status in ("需澄清", "缺乏证据", "未提及")]
    if risk_items:
        for a in risk_items:
            lines.append(f"- **{a.standard} {a.clause_id}** ({a.status}): {a.rationale[:100]}...")
    else:
        lines.append("- 无潜在不符合项")

    lines.extend([
        "",
        "## 5. 建议整改动作",
    ])
    rec_items = [a for a in report.assessments if a.recommendation]
    if rec_items:
        for a in rec_items:
            lines.append(f"- **{a.standard} {a.clause_id}**: {a.recommendation[:100]}...")
    else:
        lines.append("- 无建议整改动作")

    lines.extend([
        "",
        "## 6. 局限性",
    ])
    for lim in report.limitations:
        lines.append(f"- {lim}")

    return "\n".join(lines)


def _build_summary(assessments: list[ClauseAssessment], status_counts: Counter) -> str:
    """Build overall summary from assessments."""
    total = len(assessments)
    if total == 0:
        return "未找到可评估的条款。"

    compliant = status_counts.get("符合", 0)
    clarify = status_counts.get("需澄清", 0)
    lack = status_counts.get("缺乏证据", 0)
    missing = status_counts.get("未提及", 0)

    lines = [
        f"共评估 {total} 个条款：",
        f"- 符合：{compliant} 个",
        f"- 需澄清：{clarify} 个",
        f"- 缺乏证据：{lack} 个",
        f"- 未提及：{missing} 个",
    ]

    if missing > 0:
        lines.append(f"\n有 {missing} 个条款在内部文件中未找到相关证据，建议优先补充。")
    if clarify > 0:
        lines.append(f"有 {clarify} 个条款需要进一步澄清，建议与相关部门确认。")

    return "\n".join(lines)


def _default_limitations() -> list[str]:
    return [
        "本审查基于BM25文本检索，可能遗漏语义相关但措辞不同的证据。",
        "条款库为自动提取的候选条款，部分条款可能需要人工校验。",
        "内部文件覆盖率取决于已索引的文件范围，部分旧格式文件（.doc/.xls/.pptx）可能未被索引。",
        "本报告为内部预审辅助工具，不构成最终的认证审核结论。",
    ]


# --- Workflow nodes ---

def parse_review_scope(state: ClauseDrivenReviewerState, config: RunnableConfig) -> dict:
    """Parse user request to determine which clauses to review.

    Logic:
    1. Try direct clause ID matching (e.g. "审查4.2.4和8.5.2")
    2. Fall back to topic-based mapping
    3. For broad requests ("模拟审核"), select all MVP clauses
    """
    clause_store = _load_clause_store(config)
    review_request = get_buffer_string(state.get("messages", []))

    # Try direct clause ID matching first
    clauses = select_clauses_directly(review_request, clause_store)
    if not clauses:
        # Fall back to topic mapping
        mappings = select_topics_and_clauses(review_request, clause_store)
        clause_refs = []
        for m in mappings:
            clause_refs.extend(m.clause_refs)
        clauses = clause_store.get_clauses_by_ids(clause_refs)

    return {
        "review_request": review_request,
        "selected_clause_ids": [(c.standard, c.clause_id) for c in clauses],
    }


def retrieve_clause_evidence(state: ClauseDrivenReviewerState, config: RunnableConfig) -> EvidenceRetrievalState:
    """Retrieve evidence for each selected clause using two-round retrieval.

    Round 1: Use clause.search_terms for initial retrieval
    Round 2: Supplement with expected_evidence keywords
    """
    configurable = Configuration.from_runnable_config(config)
    retriever = ComplianceRetriever.from_index_dir(configurable.compliance_index_path)
    clause_store = _load_clause_store(config)

    clause_evidence = {}
    for standard, clause_id in state["selected_clause_ids"]:
        clause = clause_store.get_clause(standard, clause_id)
        if not clause:
            continue

        # Round 1: search with clause terms
        query = " ".join(clause.search_terms[:8])
        standard_evidence = retriever.search(query, source_type="standard", top_k=4)
        internal_evidence = retriever.search(query, source_type="internal", top_k=6)

        # Round 2: supplement with expected_evidence keywords
        for ev_desc in clause.expected_evidence[:2]:
            extra = retriever.search(ev_desc, source_type="internal", top_k=3)
            internal_evidence = _merge_evidence(internal_evidence, extra)

        key = f"{standard}::{clause_id}"
        clause_evidence[key] = {
            "standard_evidence": [e.model_dump() for e in standard_evidence],
            "internal_evidence": [e.model_dump() for e in internal_evidence],
        }

    return {
        "messages": [],
        "review_request": state["review_request"],
        "selected_clause_ids": state["selected_clause_ids"],
        "clause_evidence": clause_evidence,
    }


async def assess_clauses(state: ClauseDrivenReviewerState, config: RunnableConfig) -> dict:
    """Assess each clause against retrieved evidence using structured LLM output.

    Uses asyncio.gather for parallel assessment of multiple clauses.
    """
    from langchain.chat_models import init_chat_model

    configurable = Configuration.from_runnable_config(config)
    clause_store = _load_clause_store(config)

    model_config = {
        "model": configurable.final_report_model,
        "max_tokens": configurable.final_report_model_max_tokens,
        "api_key": _get_api_key_for_model(configurable.final_report_model, config),
        "tags": ["langsmith:nostream"],
    }

    async def assess_single(clause_ref: tuple[str, str]) -> ClauseAssessment | None:
        standard, clause_id = clause_ref
        clause = clause_store.get_clause(standard, clause_id)
        if not clause:
            return None

        key = f"{standard}::{clause_id}"
        evidence = state["clause_evidence"].get(key, {})
        std_ev, int_ev = format_clause_evidence(
            evidence.get("standard_evidence", []),
            evidence.get("internal_evidence", []),
        )

        prompt = CLAUSE_ASSESSMENT_PROMPT.format(
            standard=clause.standard,
            clause_id=clause.clause_id,
            clause_title=clause.title,
            requirement_summary=clause.requirement_summary,
            expected_evidence="; ".join(clause.expected_evidence),
            internal_evidence=int_ev,
            standard_evidence=std_ev,
            json_schema=ClauseAssessment.model_json_schema(),
        )

        try:
            model = init_chat_model(configurable_fields=("model", "max_tokens", "api_key"))
            structured_model = model.with_config(model_config).with_structured_output(
                ClauseAssessment, max_structured_output_retries=3
            )
            return await structured_model.ainvoke([HumanMessage(content=prompt)])
        except Exception:
            return None

    # Run assessments in parallel
    tasks = [assess_single(ref) for ref in state["selected_clause_ids"]]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    assessments = []
    for result in results:
        if isinstance(result, Exception) or result is None:
            continue
        assessments.append(result.model_dump())

    return {"assessments": assessments}


async def aggregate_report(state: ClauseDrivenReviewerState, config: RunnableConfig) -> dict:
    """Aggregate individual clause assessments into a structured compliance report."""
    assessments = [ClauseAssessment(**a) for a in state["assessments"]]

    status_counts = Counter(a.status for a in assessments)
    overall_summary = _build_summary(assessments, status_counts)

    report = ComplianceReviewReport(
        review_scope=state["review_request"],
        overall_summary=overall_summary,
        assessments=assessments,
        limitations=_default_limitations(),
    )

    report_json = report.model_dump_json(ensure_ascii=False, indent=2)
    report_md = _report_to_markdown(report)

    return {
        "final_report": report_json,
        "messages": [AIMessage(content=report_md)],
    }


# --- Graph construction ---

clause_driven_reviewer_builder = StateGraph(
    ClauseDrivenReviewerState,
    input=MessagesState,
    config_schema=Configuration,
)

clause_driven_reviewer_builder.add_node("parse_review_scope", parse_review_scope)
clause_driven_reviewer_builder.add_node("retrieve_clause_evidence", retrieve_clause_evidence)
clause_driven_reviewer_builder.add_node("assess_clauses", assess_clauses)
clause_driven_reviewer_builder.add_node("aggregate_report", aggregate_report)

clause_driven_reviewer_builder.add_edge(START, "parse_review_scope")
clause_driven_reviewer_builder.add_edge("parse_review_scope", "retrieve_clause_evidence")
clause_driven_reviewer_builder.add_edge("retrieve_clause_evidence", "assess_clauses")
clause_driven_reviewer_builder.add_edge("assess_clauses", "aggregate_report")
clause_driven_reviewer_builder.add_edge("aggregate_report", END)

compliance_reviewer = clause_driven_reviewer_builder.compile()


# --- API key helper ---

def _get_api_key_for_model(model_name: str, config: RunnableConfig):
    """Get a model API key without importing the broader research utils module."""

    should_get_from_config = os.getenv("GET_API_KEYS_FROM_CONFIG", "false")
    model_name = model_name.lower()
    if should_get_from_config.lower() == "true":
        api_keys = config.get("configurable", {}).get("apiKeys", {}) if config else {}
        if not api_keys:
            return None
        if model_name.startswith("openai:"):
            return api_keys.get("OPENAI_API_KEY")
        if model_name.startswith("anthropic:"):
            return api_keys.get("ANTHROPIC_API_KEY")
        if model_name.startswith("google"):
            return api_keys.get("GOOGLE_API_KEY")
        return None

    if model_name.startswith("openai:"):
        return os.getenv("OPENAI_API_KEY")
    if model_name.startswith("anthropic:"):
        return os.getenv("ANTHROPIC_API_KEY")
    if model_name.startswith("google"):
        return os.getenv("GOOGLE_API_KEY")
    return None

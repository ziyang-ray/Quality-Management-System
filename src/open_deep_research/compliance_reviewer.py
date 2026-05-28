"""LangGraph compliance reviewer backed by local QMS evidence retrieval with enhanced components."""

import os
from typing import Annotated, AsyncGenerator

from langchain_core.callbacks import dispatch_custom_event
from langchain_core.messages import AIMessage, HumanMessage, get_buffer_string
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from open_deep_research.compliance.clause_store import ClauseStore, clause_file_for_index
from open_deep_research.compliance.evidence_planner import EvidencePlanner, create_evidence_planner
from open_deep_research.compliance.knowledge_graph import ComplianceKnowledgeGraph
from open_deep_research.compliance.prompts import (
    COMPLIANCE_REVIEW_PROMPT,
    COMPLIANCE_STRUCTURED_REVIEW_PROMPT,
    format_topic_evidence_block,
)
from open_deep_research.compliance.renderers import render_compliance_review_report
from open_deep_research.compliance.retrieval import ComplianceRetriever
from open_deep_research.compliance.review_memory import ReviewMemory
from open_deep_research.compliance.review_topics import select_review_topics
from open_deep_research.compliance.schemas import ComplianceReviewReport, EvidenceItem
from open_deep_research.compliance.skill_loader import SkillLoader
from open_deep_research.configuration import Configuration


class ComplianceReviewerState(MessagesState):
    """State for the first compliance reviewer workflow."""

    review_request: str
    review_topics: list
    topic_evidence: list
    structured_report: dict
    final_report: str


class RetrievalState(TypedDict):
    """Internal update shape for evidence retrieval."""

    messages: Annotated[list, add_messages]
    review_request: str
    review_topics: list
    topic_evidence: list


def prepare_review_request(state: ComplianceReviewerState, config: RunnableConfig) -> dict:
    """Convert conversation into a concise review request."""

    messages = state.get("messages", [])
    return {"review_request": get_buffer_string(messages)}


def retrieve_evidence(state: ComplianceReviewerState, config: RunnableConfig) -> RetrievalState:
    """Retrieve official requirements and internal evidence by review topic with enhanced planning."""

    configurable = Configuration.from_runnable_config(config)
    retriever = ComplianceRetriever.from_index_dir(configurable.compliance_index_path)
    clause_store = ClauseStore.from_path(clause_file_for_index(configurable.compliance_index_path))

    def _emit_progress(event_data):
        try:
            dispatch_custom_event("review_progress", event_data, config=config)
        except Exception:
            pass

    knowledge_graph = None
    kg_dir = getattr(configurable, 'knowledge_graph_dir', None)
    if kg_dir:
        try:
            knowledge_graph = ComplianceKnowledgeGraph.from_directory(kg_dir)
        except Exception:
            pass

    skill_loader = None
    skills_dir = getattr(configurable, 'skills_dir', None)
    if skills_dir:
        try:
            skill_loader = SkillLoader.from_directory(skills_dir)
        except Exception:
            pass

    evidence_planner = EvidencePlanner(
        clause_store=clause_store,
        knowledge_graph=knowledge_graph,
        skill_loader=skill_loader,
    )

    review_request = state.get("review_request", "")
    review_topics = select_review_topics(review_request)
    topic_evidence = []

    for i, topic in enumerate(review_topics):
        _emit_progress({
            "stage": "retrieve_evidence",
            "topic_id": topic.topic_id,
            "topic_title": topic.title,
            "current": i + 1,
            "total": len(review_topics),
            "message": f"Retrieving [{i+1}/{len(review_topics)}] {topic.title}...",
        })
        standard_clauses = clause_store.get_many(topic.standard_clause_refs)

        internal_plan = evidence_planner.plan_internal_evidence_search(topic)
        internal_evidence = []
        for item in retriever.search(
            topic.internal_query,
            source_type="internal",
            top_k=6,
            preferred_terms=list(topic.preferred_internal_terms) + internal_plan.skill_expanded_terms[:3],
        ):
            internal_evidence.append(item.model_dump())

        standard_evidence = []
        for item in retriever.search(topic.standard_query, source_type="standard", top_k=4):
            standard_evidence.append(item.model_dump())

        evidence_package = evidence_planner.build_evidence_package(
            topic=topic,
            standard_evidence=standard_evidence,
            internal_evidence=internal_evidence,
            standard_clauses=[clause.model_dump() for clause in standard_clauses],
        )

        _emit_progress({
            "stage": "retrieve_evidence_done",
            "topic_id": topic.topic_id,
            "internal_count": len(internal_evidence),
            "standard_count": len(standard_evidence),
            "message": f"  Found {len(internal_evidence)} internal, {len(standard_evidence)} standard evidence",
        })

        topic_evidence.append(evidence_package)

    return {
        "messages": [],
        "review_request": review_request,
        "review_topics": [
            {
                "topic_id": topic.topic_id,
                "title": topic.title,
                "standard_clause_refs": list(topic.standard_clause_refs),
            }
            for topic in review_topics
        ],
        "topic_evidence": topic_evidence,
    }


async def generate_compliance_report(state: ComplianceReviewerState, config: RunnableConfig) -> dict:
    """Generate a structured compliance review report, then render it as Markdown."""

    from openai import AsyncOpenAI
    from langchain_openai import ChatOpenAI

    def _emit_progress(event_data):
        try:
            dispatch_custom_event("review_progress", event_data, config=config)
        except Exception:
            pass

    def _emit_chunk(content):
        try:
            dispatch_custom_event("report_chunk", {"content": content}, config=config)
        except Exception:
            pass

    _emit_progress({
        "stage": "generate_report",
        "message": "Generating compliance review report...",
    })

    configurable = Configuration.from_runnable_config(config)
    model_name = configurable.final_report_model

    # Get API configuration from environment or use defaults
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN") or os.getenv("ANTHROPIC_API_KEY")
    base_url = os.getenv("OPENAI_API_BASE") or os.getenv("OPENAI_BASE_URL")

    # If no base_url from env, try to construct from ANTHROPIC_BASE_URL
    if not base_url:
        anthropic_base = os.getenv("ANTHROPIC_BASE_URL", "")
        if anthropic_base:
            base_url = anthropic_base.replace("/anthropic", "/v1")
        else:
            base_url = "https://token-plan-sgp.xiaomimimo.com/v1"

    topic_evidence = format_topic_evidence_block(state.get("topic_evidence", []))
    structured_prompt = COMPLIANCE_STRUCTURED_REVIEW_PROMPT.format(
        review_request=state.get("review_request", ""),
        topic_evidence=topic_evidence,
    )

    if model_name.startswith("anthropic:"):
        model_name = model_name.replace("anthropic:", "")

    # Force model name for custom API
    if "mimo" not in model_name.lower():
        model_name = "mimo-v2.5-pro"

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    model = ChatOpenAI(
        model=model_name,
        max_tokens=configurable.final_report_model_max_tokens,
        client=client,
    )

    try:
        structured_model = model.with_structured_output(ComplianceReviewReport)
        structured_output = await structured_model.ainvoke([HumanMessage(content=structured_prompt)])
        structured_report = _enforce_report_guardrails(
            _coerce_compliance_report(structured_output),
            state.get("topic_evidence", []),
        )
        final_report = render_compliance_review_report(structured_report)
        _emit_chunk(final_report)
        return {
            "structured_report": structured_report.model_dump(),
            "final_report": final_report,
            "messages": [AIMessage(content=final_report)],
        }
    except Exception:
        pass

    _emit_progress({
        "stage": "generate_report_streaming",
        "message": "Streaming markdown report generation...",
    })

    prompt = COMPLIANCE_REVIEW_PROMPT.format(
        review_request=state.get("review_request", ""),
        topic_evidence=topic_evidence,
    )

    full_content = ""
    async for event in model.astream_events([HumanMessage(content=prompt)], version="v2"):
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            if chunk.content:
                full_content += chunk.content
                _emit_chunk(chunk.content)

    return {
        "structured_report": {},
        "final_report": full_content,
        "messages": [AIMessage(content=full_content)],
    }


def _coerce_compliance_report(value) -> ComplianceReviewReport:
    """Normalize provider-specific structured output into the report schema."""

    if isinstance(value, ComplianceReviewReport):
        return value
    if isinstance(value, dict):
        return ComplianceReviewReport.model_validate(value)
    return ComplianceReviewReport.model_validate_json(str(value))


def _enforce_report_guardrails(
    report: ComplianceReviewReport,
    topic_evidence: list[dict] | None = None,
) -> ComplianceReviewReport:
    """Prevent unsupported compliant findings from reaching the final report."""

    internal_evidence_by_id = _internal_evidence_by_id(topic_evidence or [])
    known_internal_evidence_ids = set(internal_evidence_by_id)
    downgraded: list[str] = []
    removed_untraceable: list[str] = []
    for assessment in report.assessments:
        hydrated_evidence: list[EvidenceItem] = []
        for evidence in assessment.evidence:
            if evidence.evidence_id and evidence.evidence_id in internal_evidence_by_id:
                hydrated_evidence.append(internal_evidence_by_id[evidence.evidence_id])
            elif evidence.evidence_id and known_internal_evidence_ids:
                removed_untraceable.append(evidence.evidence_id)
        if known_internal_evidence_ids:
            assessment.evidence = hydrated_evidence

        cited_internal_ids = {evidence.evidence_id for evidence in assessment.evidence if evidence.evidence_id}
        has_traceable_internal_evidence = bool(cited_internal_ids)
        if not known_internal_evidence_ids:
            has_traceable_internal_evidence = any(evidence.source_type == "internal" for evidence in assessment.evidence)

        if assessment.status == "符合" and not has_traceable_internal_evidence:
            assessment.status = "缺乏证据"
            assessment.risk = assessment.risk or "该条款被判为符合，但未引用可追溯的内部证据。"
            assessment.recommendation = assessment.recommendation or "补充可追溯的内部程序、记录或样本证据后再确认符合性。"
            downgraded.append(f"{assessment.standard} {assessment.clause_id}".strip())

    if removed_untraceable:
        unique_ids = sorted(set(removed_untraceable))
        report.limitations.append(
            "系统已移除未出现在本次检索证据包中的证据引用："
            + "、".join(unique_ids)
            + "。"
        )
    if downgraded:
        report.limitations.append(
            "系统已将未引用内部证据的'符合'判断降级为'缺乏证据'："
            + "、".join(downgraded)
            + "。"
        )
        if report.overall_risk_level == "低":
            report.overall_risk_level = "证据不足"
    return report


def _internal_evidence_by_id(topic_evidence: list[dict]) -> dict[str, EvidenceItem]:
    evidence_by_id: dict[str, EvidenceItem] = {}
    for topic in topic_evidence:
        for item in topic.get("internal_evidence", []):
            evidence = EvidenceItem.model_validate(item)
            if evidence.evidence_id:
                evidence_by_id[evidence.evidence_id] = evidence
    return evidence_by_id


compliance_reviewer_builder = StateGraph(
    ComplianceReviewerState,
    input=MessagesState,
    config_schema=Configuration,
)

compliance_reviewer_builder.add_node("prepare_review_request", prepare_review_request)
compliance_reviewer_builder.add_node("retrieve_evidence", retrieve_evidence)
compliance_reviewer_builder.add_node("generate_compliance_report", generate_compliance_report)

compliance_reviewer_builder.add_edge(START, "prepare_review_request")
compliance_reviewer_builder.add_edge("prepare_review_request", "retrieve_evidence")
compliance_reviewer_builder.add_edge("retrieve_evidence", "generate_compliance_report")
compliance_reviewer_builder.add_edge("generate_compliance_report", END)

compliance_reviewer = compliance_reviewer_builder.compile()


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
        return os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")
    if model_name.startswith("google"):
        return os.getenv("GOOGLE_API_KEY")
    return None


async def run_compliance_review_streaming(
    input_messages: list,
    configurable_kwargs: dict | None = None,
) -> AsyncGenerator[dict, None]:
    """Run the compliance review graph with streaming progress events.

    Yields dicts with event information:
    - {"type": "node_start", "node": str}
    - {"type": "progress", "stage": str, "message": str, ...}
    - {"type": "report_chunk", "content": str}
    - {"type": "complete", "result": dict}
    """

    config = {"configurable": configurable_kwargs or {}}

    final_result = None
    async for event in compliance_reviewer.astream_events(
        {"messages": input_messages}, config, version="v2"
    ):
        kind = event["event"]

        if kind == "on_chain_start":
            yield {"type": "node_start", "node": event.get("name", "")}

        elif kind == "on_custom_event" and event.get("name") == "review_progress":
            yield {"type": "progress", **event["data"]}

        elif kind == "on_custom_event" and event.get("name") == "report_chunk":
            yield {"type": "report_chunk", "content": event["data"]["content"]}

        elif kind == "on_chain_end" and not event.get("parent_ids"):
            final_result = event["data"].get("output")

    if final_result:
        yield {"type": "complete", "result": final_result}

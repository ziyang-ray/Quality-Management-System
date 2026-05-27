"""LangGraph compliance reviewer backed by local QMS evidence retrieval."""

import os
from typing import Annotated

from langchain_core.messages import AIMessage, HumanMessage, get_buffer_string
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from open_deep_research.compliance.prompts import COMPLIANCE_REVIEW_PROMPT, format_topic_evidence_block
from open_deep_research.compliance.retrieval import ComplianceRetriever
from open_deep_research.compliance.review_topics import select_review_topics
from open_deep_research.configuration import Configuration


class ComplianceReviewerState(MessagesState):
    """State for the first compliance reviewer workflow."""

    review_request: str
    review_topics: list
    topic_evidence: list
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
    """Retrieve official requirements and internal evidence by review topic."""

    configurable = Configuration.from_runnable_config(config)
    retriever = ComplianceRetriever.from_index_dir(configurable.compliance_index_path)
    review_request = state.get("review_request", "")
    review_topics = select_review_topics(review_request)
    topic_evidence = []
    for topic in review_topics:
        topic_evidence.append(
            {
                "topic_id": topic.topic_id,
                "title": topic.title,
                "expected_evidence": topic.expected_evidence,
                "standard_evidence": [
                    item.model_dump()
                    for item in retriever.search(topic.standard_query, source_type="standard", top_k=4)
                ],
                "internal_evidence": [
                    item.model_dump()
                    for item in retriever.search(
                        topic.internal_query,
                        source_type="internal",
                        top_k=6,
                        preferred_terms=list(topic.preferred_internal_terms),
                    )
                ],
            }
        )
    return {
        "messages": [],
        "review_request": review_request,
        "review_topics": [topic.__dict__ for topic in review_topics],
        "topic_evidence": topic_evidence,
    }


async def generate_compliance_report(state: ComplianceReviewerState, config: RunnableConfig) -> dict:
    """Generate a markdown compliance review report from retrieved evidence."""

    from langchain.chat_models import init_chat_model

    configurable = Configuration.from_runnable_config(config)
    model_config = {
        "model": configurable.final_report_model,
        "max_tokens": configurable.final_report_model_max_tokens,
        "api_key": _get_api_key_for_model(configurable.final_report_model, config),
        "tags": ["langsmith:nostream"],
    }
    prompt = COMPLIANCE_REVIEW_PROMPT.format(
        review_request=state.get("review_request", ""),
        topic_evidence=format_topic_evidence_block(state.get("topic_evidence", [])),
    )
    model = init_chat_model(configurable_fields=("model", "max_tokens", "api_key"))
    response = await model.with_config(model_config).ainvoke([HumanMessage(content=prompt)])
    return {
        "final_report": response.content,
        "messages": [AIMessage(content=response.content)],
    }


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
        return os.getenv("ANTHROPIC_API_KEY")
    if model_name.startswith("google"):
        return os.getenv("GOOGLE_API_KEY")
    return None

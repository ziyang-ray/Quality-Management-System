"""Demo script for tool calling with streaming output."""

import os
import sys
import asyncio
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# Set environment variables
API_KEY = "tp-s7egar2qket67uqm1yb7u842lvtp7bmgcjyyticqcojigb1v"
BASE_URL = "https://token-plan-sgp.xiaomimimo.com/v1"

os.environ["OPENAI_API_KEY"] = API_KEY
os.environ["OPENAI_API_BASE"] = BASE_URL
os.environ["OPENAI_BASE_URL"] = BASE_URL
os.environ["PYTHONIOENCODING"] = "utf-8"

from openai import AsyncOpenAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.tools import tool

from open_deep_research.compliance.clause_store import ClauseStore
from open_deep_research.compliance.retrieval import ComplianceRetriever
from open_deep_research.compliance.knowledge_graph import ComplianceKnowledgeGraph


# Define Tools
@tool
def search_clauses(query: str) -> str:
    """Search standard clauses by keyword. Returns matching clauses with their IDs and titles."""
    clause_store = ClauseStore.from_path(REPO_ROOT / "data" / "standard_clauses" / "clauses.jsonl")
    results = clause_store.search_clauses(query, limit=5)
    if not results:
        return f"No clauses found for query: {query}"
    output = []
    for clause in results:
        output.append(f"- {clause.standard} {clause.clause_id}: {clause.title}")
    return "\n".join(output)


@tool
def get_clause_detail(standard: str, clause_id: str) -> str:
    """Get detailed information about a specific clause by standard and clause ID."""
    clause_store = ClauseStore.from_path(REPO_ROOT / "data" / "standard_clauses" / "clauses.jsonl")
    clause = clause_store.get(standard, clause_id)
    if not clause:
        return f"Clause not found: {standard} {clause_id}"
    return f"""Standard: {clause.standard}
Clause ID: {clause.clause_id}
Title: {clause.title}
Requirement Summary: {clause.requirement_summary}
Expected Evidence: {', '.join(clause.expected_evidence)}
Search Terms: {', '.join(clause.search_terms[:5])}"""


@tool
def search_evidence(query: str, source_type: str = "internal") -> str:
    """Search for evidence in the compliance index. source_type can be 'internal' or 'standard'."""
    retriever = ComplianceRetriever.from_index_dir(REPO_ROOT / "data" / "compliance_index")
    results = retriever.search(query, source_type=source_type, top_k=3)
    if not results:
        return f"No {source_type} evidence found for: {query}"
    output = []
    for i, item in enumerate(results, 1):
        excerpt = item.excerpt[:150] + "..." if len(item.excerpt) > 150 else item.excerpt
        output.append(f"[{i}] {item.file_name} (score={item.score:.2f})\n    {excerpt}")
    return "\n\n".join(output)


@tool
def get_evidence_chain(standard: str, clause_id: str) -> str:
    """Get the evidence chain for a clause: processes -> procedures -> records from knowledge graph."""
    graph = ComplianceKnowledgeGraph.from_directory(REPO_ROOT / "data" / "compliance_graph")
    chain = graph.get_evidence_chain(standard, clause_id)
    output = []
    if chain["processes"]:
        output.append("Processes: " + ", ".join(n.label for n in chain["processes"]))
    if chain["procedures"]:
        output.append("Procedures: " + ", ".join(n.label for n in chain["procedures"]))
    if chain["records"]:
        output.append("Records: " + ", ".join(n.label for n in chain["records"]))
    return "\n".join(output) if output else "No evidence chain found"


# Define tools list
tools = [search_clauses, get_clause_detail, search_evidence, get_evidence_chain]
tools_by_name = {t.name: t for t in tools}


async def main():
    """Run tool calling demo with streaming."""

    print("=" * 70)
    print("  工具调用演示：Agent 自主审查条款")
    print("=" * 70)
    print()

    # Create model with tools
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)
    model = ChatOpenAI(
        model="mimo-v2.5-pro",
        max_tokens=4000,
        client=client,
    )
    model_with_tools = model.bind_tools(tools)

    # System prompt
    system_prompt = """你是一个专业的合规审查助手。你可以使用以下工具来帮助审查：

1. search_clauses(query) - 搜索标准条款
2. get_clause_detail(standard, clause_id) - 获取条款详情
3. search_evidence(query, source_type) - 检索证据（source_type: internal/standard）
4. get_evidence_chain(standard, clause_id) - 获取证据链

请用中文回答。在审查过程中，主动使用工具来获取信息。
"""

    user_prompt = "请帮我查找 ISO 13485:2016 中与 CAPA 相关的条款，并检索内部证据。"

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    print(f"User: {user_prompt}")
    print()
    print("Agent: ", end="", flush=True)

    # Run streaming agent loop
    max_iterations = 5
    for iteration in range(max_iterations):
        print(f"\n--- Iteration {iteration + 1} ---")

        response = None
        async for event in model_with_tools.astream_events(messages, version="v2"):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if chunk.content:
                    print(chunk.content, end="", flush=True)
            elif kind == "on_chat_model_end":
                response = event["data"]["output"]

        if response is None:
            break

        messages.append(response)

        if response.tool_calls:
            print(f"\n[Calling {len(response.tool_calls)} tool(s)]")
            for tc in response.tool_calls:
                name = tc["name"]
                args = tc["args"]
                tc_id = tc["id"]
                print(f"\n  [Tool] {name}({json.dumps(args, ensure_ascii=False)})")
                if name in tools_by_name:
                    result = tools_by_name[name].invoke(args)
                    print(f"  [Result] {result[:300]}...")
                    messages.append(ToolMessage(content=result, tool_call_id=tc_id))
                else:
                    print(f"  [Error] Unknown tool: {name}")
                    messages.append(ToolMessage(content=f"Unknown tool: {name}", tool_call_id=tc_id))
        else:
            if response.content:
                print(response.content, end="", flush=True)
            break

    print()
    print("=" * 70)
    print("  Demo complete")
    print("=" * 70)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

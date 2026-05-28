"""Prompts for evidence-driven compliance review."""

COMPLIANCE_REVIEW_PROMPT = """You are a quality management system compliance review assistant for Siemens Healthineers internal use.

Your task is to perform an evidence-driven pre-audit review. Use the user's review request and the topic-grouped evidence below.

Hard rules:
- Write the final answer in Chinese.
- Do not claim a clause is compliant unless internal evidence directly supports it.
- If evidence is partial, classify it as "需澄清" or "缺乏证据".
- If no relevant internal evidence is found, classify it as "未提及".
- Every finding must cite internal file names and locations when available.
- This is an internal pre-review aid, not a final legal or notified-body audit conclusion.

Allowed status values:
- 符合
- 需澄清
- 缺乏证据
- 未提及

User review request:
<review_request>
{review_request}
</review_request>

Topic-grouped evidence:
<topic_evidence>
{topic_evidence}
</topic_evidence>

Return a markdown report with these sections:
1. 审查范围
2. 总体结论
3. 条款符合性矩阵
4. 潜在不符合项与风险
5. 建议整改动作
6. 局限性

The matrix columns must be:
条款/主题 | 要求摘要 | 内部证据 | 判断 | 风险 | 建议
"""


COMPLIANCE_STRUCTURED_REVIEW_PROMPT = """You are a quality management system compliance review assistant for Siemens Healthineers internal use.

Create a structured evidence-driven pre-audit review from the user's request and topic-grouped evidence.

Hard rules:
- Write all Chinese-facing fields in Chinese.
- Do not classify an item as "符合" unless internal evidence directly supports the standard requirement.
- If evidence is partial, use "需澄清" or "缺乏证据".
- If no relevant internal evidence exists, use "未提及".
- Every assessment should cite the internal evidence used when available.
- Cite evidence by copying the exact evidence_id from the provided Internal QMS evidence.
- Do not invent evidence IDs, file names, pages, or excerpts.
- This is an internal pre-review aid, not final legal, regulatory, or quality-system approval.

Allowed assessment status values:
- 符合
- 需澄清
- 缺乏证据
- 未提及

Allowed overall risk levels:
- 低
- 中
- 高
- 证据不足

For each topic, assess each relevant structured standard clause. If several standard clauses are tightly related, you may create one assessment per clause or one assessment per topic, but preserve the clause IDs in the output.

User review request:
<review_request>
{review_request}
</review_request>

Topic-grouped evidence:
<topic_evidence>
{topic_evidence}
</topic_evidence>
"""


def format_evidence_block(items) -> str:
    """Format evidence items for model context."""

    if not items:
        return "No evidence found."
    lines: list[str] = []
    for index, item in enumerate(items, start=1):
        location_parts = []
        page_number = _field(item, "page_number")
        sheet_name = _field(item, "sheet_name")
        row_range = _field(item, "row_range")
        if page_number:
            location_parts.append(f"page {page_number}")
        if sheet_name:
            location_parts.append(f"sheet {sheet_name}")
        if row_range:
            location_parts.append(f"rows {row_range}")
        location = ", ".join(location_parts) or "location unavailable"
        lines.append(
            f"[{index}] Evidence ID: {_field(item, 'evidence_id') or 'unavailable'}\n"
            f"File: {_field(item, 'file_name')} ({location}, score={_field(item, 'score')})\n"
            f"Path: {_field(item, 'path')}\n"
            f"Excerpt:\n{_field(item, 'excerpt')}"
        )
    return "\n\n".join(lines)


def format_topic_evidence_block(topic_evidence: list[dict]) -> str:
    """Format topic-grouped evidence for the reviewer prompt."""

    if not topic_evidence:
        return "No topic evidence found."

    blocks: list[str] = []
    for item in topic_evidence:
        title = item.get('topic_title') or item.get('title', 'Unknown Topic')
        blocks.append(
            "\n".join(
                [
                    f"## {title}",
                    f"Expected evidence: {item.get('expected_evidence', '')}",
                    "",
                    "### Structured standard clauses",
                    format_clause_block(item.get("standard_clauses", [])),
                    "",
                    "### Official standard evidence",
                    format_evidence_block(item.get("standard_evidence", [])),
                    "",
                    "### Internal QMS evidence",
                    format_evidence_block(item.get("internal_evidence", [])),
                ]
            )
        )
    return "\n\n".join(blocks)


def format_clause_block(clauses: list[dict]) -> str:
    """Format structured standard clauses for reviewer context."""

    if not clauses:
        return "No structured clauses found."

    lines: list[str] = []
    for index, clause in enumerate(clauses, start=1):
        pages = _pages(clause)
        evidence = "; ".join(clause.get("expected_evidence", [])) or "TBD"
        summary = clause.get("requirement_summary") or clause.get("text", "")[:700]
        lines.append(
            "\n".join(
                [
                    f"[{index}] {clause.get('standard')} {clause.get('clause_id')} {clause.get('title')} ({pages})",
                    f"Expected evidence: {evidence}",
                    f"Requirement summary: {summary}",
                ]
            )
        )
    return "\n\n".join(lines)


def _field(item, name: str):
    """Read a field from either a Pydantic model or a plain dict."""

    if isinstance(item, dict):
        return item.get(name)
    return getattr(item, name, None)


def _pages(clause: dict) -> str:
    start = clause.get("page_start")
    end = clause.get("page_end")
    if start and end and start != end:
        return f"pages {start}-{end}"
    if start:
        return f"page {start}"
    return "pages unavailable"

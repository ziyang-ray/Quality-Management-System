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
            f"[{index}] {_field(item, 'file_name')} ({location}, score={_field(item, 'score')})\n"
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
        blocks.append(
            "\n".join(
                [
                    f"## {item['title']}",
                    f"Expected evidence: {item['expected_evidence']}",
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


def _field(item, name: str):
    """Read a field from either a Pydantic model or a plain dict."""

    if isinstance(item, dict):
        return item.get(name)
    return getattr(item, name, None)

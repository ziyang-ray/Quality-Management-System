"""Render structured compliance review objects into user-facing formats."""

from collections.abc import Iterable

from open_deep_research.compliance.schemas import ClauseAssessment, ComplianceReviewReport, EvidenceItem


DISCLAIMER = (
    "本报告由内部合规预审助手基于已索引文件生成，仅用于内部初步筛查；"
    "不能替代正式质量体系审核、法规判断或授权审批。"
)


def render_compliance_review_report(report: ComplianceReviewReport) -> str:
    """Render a structured compliance review report as Markdown."""

    lines: list[str] = [
        "# 合规预审报告",
        "",
        "## 审查范围",
        _clean(report.review_scope) or "未提供审查范围。",
        "",
        "## 总体结论",
        f"- 总体风险等级：{_clean(report.overall_risk_level)}",
        f"- 摘要：{_clean(report.overall_summary) or '暂无总体结论。'}",
        "",
        "## 条款符合性矩阵",
    ]

    if report.assessments:
        lines.extend(_assessment_matrix(report.assessments))
    else:
        lines.append("未生成条款级评估。")

    lines.extend(["", "## 潜在不符合项与风险"])
    risk_lines = [
        f"- {_clause_label(item)}：{_clean(item.risk)}"
        for item in report.assessments
        if _clean(item.risk) and item.status != "符合"
    ]
    lines.extend(risk_lines or ["未从当前证据中识别出明确潜在不符合项；仍需人工复核。"])

    lines.extend(["", "## 建议整改动作"])
    recommendation_lines = [
        f"- {_clause_label(item)}：{_clean(item.recommendation)}"
        for item in report.assessments
        if _clean(item.recommendation)
    ]
    lines.extend(recommendation_lines or ["暂无具体整改建议。"])

    lines.extend(["", "## 局限性"])
    lines.extend([f"- {_clean(item)}" for item in report.limitations if _clean(item)] or ["未声明额外局限性。"])

    lines.extend(["", "## 证据来源"])
    lines.extend(_all_evidence_lines(report.assessments) or ["未引用内部证据。"])

    lines.extend(["", "## 免责声明", DISCLAIMER])
    return "\n".join(lines).strip() + "\n"


def _assessment_matrix(assessments: Iterable[ClauseAssessment]) -> list[str]:
    lines = [
        "| 条款/主题 | 要求摘要 | 内部证据 | 判断 | 风险 | 建议 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in assessments:
        lines.append(
            "| "
            + " | ".join(
                [
                    _cell(_clause_label(item)),
                    _cell(item.requirement_summary),
                    _cell(_evidence_summary(item.evidence)),
                    _cell(item.status),
                    _cell(item.risk),
                    _cell(item.recommendation),
                ]
            )
            + " |"
        )
    return lines


def _evidence_summary(evidence: list[EvidenceItem]) -> str:
    if not evidence:
        return "未找到直接内部证据"
    parts = []
    for item in evidence[:3]:
        location = _location(item)
        evidence_id = f"[{item.evidence_id}] " if item.evidence_id else ""
        parts.append(f"{evidence_id}{item.file_name}{location}")
    if len(evidence) > 3:
        parts.append(f"另 {len(evidence) - 3} 条")
    return "; ".join(parts)


def _all_evidence_lines(assessments: Iterable[ClauseAssessment]) -> list[str]:
    seen: set[tuple[str, str, str, str]] = set()
    lines: list[str] = []
    for assessment in assessments:
        for evidence in assessment.evidence:
            key = (evidence.evidence_id, evidence.file_name, evidence.path, _location(evidence))
            if key in seen:
                continue
            seen.add(key)
            excerpt = _clean(evidence.excerpt)
            if len(excerpt) > 220:
                excerpt = excerpt[:217].rstrip() + "..."
            evidence_id = f"`{evidence.evidence_id}` " if evidence.evidence_id else ""
            lines.append(f"- {evidence_id}{evidence.file_name}{_location(evidence)}：{excerpt or evidence.path}")
    return lines


def _clause_label(item: ClauseAssessment) -> str:
    topic = f"{item.topic_title} / " if item.topic_title else ""
    standard = _clean(item.standard)
    clause = _clean(item.clause_id)
    if standard or clause:
        return f"{topic}{standard} {clause}".strip()
    return topic.rstrip(" /") or "未命名条款"


def _location(item: EvidenceItem) -> str:
    parts = []
    if item.page_number:
        parts.append(f"p.{item.page_number}")
    if item.sheet_name:
        parts.append(f"sheet {item.sheet_name}")
    if item.row_range:
        parts.append(f"rows {item.row_range}")
    return f" ({', '.join(parts)})" if parts else ""


def _cell(value) -> str:
    text = _clean(value)
    return text.replace("|", "\\|").replace("\n", "<br>") or "-"


def _clean(value) -> str:
    if value is None:
        return ""
    return str(value).strip()

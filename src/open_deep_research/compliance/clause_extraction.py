"""Rule-based extraction of standard clauses from PDF text."""

from __future__ import annotations

import re
from pathlib import Path

from open_deep_research.compliance.document_loader import load_file
from open_deep_research.compliance.schemas import ParsedDocumentElement, StandardClause


CLAUSE_LINE_RE = re.compile(r"^(?P<id>\d+(?:\.\d+){0,4})\s+(?P<title>\S.{0,140})$")
CLAUSE_ID_ONLY_RE = re.compile(r"^(?P<id>\d+(?:\.\d+){0,4})$")
ANNEX_RE = re.compile(r"^(附录|Annex)\b", re.IGNORECASE)
PAGE_NUMBER_RE = re.compile(r"^\d{1,4}$")


def extract_standard_clauses(pdf_path: str | Path, standard_name: str) -> list[StandardClause]:
    """Extract candidate clauses from one official PDF."""

    elements = load_file(pdf_path, "standard")
    elements = _drop_front_matter(elements, standard_name)
    clean_pages = [_clean_page(element) for element in elements]
    candidates = _find_clause_boundaries(clean_pages)
    return [_candidate_to_clause(candidate, standard_name, str(pdf_path)) for candidate in candidates]


def _clean_page(element: ParsedDocumentElement) -> dict:
    lines: list[str] = []
    for raw_line in element.text.splitlines():
        line = _normalize_line(raw_line)
        if not line:
            continue
        if PAGE_NUMBER_RE.match(line):
            continue
        if line.startswith("©") or line.startswith("ISO ") or line.startswith("INTERNATIONAL STANDARD"):
            continue
        lines.append(line)
    return {"page_number": element.page_number, "lines": lines}


def _drop_front_matter(elements: list[ParsedDocumentElement], standard_name: str) -> list[ParsedDocumentElement]:
    """Drop cover, copyright, and table-of-content pages for known standards."""

    start_page = 1
    if "13485" in standard_name or "14971" in standard_name:
        start_page = 9
    return [element for element in elements if (element.page_number or 1) >= start_page]


def _normalize_line(line: str) -> str:
    line = line.replace("\ufeff", "").replace("\xa0", " ")
    return re.sub(r"\s+", " ", line).strip()


def _find_clause_boundaries(pages: list[dict]) -> list[dict]:
    starts: list[dict] = []
    flattened: list[tuple[int | None, str]] = []
    for page in pages:
        for line in page["lines"]:
            flattened.append((page["page_number"], line))

    for index, (page_number, line) in enumerate(flattened):
        if starts and ANNEX_RE.match(line):
            break
        match = CLAUSE_LINE_RE.match(line)
        if match and _looks_like_clause(match.group("id"), match.group("title")):
            starts.append(
                {
                    "index": index,
                    "page_number": page_number,
                    "clause_id": match.group("id"),
                    "title": match.group("title").strip(),
                }
            )
            continue

        id_match = CLAUSE_ID_ONLY_RE.match(line)
        if id_match and index + 1 < len(flattened):
            next_line = flattened[index + 1][1]
            if _looks_like_clause(id_match.group("id"), next_line):
                starts.append(
                    {
                        "index": index,
                        "page_number": page_number,
                        "clause_id": id_match.group("id"),
                        "title": next_line.strip(),
                        "title_line_index": index + 1,
                    }
                )

    clauses: list[dict] = []
    for start_position, start in enumerate(starts):
        end_index = starts[start_position + 1]["index"] if start_position + 1 < len(starts) else len(flattened)
        body_start = start.get("title_line_index", start["index"]) + 1
        body_lines = [line for _, line in flattened[body_start:end_index]]
        if not body_lines and start["clause_id"].count(".") == 0:
            continue
        page_end = flattened[end_index - 1][0] if end_index > start["index"] else start["page_number"]
        clauses.append({**start, "text": "\n".join(body_lines).strip(), "page_end": page_end})
    return _dedupe_clauses(clauses)


def _looks_like_clause(clause_id: str, title: str) -> bool:
    if not title or len(title) < 2:
        return False
    if title.startswith(".") or set(title) <= {".", " "}:
        return False
    if "..." in title or "…" in title:
        return False
    first_number = int(clause_id.split(".")[0])
    if first_number == 0 or first_number > 12:
        return False
    # Avoid table rows that map ISO 13485 clauses to ISO 9001 clauses.
    if "ISO 9001" in title or "对应关系" in title:
        return False
    return True


def _dedupe_clauses(clauses: list[dict]) -> list[dict]:
    by_id: dict[str, dict] = {}
    for clause in clauses:
        current = by_id.get(clause["clause_id"])
        if current is None or len(clause["text"]) > len(current["text"]):
            by_id[clause["clause_id"]] = clause
    return sorted(by_id.values(), key=lambda item: [int(part) for part in item["clause_id"].split(".")])


def _candidate_to_clause(candidate: dict, standard_name: str, source_path: str) -> StandardClause:
    text = candidate["text"]
    title = candidate["title"]
    return StandardClause(
        standard=standard_name,
        clause_id=candidate["clause_id"],
        title=title,
        text=text,
        requirement_summary=_make_summary(text),
        expected_evidence=_expected_evidence(candidate["clause_id"], title, text),
        search_terms=_search_terms(candidate["clause_id"], title, text),
        source_path=source_path,
        page_start=candidate.get("page_number"),
        page_end=candidate.get("page_end"),
    )


def _make_summary(text: str, max_chars: int = 450) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= max_chars:
        return compact
    return compact[:max_chars].rsplit(" ", 1)[0] + "..."


def _expected_evidence(clause_id: str, title: str, text: str) -> list[str]:
    haystack = f"{clause_id} {title} {text}".lower()
    evidence: list[str] = []
    rules = [
        (("document", "文件控制", "4.2.4"), "文件批准、修订状态、分发控制、作废文件控制记录"),
        (("record", "记录控制", "4.2.5"), "记录标识、保存期限、检索、完整性和处置记录"),
        (("training", "competence", "培训", "6.2"), "人员能力要求、培训记录、有效性评价记录"),
        (("internal audit", "内部审核", "8.2.4"), "审核计划、审核报告、不符合项和纠正措施跟踪记录"),
        (("corrective", "纠正措施", "8.5.2"), "根因分析、纠正措施计划、实施证据、有效性评审记录"),
        (("preventive", "预防措施", "8.5.3"), "潜在不合格分析、预防措施计划、实施和有效性评审记录"),
        (("risk management", "风险管理", "risk control"), "风险管理计划、风险分析、风险评价、风险控制和残余风险记录"),
        (("supplier", "采购", "供方"), "供应商评价、选择、监视、再评价和采购验证记录"),
        (("nonconforming", "不合格品"), "不合格品识别、隔离、评价、处置和批准记录"),
        (("release", "放行", "产品的监视和测量"), "检验记录、放行授权、接收准则和产品符合性证据"),
    ]
    for needles, item in rules:
        if any(needle.lower() in haystack for needle in needles):
            evidence.append(item)
    return evidence


def _search_terms(clause_id: str, title: str, text: str) -> list[str]:
    terms = [clause_id, title]
    for token in re.findall(r"[A-Za-z][A-Za-z\-]{3,}|[\u4e00-\u9fff]{2,}", f"{title} {text}"):
        if token not in terms:
            terms.append(token)
        if len(terms) >= 14:
            break
    return terms

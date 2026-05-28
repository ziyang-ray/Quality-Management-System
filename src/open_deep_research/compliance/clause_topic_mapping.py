"""Mapping between review topics and specific standard clause IDs."""

import re
from dataclasses import dataclass

from open_deep_research.compliance.clause_store import ClauseStore
from open_deep_research.compliance.schemas import StandardClause


@dataclass(frozen=True)
class TopicClauseMapping:
    """A review topic bound to specific standard clause IDs."""

    topic_id: str
    title: str
    clause_refs: tuple[tuple[str, str], ...]  # (standard, clause_id)
    internal_query: str
    preferred_internal_terms: tuple[str, ...]
    expected_evidence: str
    aliases: tuple[str, ...]


TOPIC_CLAUSE_MAPPINGS: tuple[TopicClauseMapping, ...] = (
    TopicClauseMapping(
        topic_id="document_control",
        title="文件控制",
        clause_refs=(
            ("ISO 13485:2016", "4.2.4"),
        ),
        internal_query="Document Management 文件管理 document control approval revision obsolete distribution SAP stamp",
        preferred_internal_terms=("TP_001", "Document Management", "文件管理"),
        expected_evidence="文件评审批准、版本/修订状态、分发控制、外来文件控制、作废文件控制。",
        aliases=("文件", "文件控制", "document", "document control", "4.2.4"),
    ),
    TopicClauseMapping(
        topic_id="record_control",
        title="记录控制",
        clause_refs=(
            ("ISO 13485:2016", "4.2.5"),
        ),
        internal_query="record control 记录 控制 retention storage retrieval integrity DHR quality record",
        preferred_internal_terms=("record", "DHR", "记录"),
        expected_evidence="记录标识、储存、安全完整性、检索、保存期限、处置及保密控制。",
        aliases=("记录", "记录控制", "record", "quality record", "4.2.5"),
    ),
    TopicClauseMapping(
        topic_id="training_competence",
        title="培训与人员能力",
        clause_refs=(
            ("ISO 13485:2016", "6.2"),
        ),
        internal_query="Qualification and Training 资质 培训 competence awareness training record",
        preferred_internal_terms=("TP_005", "Qualification and Training", "资质", "培训"),
        expected_evidence="岗位能力要求、培训安排、培训记录、有效性评价、人员意识要求。",
        aliases=("培训", "资质", "能力", "training", "competence", "6.2"),
    ),
    TopicClauseMapping(
        topic_id="change_management",
        title="变更管理",
        clause_refs=(
            ("ISO 13485:2016", "4.2.4"),
            ("ISO 13485:2016", "7.3.9"),
            ("ISO 13485:2016", "7.3.10"),
        ),
        internal_query="Change Management 变更 change request engineering design change review approval impact evaluation",
        preferred_internal_terms=("TP_003", "Change Management", "变更"),
        expected_evidence="变更申请、影响评估、评审批准、实施验证、记录保存。",
        aliases=("变更", "change", "change management", "engineering change"),
    ),
    TopicClauseMapping(
        topic_id="capa",
        title="CAPA 与纠正预防措施",
        clause_refs=(
            ("ISO 13485:2016", "8.5.2"),
            ("ISO 13485:2016", "8.5.3"),
        ),
        internal_query="CAPA corrective preventive action root cause effectiveness Q-Gate correction quality reporting",
        preferred_internal_terms=("TP_020", "CAPA", "Q-Reporting"),
        expected_evidence="问题来源、根因分析、纠正/预防措施计划、责任人与期限、实施证据、有效性验证。",
        aliases=("capa", "纠正", "预防", "corrective", "preventive", "8.5.2", "8.5.3"),
    ),
    TopicClauseMapping(
        topic_id="internal_audit",
        title="内部审核",
        clause_refs=(
            ("ISO 13485:2016", "8.2.4"),
        ),
        internal_query="Internal Audit Procedure 内部审核 audit program audit plan audit report corrective action",
        preferred_internal_terms=("TP_032", "Internal Audit", "内部审核"),
        expected_evidence="审核方案、审核准则、审核计划、审核报告、不符合项跟踪、纠正措施验证。",
        aliases=("内部审核", "内审", "internal audit", "audit", "8.2.4"),
    ),
    TopicClauseMapping(
        topic_id="nonconforming_product",
        title="不合格品控制",
        clause_refs=(
            ("ISO 13485:2016", "8.3"),
        ),
        internal_query="Non-conforming Materials Procedure 不合格品 identification blocked area disposition concession",
        preferred_internal_terms=("TP_019", "Non-conforming", "不合格"),
        expected_evidence="不合格品识别、隔离、评审、处置、让步使用、记录及追溯。",
        aliases=("不合格", "不合格品", "nonconforming", "non-conforming", "8.3"),
    ),
    TopicClauseMapping(
        topic_id="supplier_quality",
        title="供应商质量管理",
        clause_refs=(
            ("ISO 13485:2016", "7.4.1"),
            ("ISO 13485:2016", "7.4.2"),
            ("ISO 13485:2016", "7.4.3"),
        ),
        internal_query="Supplier Quality Management Supplier Audits 供应商 采购 supplier audit action plan evaluation",
        preferred_internal_terms=("TP_038", "Supplier Quality", "供应商"),
        expected_evidence="供应商选择评价、采购信息、来料验证、供应商审核、问题跟踪与再评价。",
        aliases=("供应商", "采购", "supplier", "purchasing", "7.4"),
    ),
    TopicClauseMapping(
        topic_id="risk_management",
        title="风险管理接口",
        clause_refs=(
            ("ISO 13485:2016", "7.1"),
            ("ISO 14971:2019", "4.1"),
            ("ISO 14971:2019", "6"),
            ("ISO 14971:2019", "8"),
            ("ISO 14971:2019", "9"),
        ),
        internal_query="Risk Management Product Risk Management risk management file plan report production post-production review",
        preferred_internal_terms=("TP_037", "Risk Management", "风险"),
        expected_evidence="风险管理计划、风险管理文件、风险控制措施、生产和上市后信息回顾。",
        aliases=("风险", "风险管理", "risk", "risk management", "iso 14971"),
    ),
    TopicClauseMapping(
        topic_id="product_release_dhr",
        title="产品放行与 DHR",
        clause_refs=(
            ("ISO 13485:2016", "8.2.6"),
            ("ISO 13485:2016", "7.5.1"),
            ("ISO 13485:2016", "4.2.5"),
        ),
        internal_query="Final Inspection Product Release Device History Record DHR quality certificate release sheet",
        preferred_internal_terms=("TP_009", "TP_058", "Final Inspection", "DHR", "Product Release"),
        expected_evidence="最终检验、产品放行授权、质量证书、DHR 索引、生产/检验记录完整性。",
        aliases=("放行", "最终检验", "dhr", "device history", "product release", "final inspection"),
    ),
)


def select_topics_and_clauses(
    review_request: str,
    clause_store: ClauseStore,
    max_topics: int = 10,
) -> list[TopicClauseMapping]:
    """Select review topics based on user request and validate clause refs exist."""
    normalized = review_request.lower()
    broad_markers = ("iso 13485", "体系", "全", "模拟审核", "符合性", "qms")

    if any(marker in normalized for marker in broad_markers):
        selected = list(TOPIC_CLAUSE_MAPPINGS[:max_topics])
    else:
        selected = []
        for mapping in TOPIC_CLAUSE_MAPPINGS:
            if any(alias.lower() in normalized for alias in mapping.aliases):
                selected.append(mapping)
        if not selected:
            selected = list(TOPIC_CLAUSE_MAPPINGS[:max_topics])

    # Validate that clause refs exist in the store
    validated = []
    for mapping in selected:
        valid_refs = []
        for standard, clause_id in mapping.clause_refs:
            if clause_store.get_clause(standard, clause_id):
                valid_refs.append((standard, clause_id))
        if valid_refs:
            validated.append(mapping)

    return validated[:max_topics]


_CLAUSE_ID_PATTERN = re.compile(r"(\d+\.\d+(?:\.\d+)?)")


def select_clauses_directly(
    review_request: str,
    clause_store: ClauseStore,
    max_clauses: int = 50,
) -> list[StandardClause]:
    """Match clause IDs directly from user request text (e.g. '审查4.2.4和8.5.2')."""
    found_ids = _CLAUSE_ID_PATTERN.findall(review_request)
    if not found_ids:
        return []

    clauses = []
    seen = set()
    for clause_id in found_ids:
        # Try ISO 13485 first, then ISO 14971
        for standard in ("ISO 13485:2016", "ISO 14971:2019"):
            clause = clause_store.get_clause(standard, clause_id)
            if clause:
                key = (standard, clause_id)
                if key not in seen:
                    clauses.append(clause)
                    seen.add(key)
                break

    return clauses[:max_clauses]

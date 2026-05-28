"""Review topic selection for the ISO 13485 compliance MVP."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReviewTopic:
    """A bounded audit topic with search queries for standards and internal evidence."""

    topic_id: str
    title: str
    standard_clause_refs: tuple[tuple[str, str], ...]
    standard_query: str
    internal_query: str
    expected_evidence: str
    aliases: tuple[str, ...]
    preferred_internal_terms: tuple[str, ...] = ()
    related_topics: tuple[str, ...] = ()
    risk_indicators: tuple[str, ...] = ()


ISO_13485_MVP_TOPICS: tuple[ReviewTopic, ...] = (
    ReviewTopic(
        topic_id="document_control",
        title="文件控制",
        standard_clause_refs=(("ISO 13485:2016", "4.2.4"),),
        standard_query="ISO 13485 4.2.4 document control 文件控制 approval revision obsolete external documents",
        internal_query="Document Management 文件管理 document control approval revision obsolete distribution SAP stamp",
        expected_evidence="文件评审批准、版本/修订状态、分发控制、外来文件控制、作废文件控制。",
        aliases=("文件", "文件控制", "document", "document control", "4.2.4"),
        preferred_internal_terms=("TP_001", "Document Management", "文件管理"),
        related_topics=("record_control", "change_management"),
        risk_indicators=("文件未受控", "使用过期版本", "外来文件未审批", "作废文件仍在使用"),
    ),
    ReviewTopic(
        topic_id="record_control",
        title="记录控制",
        standard_clause_refs=(("ISO 13485:2016", "4.2.5"),),
        standard_query="ISO 13485 4.2.5 record control 记录控制 retention storage retrieval integrity confidentiality",
        internal_query="record control 记录 控制 retention storage retrieval integrity DHR quality record",
        expected_evidence="记录标识、储存、安全完整性、检索、保存期限、处置及保密控制。",
        aliases=("记录", "记录控制", "record", "quality record", "4.2.5"),
        preferred_internal_terms=("record", "DHR", "记录"),
        related_topics=("document_control", "product_release_dhr"),
        risk_indicators=("记录丢失", "保存期限不足", "记录不可追溯", "保密措施缺失"),
    ),
    ReviewTopic(
        topic_id="training_competence",
        title="培训与人员能力",
        standard_clause_refs=(("ISO 13485:2016", "6.2"),),
        standard_query="ISO 13485 6.2 human resources competence training awareness 人力资源 培训 能力",
        internal_query="Qualification and Training 资质 培训 competence awareness training record",
        expected_evidence="岗位能力要求、培训安排、培训记录、有效性评价、人员意识要求。",
        aliases=("培训", "资质", "能力", "training", "competence", "6.2"),
        preferred_internal_terms=("TP_005", "Qualification and Training", "资质", "培训"),
        related_topics=(),
        risk_indicators=("人员无资质上岗", "培训记录缺失", "培训有效性未评价"),
    ),
    ReviewTopic(
        topic_id="change_management",
        title="变更管理",
        standard_clause_refs=(("ISO 13485:2016", "4.1.4"),),
        standard_query="ISO 13485 change management process changes QMS process validation review approval 变更",
        internal_query="Change Management 变更 change request engineering design change review approval impact evaluation",
        expected_evidence="变更申请、影响评估、评审批准、实施验证、记录保存。",
        aliases=("变更", "change", "change management", "engineering change"),
        preferred_internal_terms=("TP_003", "Change Management", "变更"),
        related_topics=("document_control", "risk_management"),
        risk_indicators=("变更未评审批准", "影响评估不充分", "变更未验证"),
    ),
    ReviewTopic(
        topic_id="capa",
        title="CAPA 与纠正预防措施",
        standard_clause_refs=(
            ("ISO 13485:2016", "8.5.2"),
            ("ISO 13485:2016", "8.5.3"),
        ),
        standard_query="ISO 13485 8.5.2 纠正措施 8.5.3 预防措施 原因 措施 有效性 记录",
        internal_query="CAPA corrective preventive action root cause effectiveness Q-Gate correction quality reporting",
        expected_evidence="问题来源、根因分析、纠正/预防措施计划、责任人与期限、实施证据、有效性验证。",
        aliases=("capa", "纠正", "预防", "corrective", "preventive", "8.5.2", "8.5.3"),
        preferred_internal_terms=("TP_020", "CAPA", "Q-Reporting"),
        related_topics=("internal_audit", "nonconforming_product"),
        risk_indicators=("CAPA长期未关闭", "无根因分析", "有效性未验证", "重复发生同类问题"),
    ),
    ReviewTopic(
        topic_id="internal_audit",
        title="内部审核",
        standard_clause_refs=(("ISO 13485:2016", "8.2.4"),),
        standard_query="ISO 13485 8.2.4 internal audit audit program audit criteria records 内部审核",
        internal_query="Internal Audit Procedure 内部审核 audit program audit plan audit report corrective action",
        expected_evidence="审核方案、审核准则、审核计划、审核报告、不符合项跟踪、纠正措施验证。",
        aliases=("内部审核", "内审", "internal audit", "audit", "8.2.4"),
        preferred_internal_terms=("TP_032", "Internal Audit", "内部审核"),
        related_topics=("capa",),
        risk_indicators=("审核方案未覆盖所有过程", "审核员审核自己工作", "不符合项未关闭"),
    ),
    ReviewTopic(
        topic_id="nonconforming_product",
        title="不合格品控制",
        standard_clause_refs=(
            ("ISO 13485:2016", "8.3.1"),
            ("ISO 13485:2016", "8.3.2"),
            ("ISO 13485:2016", "8.3.3"),
            ("ISO 13485:2016", "8.3.4"),
        ),
        standard_query="ISO 13485 8.3 nonconforming product control identification segregation disposition 不合格品",
        internal_query="Non-conforming Materials Procedure 不合格品 identification blocked area disposition concession",
        expected_evidence="不合格品识别、隔离、评审、处置、让步使用、记录及追溯。",
        aliases=("不合格", "不合格品", "nonconforming", "non-conforming", "8.3"),
        preferred_internal_terms=("TP_019", "Non-conforming", "不合格"),
        related_topics=("capa", "supplier_quality"),
        risk_indicators=("不合格品未隔离", "处置记录缺失", "让步使用未审批"),
    ),
    ReviewTopic(
        topic_id="supplier_quality",
        title="供应商质量管理",
        standard_clause_refs=(
            ("ISO 13485:2016", "7.4.1"),
            ("ISO 13485:2016", "7.4.2"),
            ("ISO 13485:2016", "7.4.3"),
        ),
        standard_query="ISO 13485 7.4 purchasing supplier evaluation selection monitoring re-evaluation 采购 供应商",
        internal_query="Supplier Quality Management Supplier Audits 供应商 采购 supplier audit action plan evaluation",
        expected_evidence="供应商选择评价、采购信息、来料验证、供应商审核、问题跟踪与再评价。",
        aliases=("供应商", "采购", "supplier", "purchasing", "7.4"),
        preferred_internal_terms=("TP_038", "Supplier Quality", "供应商"),
        related_topics=("nonconforming_product",),
        risk_indicators=("供应商未评价", "来料未验证", "供应商问题未跟踪"),
    ),
    ReviewTopic(
        topic_id="risk_management",
        title="风险管理接口",
        standard_clause_refs=(
            ("ISO 13485:2016", "7.1"),
            ("ISO 13485:2016", "8.2.1"),
            ("ISO 14971:2019", "4.1"),
            ("ISO 14971:2019", "5"),
            ("ISO 14971:2019", "6"),
            ("ISO 14971:2019", "7"),
        ),
        standard_query="ISO 13485 risk management ISO 14971 risk management file production post-production information 风险管理",
        internal_query="Risk Management Product Risk Management risk management file plan report production post-production review",
        expected_evidence="风险管理计划、风险管理文件、风险控制措施、生产和上市后信息回顾。",
        aliases=("风险", "风险管理", "risk", "risk management", "iso 14971"),
        preferred_internal_terms=("TP_037", "Risk Management", "风险"),
        related_topics=("change_management", "product_release_dhr"),
        risk_indicators=("风险管理文件缺失", "风险控制措施未实施", "上市后信息未回顾"),
    ),
    ReviewTopic(
        topic_id="product_release_dhr",
        title="产品放行与 DHR",
        standard_clause_refs=(
            ("ISO 13485:2016", "7.5.1"),
            ("ISO 13485:2016", "8.2.6"),
            ("ISO 13485:2016", "4.2.5"),
        ),
        standard_query="ISO 13485 8.2.6 产品的监视和测量 7.5.1 生产和服务提供控制 放行 记录 4.2.5",
        internal_query="Final Inspection Product Release Device History Record DHR quality certificate release sheet",
        expected_evidence="最终检验、产品放行授权、质量证书、DHR 索引、生产/检验记录完整性。",
        aliases=("放行", "最终检验", "dhr", "device history", "product release", "final inspection"),
        preferred_internal_terms=("TP_009", "TP_058", "Final Inspection", "DHR", "Product Release"),
        related_topics=("record_control", "risk_management"),
        risk_indicators=("DHR不完整", "放行未授权", "检验记录缺失"),
    ),
)


def select_review_topics(review_request: str, max_topics: int = 10) -> list[ReviewTopic]:
    """Select explicit review topics from the user request, defaulting to the MVP set."""

    normalized = review_request.lower()
    broad_markers = ("iso 13485", "体系", "全", "模拟审核", "符合性", "qms")
    if any(marker in normalized for marker in broad_markers):
        return list(ISO_13485_MVP_TOPICS[:max_topics])

    selected: list[ReviewTopic] = []
    selected_ids: set[str] = set()
    for topic in ISO_13485_MVP_TOPICS:
        if any(alias.lower() in normalized for alias in topic.aliases):
            selected.append(topic)
            selected_ids.add(topic.topic_id)

    if selected:
        expanded: list[ReviewTopic] = []
        for topic in selected:
            expanded.append(topic)
            for related_id in topic.related_topics:
                if related_id not in selected_ids:
                    related_topic = get_topic_by_id(related_id)
                    if related_topic:
                        expanded.append(related_topic)
                        selected_ids.add(related_id)
        return expanded[:max_topics]
    return list(ISO_13485_MVP_TOPICS[:max_topics])


def get_topic_by_id(topic_id: str) -> ReviewTopic | None:
    """Get a topic by its ID."""

    for topic in ISO_13485_MVP_TOPICS:
        if topic.topic_id == topic_id:
            return topic
    return None


def get_topic_by_alias(alias: str) -> ReviewTopic | None:
    """Get a topic by one of its aliases."""

    alias_lower = alias.lower()
    for topic in ISO_13485_MVP_TOPICS:
        if any(a.lower() == alias_lower for a in topic.aliases):
            return topic
    return None


def get_all_topics() -> list[ReviewTopic]:
    """Get all available review topics."""

    return list(ISO_13485_MVP_TOPICS)


def get_topics_by_standard(standard: str) -> list[ReviewTopic]:
    """Get all topics that reference a specific standard."""

    return [
        topic for topic in ISO_13485_MVP_TOPICS
        if any(ref[0] == standard for ref in topic.standard_clause_refs)
    ]

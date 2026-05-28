# QMS合规审查系统 - 进阶改进计划

## 背景

当前系统是一个**一次性RAG**（检索增强生成），虽然能工作，但过于简单，缺乏深度。为了在简历和面试中更有竞争力，需要增加以下维度：

1. **记忆系统** - 跨会话的审查历史和学习能力
2. **多智能体协作** - 模拟真实审核场景的多个角色
3. **高级检索** - 语义检索、混合检索、上下文感知
4. **评估框架** - 量化审查质量，持续优化
5. **可视化和交互** - 更专业的用户体验

---

## 改进路线图

### 阶段1：记忆系统（1-2周）

**目标**：让系统能够"记住"之前的审查结果，避免重复工作，积累知识。

#### 1.1 审查历史记忆

```python
# 新增：src/open_deep_research/compliance/memory/review_history.py

class ReviewHistory:
    """审查历史记忆"""
    
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self.history: list[ReviewSession] = []
    
    def save_session(self, session: ReviewSession):
        """保存审查会话"""
        ...
    
    def get_clause_history(self, clause_id: str) -> list[ClauseAssessment]:
        """获取某个条款的历史评估"""
        ...
    
    def get_trend(self, clause_id: str) -> TrendAnalysis:
        """分析条款符合性的趋势"""
        ...
```

**数据结构**：
```python
@dataclass
class ReviewSession:
    session_id: str
    timestamp: datetime
    request: str
    assessments: list[ClauseAssessment]
    confirmed_by: Optional[str]  # 人工确认者
    notes: str

@dataclass
class TrendAnalysis:
    clause_id: str
    status_history: list[tuple[datetime, ReviewStatus]]
    improvement_notes: list[str]
    risk_level: str  # "improving", "stable", "declining"
```

#### 1.2 纠正措施跟踪

```python
# 新增：src/open_deep_research/compliance/memory/capa_tracker.py

class CAPATracker:
    """纠正措施生命周期跟踪"""
    
    def create_capa(self, finding: Finding) -> CAPA:
        """从审查发现创建CAPA"""
        ...
    
    def update_status(self, capa_id: str, status: CAPAStatus):
        """更新CAPA状态"""
        ...
    
    def get_overdue_capas(self) -> list[CAPA]:
        """获取超期未关闭的CAPA"""
        ...
    
    def generate_follow_up_report(self) -> str:
        """生成CAPA跟踪报告"""
        ...
```

**数据结构**：
```python
@dataclass
class CAPA:
    capa_id: str
    source_finding: Finding
    root_cause: str
    corrective_action: str
    preventive_action: str
    responsible_person: str
    due_date: datetime
    status: CAPAStatus  # OPEN, IN_PROGRESS, VERIFIED, CLOSED
    effectiveness_check: Optional[EffectivenessCheck]
```

#### 1.3 查询调优记忆

```python
# 新增：src/open_deep_research/compliance/memory/query_memory.py

class QueryMemory:
    """查询调优记忆"""
    
    def record_feedback(self, query: str, clause_id: str, 
                       relevant: bool, feedback: str):
        """记录查询反馈"""
        ...
    
    def get_optimized_query(self, clause_id: str) -> str:
        """获取优化后的查询"""
        ...
    
    def get_synonyms(self, term: str) -> list[str]:
        """获取术语同义词"""
        ...
```

**存储格式**：
```json
{
  "clause_id": "8.5.2",
  "original_query": "CAPA corrective action",
  "optimized_queries": [
    "corrective action preventive action root cause effectiveness",
    "纠正措施 预防措施 根因分析 有效性验证"
  ],
  "synonyms": {
    "CAPA": ["纠正和预防措施", "corrective and preventive action"],
    "root cause": ["根本原因", "root cause analysis"]
  },
  "feedback_history": [
    {"date": "2026-05-28", "relevant": true, "note": "找到了TP_020"}
  ]
}
```

---

### 阶段2：多智能体协作（2-3周）

**目标**：模拟真实审核场景，多个AI角色协作完成审查。

#### 2.1 角色定义

```python
# 新增：src/open_deep_research/compliance/agents/roles.py

class AuditRole(Enum):
    """审核角色"""
    LEAD_AUDITOR = "lead_auditor"          # 主审核员
    TECHNICAL_EXPERT = "technical_expert"   # 技术专家
    QUALITY_MANAGER = "quality_manager"     # 质量经理
    DOCUMENT_CONTROL = "document_control"   # 文控专员
    DEPARTMENT_REP = "department_rep"       # 部门代表

@dataclass
class AgentProfile:
    """智能体档案"""
    role: AuditRole
    name: str
    expertise: list[str]
    personality: str  # 严谨、灵活、批判性等
    focus_areas: list[str]
    questioning_style: str
```

#### 2.2 智能体实现

```python
# 新增：src/open_deep_research/compliance/agents/lead_auditor.py

class LeadAuditorAgent:
    """主审核员智能体"""
    
    def __init__(self, profile: AgentProfile):
        self.profile = profile
        self.findings: list[Finding] = []
        self.questions: list[Question] = []
    
    def plan_audit(self, scope: AuditScope) -> AuditPlan:
        """制定审核计划"""
        ...
    
    def review_evidence(self, clause: StandardClause, 
                       evidence: list[EvidenceItem]) -> Assessment:
        """审核证据"""
        ...
    
    def ask_follow_up(self, assessment: Assessment) -> Question:
        """提出跟进问题"""
        ...
    
    def make_judgment(self, all_evidence: list[Evidence]) -> Judgment:
        """做出最终判断"""
        ...
```

```python
# 新增：src/open_deep_research/compliance/agents/department_rep.py

class DepartmentRepAgent:
    """部门代表智能体（被审核方）"""
    
    def respond_to_question(self, question: Question, 
                          available_docs: list[Document]) -> Response:
        """回答审核员问题"""
        ...
    
    def provide_evidence(self, requirement: str) -> list[Evidence]:
        """提供证据"""
        ...
    
    def explain_process(self, process_name: str) -> str:
        """解释流程"""
        ...
```

#### 2.3 协作工作流

```python
# 新增：src/open_deep_research/compliance/agents/orchestrator.py

class AuditOrchestrator:
    """审核协调器"""
    
    def __init__(self):
        self.lead_auditor = LeadAuditorAgent(...)
        self.technical_expert = TechnicalExpertAgent(...)
        self.department_rep = DepartmentRepAgent(...)
        self.quality_manager = QualityManagerAgent(...)
    
    def conduct_audit(self, scope: AuditScope) -> AuditReport:
        """执行完整审核流程"""
        
        # 1. 主审核员制定计划
        plan = self.lead_auditor.plan_audit(scope)
        
        # 2. 部门代表准备材料
        self.department_rep.prepare_documents(plan)
        
        # 3. 逐条款审核
        for clause in plan.clauses:
            # 主审核员审核证据
            assessment = self.lead_auditor.review_evidence(clause)
            
            # 如果需要，技术专家参与
            if assessment.needs_expert_review:
                expert_opinion = self.technical_expert.analyze(clause, assessment)
                assessment.merge_expert_opinion(expert_opinion)
            
            # 部门代表回应
            if assessment.has_questions:
                response = self.department_rep.respond_to_questions(
                    assessment.questions
                )
                assessment.update_with_response(response)
            
            # 质量经理审核
            self.quality_manager.review_assessment(assessment)
        
        # 4. 生成最终报告
        return self.lead_auditor.generate_final_report()
```

#### 2.4 对话模拟

```python
# 新增：src/open_deep_research/compliance/agents/dialogue.py

class AuditDialogue:
    """审核对话模拟"""
    
    def simulate_interview(self, clause: StandardClause, 
                         department: str) -> DialogueHistory:
        """模拟审核访谈"""
        
        dialogue = DialogueHistory()
        
        # 主审核员开场
        dialogue.add(self.lead_auditor.opening_statement(clause))
        
        # 部门代表回应
        dialogue.add(self.department_rep.introduce_process(clause))
        
        # 审核员追问
        for question in self.lead_auditor.generate_questions(clause):
            dialogue.add(question)
            response = self.department_rep.answer(question)
            dialogue.add(response)
            
            # 如果回答不充分，继续追问
            if not response.is_satisfactory():
                follow_up = self.lead_auditor.follow_up(question, response)
                dialogue.add(follow_up)
                dialogue.add(self.department_rep.answer(follow_up))
        
        # 审核员总结
        dialogue.add(self.lead_auditor.summarize_findings())
        
        return dialogue
```

---

### 阶段3：高级检索（1-2周）

**目标**：从关键词匹配升级到语义理解。

#### 3.1 向量检索

```python
# 新增：src/open_deep_research/compliance/retrieval/vector_retriever.py

class VectorRetriever:
    """向量检索器"""
    
    def __init__(self, embedding_model: str = "text-embedding-3-small"):
        self.embedding_model = embedding_model
        self.index: Optional[faiss.Index] = None
        self.documents: list[Document] = []
    
    def build_index(self, documents: list[Document]):
        """构建向量索引"""
        embeddings = self._embed_documents(documents)
        self.index = faiss.IndexFlatL2(len(embeddings[0]))
        self.index.add(embeddings)
        self.documents = documents
    
    def search(self, query: str, top_k: int = 10) -> list[SearchResult]:
        """语义搜索"""
        query_embedding = self._embed_query(query)
        scores, indices = self.index.search(query_embedding, top_k)
        return [SearchResult(doc=self.documents[i], score=s) 
                for i, s in zip(indices[0], scores[0])]
```

#### 3.2 混合检索

```python
# 新增：src/open_deep_research/compliance/retrieval/hybrid_retriever.py

class HybridRetriever:
    """混合检索器（BM25 + 向量）"""
    
    def __init__(self):
        self.bm25_retriever = ComplianceRetriever(...)
        self.vector_retriever = VectorRetriever(...)
    
    def search(self, query: str, top_k: int = 10) -> list[SearchResult]:
        """混合搜索"""
        # BM25结果
        bm25_results = self.bm25_retriever.search(query, top_k=top_k*2)
        
        # 向量结果
        vector_results = self.vector_retriever.search(query, top_k=top_k*2)
        
        # 融合排序（RRF - Reciprocal Rank Fusion）
        fused_results = self._reciprocal_rank_fusion(
            bm25_results, vector_results, k=60
        )
        
        return fused_results[:top_k]
    
    def _reciprocal_rank_fusion(self, *result_lists, k=60):
        """RRF融合算法"""
        scores = {}
        for results in result_lists:
            for rank, result in enumerate(results):
                doc_id = result.doc.id
                if doc_id not in scores:
                    scores[doc_id] = 0
                scores[doc_id] += 1 / (k + rank + 1)
        
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

#### 3.3 上下文感知检索

```python
# 新增：src/open_deep_research/compliance/retrieval/context_aware.py

class ContextAwareRetriever:
    """上下文感知检索"""
    
    def search_with_context(self, clause: StandardClause, 
                           audit_context: AuditContext) -> list[SearchResult]:
        """考虑审核上下文的检索"""
        
        # 基础查询
        base_query = " ".join(clause.search_terms)
        
        # 根据上下文扩展查询
        expanded_query = self._expand_query(base_query, audit_context)
        
        # 检索
        results = self.hybrid_retriever.search(expanded_query)
        
        # 根据上下文重排序
        reranked = self._rerank_with_context(results, audit_context)
        
        return reranked
    
    def _expand_query(self, query: str, context: AuditContext) -> str:
        """根据上下文扩展查询"""
        expansions = []
        
        # 如果是内审，添加内审相关术语
        if context.audit_type == "internal_audit":
            expansions.extend(["内审", "internal audit", "审核发现"])
        
        # 如果是外审，添加认证相关术语
        if context.audit_type == "external_audit":
            expansions.extend(["认证", "certification", "不符合项"])
        
        # 根据部门添加相关术语
        if context.department:
            expansions.extend(self._get_department_terms(context.department))
        
        return query + " " + " ".join(expansions)
```

---

### 阶段4：评估框架（1周）

**目标**：量化审查质量，持续优化。

#### 4.1 Golden Test Set

```python
# 新增：tests/golden_test_set.py

GOLDEN_TEST_CASES = [
    {
        "id": "TC-001",
        "clause_id": "8.5.2",
        "clause_title": "纠正措施",
        "internal_evidence_files": ["TP_020_CAPA.pdf"],
        "expected_status": "符合",
        "expected_rationale_contains": ["根因分析", "有效性验证"],
        "difficulty": "easy"
    },
    {
        "id": "TC-002",
        "clause_id": "7.4.1",
        "clause_title": "采购过程",
        "internal_evidence_files": [],
        "expected_status": "缺乏证据",
        "expected_rationale_contains": [],
        "difficulty": "medium"
    },
    # ... 更多测试用例
]
```

#### 4.2 评估指标

```python
# 新增：src/open_deep_research/compliance/evaluation/metrics.py

class ComplianceMetrics:
    """合规审查评估指标"""
    
    @staticmethod
    def status_accuracy(predicted: ReviewStatus, 
                       expected: ReviewStatus) -> float:
        """状态准确率"""
        return 1.0 if predicted == expected else 0.0
    
    @staticmethod
    def evidence_relevance(retrieved: list[EvidenceItem],
                          relevant_files: list[str]) -> float:
        """证据相关性"""
        if not relevant_files:
            return 1.0 if not retrieved else 0.0
        
        retrieved_files = {e.file_name for e in retrieved}
        relevant_set = set(relevant_files)
        
        intersection = retrieved_files & relevant_set
        precision = len(intersection) / len(retrieved_files) if retrieved_files else 0
        recall = len(intersection) / len(relevant_set)
        
        if precision + recall == 0:
            return 0.0
        return 2 * precision * recall / (precision + recall)
    
    @staticmethod
    def rationale_quality(rationale: str, 
                         expected_keywords: list[str]) -> float:
        """理由质量"""
        if not expected_keywords:
            return 1.0
        
        found = sum(1 for kw in expected_keywords if kw in rationale)
        return found / len(expected_keywords)
```

#### 4.3 自动评估

```python
# 新增：src/open_deep_research/compliance/evaluation/evaluator.py

class ComplianceEvaluator:
    """合规审查自动评估器"""
    
    def evaluate_system(self, test_cases: list[TestCase]) -> EvaluationReport:
        """评估整个系统"""
        results = []
        
        for case in test_cases:
            # 运行审查
            report = self.run_review(case.clause_id)
            
            # 评估结果
            result = self.evaluate_case(case, report)
            results.append(result)
        
        # 汇总
        return EvaluationReport(
            total_cases=len(results),
            accuracy=sum(r.status_accuracy for r in results) / len(results),
            evidence_recall=sum(r.evidence_recall for r in results) / len(results),
            rationale_quality=sum(r.rationale_quality for r in results) / len(results),
            details=results
        )
```

---

### 阶段5：可视化和交互（1-2周）

**目标**：提供更专业的用户体验。

#### 5.1 Web界面

```python
# 新增：src/open_deep_research/compliance/ui/app.py

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/")
async def home():
    return HTMLResponse("""
    <html>
        <head><title>QMS Compliance Reviewer</title></head>
        <body>
            <h1>QMS合规审查系统</h1>
            <form action="/review" method="post">
                <textarea name="request" placeholder="输入审查请求..."></textarea>
                <button type="submit">开始审查</button>
            </form>
        </body>
    </html>
    """)

@app.post("/review")
async def run_review(request: str):
    # 运行审查
    report = await compliance_reviewer.ainvoke(...)
    return {"report": report}
```

#### 5.2 可视化报告

```python
# 新增：src/open_deep_research/compliance/visualization/report_viz.py

class ReportVisualizer:
    """报告可视化"""
    
    def create_dashboard(self, report: ComplianceReviewReport) -> str:
        """创建仪表板"""
        html = f"""
        <html>
        <head>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        </head>
        <body>
            <h1>合规审查仪表板</h1>
            
            <!-- 状态分布饼图 -->
            <div id="status-pie"></div>
            <script>
                Plotly.newPlot('status-pie', [{{
                    values: [{report.status_counts['符合']}, 
                            {report.status_counts['需澄清']},
                            {report.status_counts['缺乏证据']},
                            {report.status_counts['未提及']}],
                    labels: ['符合', '需澄清', '缺乏证据', '未提及'],
                    type: 'pie'
                }}]);
            </script>
            
            <!-- 条款详情表格 -->
            <table>
                <tr>
                    <th>条款</th>
                    <th>状态</th>
                    <th>风险</th>
                    <th>建议</th>
                </tr>
                {"".join(f'''
                <tr>
                    <td>{a.clause_id}</td>
                    <td class="{a.status}">{a.status}</td>
                    <td>{a.risk[:50]}...</td>
                    <td>{a.recommendation[:50]}...</td>
                </tr>
                ''' for a in report.assessments)}
            </table>
        </body>
        </html>
        """
        return html
```

---

## 简历亮点提炼

### 技术亮点

1. **多智能体系统**
   - 设计了5种审核角色的智能体
   - 实现了角色间的协作和对话模拟
   - 使用LangGraph编排复杂工作流

2. **记忆系统**
   - 审查历史记忆：跨会话的审查结果追踪
   - 纠正措施跟踪：CAPA生命周期管理
   - 查询调优记忆：自动优化检索策略

3. **混合检索**
   - BM25 + 向量检索的融合
   - RRF（Reciprocal Rank Fusion）排序算法
   - 上下文感知的查询扩展

4. **评估框架**
   - Golden Test Set设计
   - 多维度评估指标（准确率、召回率、理由质量）
   - 自动化评估流水线

5. **系统设计**
   - 模块化架构，易于扩展
   - 结构化输出，便于程序化处理
   - 完整的溯源链路

### 业务价值

1. **效率提升**
   - 自动化审查减少人工工作量80%+
   - 标准化的审查流程
   - 可追溯的审查历史

2. **质量保证**
   - 基于证据的判断，避免主观臆断
   - 持续的评估和优化
   - 知识积累和复用

3. **合规支持**
   - ISO 13485/14971全覆盖
   - 审计准备和模拟
   - 纠正措施跟踪

---

## 实施计划

### 第1阶段：记忆系统（1-2周）

**Week 1**：
- 实现审查历史存储
- 实现CAPA跟踪
- 集成到审查工作流

**Week 2**：
- 实现查询调优记忆
- 添加趋势分析
- 测试和优化

### 第2阶段：多智能体（2-3周）

**Week 3**：
- 定义智能体角色和档案
- 实现主审核员智能体
- 实现部门代表智能体

**Week 4**：
- 实现协调器
- 实现对话模拟
- 集成测试

**Week 5**：
- 添加技术专家和质量经理
- 优化协作流程
- 端到端测试

### 第3阶段：高级检索（1-2周）

**Week 6**：
- 实现向量检索
- 实现混合检索
- 性能优化

**Week 7**：
- 实现上下文感知检索
- 评估检索质量
- 调优参数

### 第4阶段：评估框架（1周）

**Week 8**：
- 设计Golden Test Set
- 实现评估指标
- 建立评估流水线

### 第5阶段：可视化（1-2周）

**Week 9-10**：
- 实现Web界面
- 实现可视化报告
- 用户测试和优化

---

## 验证方法

### 单元测试

```bash
# 记忆系统测试
python -m pytest tests/test_memory.py -v

# 多智能体测试
python -m pytest tests/test_agents.py -v

# 检索测试
python -m pytest tests/test_retrieval.py -v
```

### 集成测试

```bash
# 端到端审查测试
python -m pytest tests/test_end_to_end.py -v

# 多智能体协作测试
python -m pytest tests/test_multi_agent.py -v
```

### 评估测试

```bash
# 运行Golden Test Set
python scripts/run_evaluation.py --test-set golden

# 生成评估报告
python scripts/generate_eval_report.py
```

---

## 关键文件清单

### 新增文件

```
src/open_deep_research/compliance/
├── memory/
│   ├── __init__.py
│   ├── review_history.py
│   ├── capa_tracker.py
│   └── query_memory.py
├── agents/
│   ├── __init__.py
│   ├── roles.py
│   ├── lead_auditor.py
│   ├── department_rep.py
│   ├── technical_expert.py
│   ├── quality_manager.py
│   └── orchestrator.py
├── retrieval/
│   ├── __init__.py
│   ├── vector_retriever.py
│   ├── hybrid_retriever.py
│   └── context_aware.py
├── evaluation/
│   ├── __init__.py
│   ├── metrics.py
│   └── evaluator.py
└── visualization/
    ├── __init__.py
    └── report_viz.py

tests/
├── test_memory.py
├── test_agents.py
├── test_retrieval.py
├── test_evaluation.py
└── golden_test_set.py

scripts/
├── run_evaluation.py
└── generate_eval_report.py
```

### 修改文件

```
src/open_deep_research/compliance_reviewer.py  # 集成记忆系统
src/open_deep_research/compliance/retrieval.py  # 升级为混合检索
src/open_deep_research/configuration.py         # 新增配置项
```

---

## 总结

这个改进计划将项目从一个**简单的RAG系统**升级为**企业级的智能审核平台**：

1. **记忆系统** → 让系统能够学习和积累
2. **多智能体** → 模拟真实审核场景
3. **高级检索** → 提升证据召回率
4. **评估框架** → 量化和持续优化
5. **可视化** → 提供专业用户体验

这些改进将使项目在简历上成为**强有力的亮点**，展示：
- 系统架构设计能力
- AI Agent开发经验
- 多智能体协作设计
- 评估和优化能力
- 企业级应用开发经验

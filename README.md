# Quality Management System Compliance Assistant

基于 LangGraph 的西门子医疗内部质量体系合规审查 Agent 系统。

按 ISO 13485:2016 / ISO 14971:2019 标准条款，对内部 QMS 文件进行证据驱动的自动化预审。

## 功能

- **条款级审查**：按具体标准条款（如 8.5.2 纠正措施）逐条审查
- **主题级审查**：按审查主题（CAPA、内部审核、供应商管理等）分组审查
- **多智能体协作**：法规审核员 + 内部QMS审核员 + 风险评审员 + 审计总监
- **知识图谱**：条款 → 流程 → 程序 → 记录的证据链导航
- **技能包**：部门审核经验沉淀，支持 YAML 格式 + 审批流程
- **审计记忆**：审查历史、人工反馈、行动跟踪的持久化
- **流式输出**：实时显示审查进度和报告生成过程

## 快速开始

### 1. 环境要求

- Python >= 3.10
- API Key（OpenAI / Anthropic / 自定义 API）

### 2. 安装依赖

```bash
cd open_deep_research-main
pip install -e .
```

### 3. 配置 API

复制 `.env.example` 为 `.env`，填入你的 API Key：

```bash
cp .env.example .env
```

`.env` 文件内容：

```bash
# API 配置（三选一）
OPENAI_API_KEY=your-key-here
# 或
ANTHROPIC_API_KEY=your-key-here
# 或自定义 API
OPENAI_API_KEY=your-key-here
OPENAI_API_BASE=https://your-api-endpoint/v1

# 模型配置
FINAL_REPORT_MODEL=anthropic:claude-3-5-sonnet-20241022
```

### 4. 构建索引

首次使用需要构建文档索引：

```bash
# 构建证据索引（扫描 data/official_docs 和 data/internal_docs）
python scripts/build_compliance_index.py

# 构建知识图谱
python scripts/build_initial_knowledge_graph.py
```

### 5. 运行审查

```bash
# 预览证据（不调用 LLM，用于调试检索质量）
python scripts/preview_compliance_review.py --request "请审查 CAPA" --full

# 生成审查报告
python scripts/run_compliance_review.py --request "请审查 CAPA" --output reports/capa.md

# 流式输出
python scripts/run_compliance_review.py --request "请审查 CAPA" --stream

# 多智能体审查
python scripts/run_multi_agent_review.py
```

## 项目结构

```
open_deep_research-main/
├── src/open_deep_research/
│   ├── compliance_reviewer.py      # 合规审查 LangGraph 工作流
│   ├── compliance/                 # 合规模块
│   │   ├── schemas.py              #   20 个 Pydantic 数据模型
│   │   ├── document_loader.py      #   PDF/DOCX/XLSX/XLSM 解析
│   │   ├── chunking.py             #   文本切分（1800字符/chunk）
│   │   ├── retrieval.py            #   BM25 检索引擎
│   │   ├── clause_extraction.py    #   标准条款自动抽取
│   │   ├── clause_store.py         #   条款库管理
│   │   ├── knowledge_graph.py      #   轻量知识图谱
│   │   ├── skill_loader.py         #   部门技能包加载
│   │   ├── review_memory.py        #   审计记忆系统
│   │   ├── evidence_planner.py     #   证据检索规划器
│   │   ├── compliance_orchestra.py #   多智能体编排
│   │   ├── review_topics.py        #   10 个 MVP 审查主题
│   │   ├── prompts.py              #   提示词模板
│   │   └── renderers.py            #   Markdown 报告渲染
│   └── configuration.py            # 统一配置
├── scripts/                        # CLI 工具
├── tests/                          # 测试
└── data/
    ├── official_docs/              # ISO 标准原文（不入 Git）
    ├── internal_docs/              # 内部 QMS 文件（不入 Git）
    ├── compliance_index/           # 证据索引
    ├── standard_clauses/           # 条款库（198 条）
    ├── compliance_graph/           # 知识图谱
    ├── skills/                     # 技能包
    └── review_memory/              # 审计记忆
```

## 审查主题

系统内置 10 个 ISO 13485 MVP 审查主题：

| 主题 | 条款 | 说明 |
|------|------|------|
| 文件控制 | 4.2.4 | 文件评审批准、版本控制、分发 |
| 记录控制 | 4.2.5 | 记录标识、储存、保存期限 |
| 培训与人员能力 | 6.2 | 岗位能力、培训记录、有效性 |
| 变更管理 | 4.1.4 | 变更申请、影响评估、验证 |
| CAPA | 8.5.2, 8.5.3 | 纠正措施、预防措施 |
| 内部审核 | 8.2.4 | 审核方案、审核报告、不符合项 |
| 不合格品控制 | 8.3.1-8.3.4 | 识别、隔离、处置、让步 |
| 供应商质量管理 | 7.4.1-7.4.3 | 供应商评价、来料验证 |
| 风险管理接口 | 7.1, 8.2.1, ISO 14971 | 风险管理文件、风险控制 |
| 产品放行与 DHR | 7.5.1, 8.2.6 | 最终检验、DHR 完整性 |

## 使用示例

### 审查单个条款

```python
import asyncio
from scripts.run_clause_review import review_single_clause

asyncio.run(review_single_clause("ISO 13485:2016", "8.5.2"))
```

### 自定义审查请求

```bash
# 审查多个主题
python scripts/run_compliance_review.py \
  --request "请审查 CAPA、内部审核和不合格品控制" \
  --output reports/review.md

# 保存证据包和结构化报告
python scripts/run_compliance_review.py \
  --request "请审查供应商质量管理" \
  --artifacts-dir runs
```

## 技术栈

- **Agent 框架**：LangGraph >= 0.5.4
- **LLM 集成**：LangChain（支持 OpenAI / Anthropic / Google / DeepSeek / Groq）
- **数据模型**：Pydantic v2
- **文档解析**：pymupdf, python-docx, openpyxl
- **检索算法**：BM25（k1=1.5, b=0.75）+ 元数据加权
- **知识图谱**：JSONL 轻量图谱（7 种关系类型）
- **输出格式**：Markdown + JSON 结构化

## 数据安全

- 内部文件和标准原文**不推入 Git 仓库**
- 默认**禁用公网搜索**（`external_search_allowed=false`）
- 每个结论必须有**可追溯的 evidence_id**
- 无证据的"符合"判断**自动降级为"缺乏证据"**
- 审计记忆中**只有人工确认的内容**才影响后续审查

## License

MIT

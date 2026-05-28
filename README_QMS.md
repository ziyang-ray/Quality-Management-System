# QMS Compliance Reviewer

基于 Open Deep Research 改造的 QMS 合规审查系统，用于西门子医疗内部质量管理体系文件的自动化预审。

## 项目概述

本项目将通用的AI研究代理改造为专业的合规审查工具，能够：

- 自动解析ISO标准（ISO 13485:2016、ISO 14971:2019）并提取条款
- 索引内部QMS文件（PDF/Word/Excel）
- 根据标准条款逐条审查内部文件的符合性
- 生成结构化的审查报告

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        准备阶段（一次性）                         │
├─────────────────────────────────────────────────────────────────┤
│  [ISO标准PDF] ──→ 条款提取 ──→ clauses.jsonl (198条)            │
│  [内部QMS文件] ──→ 索引构建 ──→ chunks.jsonl (1270+块)          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        审查阶段（每次运行）                       │
├─────────────────────────────────────────────────────────────────┤
│  用户请求 ──→ 解析范围 ──→ 检索证据 ──→ AI判断 ──→ 审查报告      │
└─────────────────────────────────────────────────────────────────┘
```

## 文件结构

```
QMS--main/
├── src/open_deep_research/
│   ├── compliance/                    # 合规模块
│   │   ├── schemas.py                 # 数据模型定义
│   │   ├── document_loader.py         # 文档解析（PDF/DOCX/XLSX）
│   │   ├── chunking.py                # 文本分块
│   │   ├── index_store.py             # 索引存储
│   │   ├── retrieval.py               # BM25检索引擎
│   │   ├── clause_extraction.py       # ISO条款提取
│   │   ├── clause_store.py            # 条款存储与查询
│   │   ├── clause_topic_mapping.py    # 主题-条款映射
│   │   ├── review_topics.py           # 审查主题定义
│   │   ├── prompts.py                 # AI提示词模板
│   │   └── compliance_tools.py        # LangChain工具
│   ├── compliance_reviewer.py         # 审查工作流（LangGraph）
│   └── configuration.py               # 配置管理
├── scripts/
│   ├── extract_standard_clauses.py    # 条款提取脚本
│   ├── build_compliance_index.py      # 索引构建脚本
│   └── run_compliance_review.py       # 审查运行脚本
├── tests/                             # 测试文件
├── 文件/                              # 本地文件（不提交到Git）
│   ├── 官方文件/                      # ISO标准PDF
│   └── 内部文件/                      # 西门子QMS文件
└── data/                              # 生成数据（不提交到Git）
    ├── standard_clauses/              # 条款库
    └── compliance_index/              # 证据索引
```

## 快速开始

### 1. 安装依赖

```bash
# 使用 pip
pip install -e .

# 或使用 uv（推荐）
uv sync
```

### 2. 准备文件

将文件放在指定位置：
- **官方标准**：`文件/官方文件/`
  - `ISO13485-2016中文版.pdf`
  - `EN-ISO-14971-2019-Application-of-risk-management.pdf`
- **内部QMS文件**：`文件/内部文件/`（支持PDF/DOCX/XLSX/XLSM格式）

### 3. 构建数据（一次性）

```bash
# 提取ISO条款
python scripts/extract_standard_clauses.py --official-docs "文件/官方文件"

# 构建证据索引
python scripts/build_compliance_index.py \
  --official-docs "文件/官方文件" \
  --internal-docs "文件/内部文件"
```

### 4. 配置API密钥

```bash
# 使用OpenAI
export OPENAI_API_KEY="your-api-key"

# 或使用Anthropic
export ANTHROPIC_API_KEY="your-api-key"
export ANTHROPIC_BASE_URL="https://your-proxy-url"  # 可选
```

### 5. 运行审查

```bash
# 审查特定主题
python scripts/run_compliance_review.py \
  --request "请审查文件控制、记录控制和CAPA" \
  --model "anthropic:claude-sonnet-4-20250514"

# 完整ISO 13485审核
python scripts/run_compliance_review.py \
  --request "请进行ISO 13485模拟审核" \
  --model "anthropic:claude-sonnet-4-20250514" \
  --output reports/full_audit.md
```

## 审查范围

系统覆盖ISO 13485:2016的10个核心领域：

| 主题 | 条款 | 内部文件 |
|------|------|----------|
| 文件控制 | 4.2.4 | TP_001 Document Management |
| 记录控制 | 4.2.5 | DHR相关文件 |
| 培训与能力 | 6.2 | TP_005 Qualification and Training |
| 变更管理 | 7.3.9/7.3.10 | TP_003 Change Management |
| CAPA | 8.5.2/8.5.3 | TP_020 CAPA and Q-Reporting |
| 内部审核 | 8.2.4 | TP_032 Internal Audit |
| 不合格品 | 8.3 | TP_019 Non-conforming Materials |
| 供应商质量 | 7.4.1-7.4.3 | TP_038 Supplier Quality Management |
| 风险管理 | ISO 14971 | TP_037 Risk Management |
| 产品放行 | 8.2.6/7.5.1 | TP_009/TP_058 Final Inspection/DHR |

## 审查结果说明

每个条款的评估结果分为四类：

| 状态 | 含义 | 后续动作 |
|------|------|----------|
| **符合** | 内部证据直接支持合规 | 无需行动 |
| **需澄清** | 证据部分或模糊 | 需要补充说明或证据 |
| **缺乏证据** | 存在相关证据但未覆盖要求 | 需要补充完整证据 |
| **未提及** | 无相关内部证据 | 需要建立程序或文件 |

## 输出示例

审查报告包含以下部分：

1. **审查范围**：本次审查覆盖的条款
2. **总体结论**：各状态统计
3. **条款符合性矩阵**：逐条评估结果
4. **潜在不符合项**：需要关注的问题
5. **建议整改动作**：具体的改进建议
6. **局限性**：系统的已知限制

## 配置选项

在 `configuration.py` 中可配置：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `official_docs_path` | `G:\合规助手\官方文件` | 官方标准文件路径 |
| `internal_docs_path` | `G:\合规助手\部门内部文件` | 内部QMS文件路径 |
| `compliance_index_path` | `data/compliance_index` | 证据索引目录 |
| `clause_store_path` | `data/standard_clauses/clauses.jsonl` | 条款库路径 |
| `final_report_model` | `openai:gpt-4.1` | AI模型选择 |

## 测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试
python -m pytest tests/test_clause_store.py -v
```

## 技术栈

- **LangGraph**：工作流引擎
- **LangChain**：AI模型调用
- **Pydantic**：数据模型验证
- **PyMuPDF**：PDF解析
- **python-docx**：Word解析
- **openpyxl**：Excel解析

## 已知限制

1. **文件格式**：仅支持PDF/DOCX/XLSX/XLSM，不支持旧格式（.doc/.xls/.pptx）
2. **检索方式**：基于BM25关键词检索，可能遗漏语义相关但措辞不同的证据
3. **条款库**：自动提取的候选条款，部分可能需要人工校验
4. **覆盖范围**：当前仅覆盖ISO 13485的10个核心领域

## 后续计划

- [ ] 支持旧格式文件（.doc/.xls/.pptx）
- [ ] 建立测试用例集，量化审查准确率
- [ ] 审查记忆系统（历史记录、纠正措施跟踪）
- [ ] 多智能体协作

## 许可证

MIT License

## 致谢

基于 [Open Deep Research](https://github.com/langchain-ai/open_deep_research) 改造。

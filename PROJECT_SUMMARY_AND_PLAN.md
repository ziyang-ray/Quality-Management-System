# QMS Compliance Agent Project Summary And Plan

Date: 2026-05-28

## Summary

This project adapts `open_deep_research-main` into an evidence-driven compliance review agent for Siemens Healthineers internal QMS documents.

The current priority is solution B: a compliance matrix backed by standard clauses and internal document evidence. Solution C, a multi-agent audit platform, is intentionally left for a later phase after retrieval and evidence quality are stable.

## Completed

### Compliance Module

Added `src/open_deep_research/compliance/` with:

- `schemas.py`: structured document chunks, evidence items, standard clauses, and review objects.
- `document_loader.py`: PDF, DOCX, XLSX, and XLSM parsing.
- `chunking.py`: traceable chunking with file/page/sheet metadata.
- `index_store.py`: local JSONL index persistence.
- `retrieval.py`: local BM25-style retrieval with topic-aware metadata boosting.
- `review_topics.py`: ISO 13485 MVP review topics.
- `prompts.py`: evidence-driven review prompt and evidence formatting.
- `compliance_tools.py`: local compliance retrieval tools.
- `clause_extraction.py`: rule-based standard clause extraction from PDF text.

### Scripts

Added:

- `scripts/build_compliance_index.py`
- `scripts/inspect_compliance_index.py`
- `scripts/preview_compliance_review.py`
- `scripts/run_compliance_review.py`
- `scripts/extract_standard_clauses.py`

Current index result:

```text
Files seen: 148
Files indexed: 118
Chunks: 1177
Skipped files: 30
```

Skipped files are mostly legacy `.doc`, `.xls`, `.pptx`, and PDFs with no extractable text.

### Compliance Reviewer Graph

Added `src/open_deep_research/compliance_reviewer.py` and registered it in `langgraph.json`:

```json
"Compliance Reviewer": "./src/open_deep_research/compliance_reviewer.py:compliance_reviewer"
```

Current flow:

```text
User review request
-> prepare review request
-> select review topics
-> retrieve official standard evidence and internal QMS evidence by topic
-> generate compliance report with LLM
```

LLM initialization is lazy to avoid local Anaconda `torch` CUDA DLL failures during indexing and retrieval tests.

### ISO 13485 MVP Topics

Current MVP topics:

1. Document control
2. Record control
3. Training and competence
4. Change management
5. CAPA
6. Internal audit
7. Nonconforming product
8. Supplier quality management
9. Risk management interface
10. Product release and DHR

Each topic includes:

- `topic_id`
- title
- standard query
- internal query
- expected evidence
- aliases
- preferred internal file terms

CAPA, internal audit, and DHR retrieval were previewed and tuned.

### Standard Clause Extraction

Added candidate clause extraction for official PDFs.

Run:

```powershell
python scripts\extract_standard_clauses.py
```

Outputs:

```text
data/standard_clauses/clauses.jsonl
data/standard_clauses/clauses_review.md
```

Current extraction result:

```text
ISO 13485:2016: 141 candidate clauses
ISO 14971:2019: 57 candidate clauses
Total: 198 candidate clauses
```

Key clauses verified by spot check:

- ISO 13485 4.2.4 Document control
- ISO 13485 4.2.5 Record control
- ISO 13485 8.2.4 Internal audit
- ISO 13485 8.5.2 Corrective action
- ISO 13485 8.5.3 Preventive action
- ISO 14971 1 Scope
- ISO 14971 3.25 Risk management file
- ISO 14971 4.1 Risk management process
- ISO 14971 6 Risk evaluation
- ISO 14971 8 Evaluation of overall residual risk
- ISO 14971 9 Risk management review

The clause library is currently marked as `candidate` and should be reviewed before becoming the authoritative review source.

### Usage Documentation

Added `COMPLIANCE_USAGE.md`.

Primary workflow:

```powershell
python scripts\build_compliance_index.py
python scripts\preview_compliance_review.py --request "Please review CAPA, internal audit, and DHR"
python scripts\extract_standard_clauses.py
python scripts\run_compliance_review.py --request "Please review CAPA, internal audit, and DHR" --output reports\capa_audit.md
```

LangGraph Studio can also be used:

```powershell
uvx --refresh --from "langgraph-cli[inmem]" --with-editable . --python 3.11 langgraph dev --allow-blocking
```

### Tests

Current test result:

```text
6 passed
```

Warnings are from existing Pydantic/LangGraph deprecated APIs and do not block current functionality.

## Important Decisions

### Push Code Only

The GitHub repository should contain code and documentation only.

Do not push:

- `G:\合规助手\官方文件`
- `G:\合规助手\部门内部文件`
- generated local indexes under `data/`

Reasons:

- ISO standards may have copyright restrictions.
- Internal QMS documents are confidential.
- The codebase should be decoupled from local or enterprise knowledge stores.

### Build Evidence First, Then Agents

The system should first stabilize:

```text
standard clauses
-> internal evidence
-> evidence package
-> structured judgment
```

Multi-agent collaboration should come after evidence quality is stable.

### Memory System Later

The useful memory for this domain is audit memory, not chat memory:

- review history
- human-confirmed findings
- query tuning history
- corrective action follow-up

Avoid autonomous self-learning of compliance rules.

## Next Plan

### Phase 1: Stabilize Clause Library

Review `data/standard_clauses/clauses_review.md`.

Add status values:

- `approved`
- `needs_fix`
- `ignore`

Prioritize:

- ISO 13485 4.2.4
- ISO 13485 4.2.5
- ISO 13485 6.2
- ISO 13485 7.4
- ISO 13485 8.2.4
- ISO 13485 8.3
- ISO 13485 8.5.2
- ISO 13485 8.5.3
- ISO 14971 risk management process clauses

### Phase 2: Connect Clause Store To Reviewer

Add `clause_store.py`.

Support:

- load `clauses.jsonl`
- query by `standard + clause_id`
- map review topics to specific clause IDs
- build topic evidence packages

### Phase 3: Structured Output

Move LLM output from free Markdown to JSON first, then render Markdown/Excel.

Required statuses:

- 符合
- 需澄清
- 缺乏证据
- 未提及

### Phase 4: Improve File Coverage

Handle skipped files:

- convert legacy `.doc` to `.docx` or PDF
- support `.xls`
- support `.pptx`
- add OCR for PDFs with no extractable text

### Phase 5: Semi-Automated Retrieval Evaluation

Add `evaluate_compliance_retrieval.py`.

Evaluate:

- standard clause hit
- internal main-file hit
- ranking quality
- evidence coverage, manually scored

### Phase 6: Review Memory

Add persistent review memory:

- audit history
- confirmed findings
- query tuning notes
- corrective action lifecycle

### Phase 7: Multi-Agent Version

Upgrade to multi-agent architecture:

- standard clause agent
- internal evidence agent
- compliance judgment agent
- risk and remediation agent
- report generation agent
- human review coordinator

## Recommended Next Step

When continuing work:

1. Review `data/standard_clauses/clauses_review.md`.
2. Add `clause_store.py`.
3. Bind `review_topics.py` topics to clause IDs.
4. Build evidence packages from clause library plus internal evidence.
5. Then test prompt quality and structured output.

Guiding principle:

```text
Get the clauses and evidence right before asking the LLM to judge.
```

# QMS Compliance Agent Project Summary And Plan

Date: 2026-05-28

## Project Direction

This project adapts `open_deep_research-main` into an evidence-driven internal QMS compliance review agent for Siemens Healthineers use cases.

Current strategic choice:

- First build solution B: a reliable clause-driven compliance review assistant.
- Keep solution C, the fuller multi-agent audit platform, as a later career-strengthening extension.

The guiding principle is:

```text
Get clauses and evidence right before making the agent more autonomous.
```

## What Works Now

### 1. Local Compliance Knowledge Pipeline

Added `src/open_deep_research/compliance/` as a dedicated compliance domain module.

Current module responsibilities:

- `schemas.py`: Pydantic models for chunks, evidence, standard clauses, clause assessments, and final review reports.
- `document_loader.py`: parses PDF, DOCX, XLSX, and XLSM files.
- `chunking.py`: creates traceable chunks with file/page/sheet metadata.
- `index_store.py`: persists a local JSONL compliance index.
- `retrieval.py`: performs local BM25-style retrieval with topic-aware preferred-term boosting.
- `review_topics.py`: defines ISO 13485 MVP review topics and maps them to standard clause references.
- `prompts.py`: formats evidence and defines both free-text and structured review prompts.
- `clause_extraction.py`: extracts candidate clauses from official standard PDFs.
- `clause_store.py`: loads structured standard clauses from `data/standard_clauses/clauses.jsonl`.
- `renderers.py`: renders structured `ComplianceReviewReport` objects into Markdown.

### 2. Indexing And Retrieval

The local document index has been built from official and internal folders.

Current index result:

```text
Files seen: 148
Files indexed: 118
Chunks: 1177
Skipped files: 30
```

Skipped files are mainly legacy `.doc`, `.xls`, `.pptx`, or PDFs with no extractable text.

Important: generated indexes and source documents should remain local and should not be pushed to GitHub.

### 3. ISO 13485 MVP Topics

The current MVP scope contains 10 review topics:

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

Each topic now includes:

- `topic_id`
- title
- official standard query
- internal evidence query
- expected evidence
- aliases
- preferred internal file terms
- structured standard clause references

This is the beginning of true clause-driven review.

### 4. Standard Clause Library

The extraction script creates:

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

Spot-checked useful clauses include:

- ISO 13485 4.2.4 Document control
- ISO 13485 4.2.5 Record control
- ISO 13485 8.2.4 Internal audit
- ISO 13485 8.5.2 Corrective action
- ISO 13485 8.5.3 Preventive action
- ISO 14971 3.25 Risk management file
- ISO 14971 4.1 Risk management process
- ISO 14971 6 Risk evaluation
- ISO 14971 8 Evaluation of overall residual risk
- ISO 14971 9 Risk management review

The library is still marked as candidate quality. It is useful now, but should be reviewed before being treated as authoritative.

### 5. Clause-Driven Review Flow

The current compliance reviewer graph is:

```text
User review request
-> prepare review request
-> select review topics
-> retrieve structured standard clauses
-> retrieve official standard evidence
-> retrieve internal QMS evidence
-> generate structured review output
-> render Markdown report
```

This differs from the earlier flow because the LLM is no longer asked to infer the relevant requirements only from retrieved text snippets. The system first provides explicit clause objects, then asks the LLM to judge internal evidence against those clauses.

This reduces drift and makes the output easier to test.

### 6. Structured Output

The report generation path now prefers structured output:

```text
ComplianceReviewReport
-> ClauseAssessment[]
-> EvidenceItem[]
-> Markdown renderer
```

If structured model output fails, the reviewer falls back to the older free-text Markdown prompt.

Current guardrail:

- any `符合` assessment without cited internal evidence is automatically downgraded to `缺乏证据`
- cited internal evidence is hydrated from the retrieved evidence package by `evidence_id`
- evidence IDs that do not exist in the retrieval package are removed and recorded in limitations

Benefits:

- easier regression tests
- easier future Excel export
- easier frontend rendering
- easier audit trail
- easier human review and correction

### 7. Scripts

Useful commands:

```powershell
python scripts\build_compliance_index.py
python scripts\inspect_compliance_index.py
python scripts\extract_standard_clauses.py
python scripts\preview_compliance_review.py --request "Please review CAPA"
python scripts\evaluate_compliance_retrieval.py --internal-top-k 3
python scripts\run_compliance_review.py --request "Please review CAPA, internal audit, and DHR" --output reports\capa_audit.md
```

To keep full review artifacts:

```powershell
python scripts\run_compliance_review.py --request "Please review CAPA" --artifacts-dir runs
```

This writes:

- `evidence_package.json`
- `structured_report.json`
- `report.md`

Latest CAPA preview result:

```text
Selected topics: 1
Structured clauses:
- ISO 13485:2016 8.5.2
- ISO 13485:2016 8.5.3
Internal evidence:
- [83adf708fc1d2642d484d72e] CAPA Report.docx
- [b6bbf0c20cc9e4898fc41abc] CAPA and Q report.pdf
```

Latest retrieval evaluation result:

```text
Topics: 10
Clause coverage: 9/10
Internal evidence coverage: 10/10
```

### 8. Tests

Current focused test result:

```text
10 passed
```

The warnings are from existing Pydantic/LangGraph deprecated APIs and do not block current functionality.

## Important Design Choices

### Evidence First

For compliance work, the dangerous failure mode is not “the answer is ugly”; it is “the answer sounds confident without evidence.”

So the project should optimize in this order:

1. correct clause library
2. correct internal evidence retrieval
3. structured judgment
4. report rendering
5. user experience and automation

### Local By Default

External search should remain disabled by default for internal QMS review.

Reasons:

- internal documents may be confidential
- ISO standards may have copyright restrictions
- audit results need traceable local evidence

### Memory Should Be Audit Memory

Do not prioritize generic chatbot memory.

Useful memory for this project means:

- previous review runs
- human-confirmed findings
- false positive and false negative retrieval cases
- query tuning decisions
- CAPA follow-up status
- accepted clause interpretations

Compliance rules should not be silently rewritten by the model. Human-approved memory should be explicit and traceable.

## Recommended Optimization Plan

### Phase 1: Stabilize The Clause Library

Goal: turn candidate extracted clauses into trusted clause objects.

Actions:

- review `data/standard_clauses/clauses_review.md`
- add `extraction_status` values such as `approved`, `needs_fix`, `ignore`
- manually fix missing or split clauses for high-value ISO 13485 and ISO 14971 sections
- enrich each approved clause with:
  - requirement summary
  - expected evidence
  - search terms

Priority clauses:

- ISO 13485 4.2.4
- ISO 13485 4.2.5
- ISO 13485 6.2
- ISO 13485 7.4
- ISO 13485 8.2.4
- ISO 13485 8.3
- ISO 13485 8.5.2
- ISO 13485 8.5.3
- ISO 14971 risk management process clauses

### Phase 2: Tool Calling

Goal: expose compliance actions as deterministic tools instead of hiding everything inside one graph node.

Recommended tools:

- `search_standard_clauses(standard, clause_id, query)`
- `search_internal_evidence(query, topic_id, top_k)`
- `get_compliance_index_summary()`
- `get_review_topic(topic_id)`
- `render_compliance_report(report_json)`

Why this matters:

- tool calls create inspectable intermediate steps
- the UI can show progress by tool result
- future agents can reuse the same tools
- retrieval can be evaluated separately from generation

### Phase 3: Function Calling And Structured Output

Goal: make model output contract-based.

Current work already started this with:

- `ComplianceReviewReport`
- `ClauseAssessment`
- `EvidenceItem`

Next improvements:

- add stricter schema descriptions for each field
- require evidence IDs instead of free-form evidence text
- validate that cited evidence exists in the retrieved package
- reject impossible statuses, for example `符合` with no internal evidence
- add automatic retry when schema validation fails

This is one of the highest-return improvements because it turns the LLM into a component inside a controlled workflow rather than the owner of the whole result.

### Phase 4: ReAct, But Only For Evidence Gathering

ReAct is useful later, but should not be the first optimization.

Recommended use:

```text
Think about missing evidence
-> call search tools
-> inspect results
-> call more focused search tools
-> stop when enough evidence or clear gap
```

Do not use ReAct as an unbounded compliance decision loop.

Good limits:

- max 3-5 tool calls per topic
- no external search unless explicitly enabled
- final judgment must cite retrieved evidence
- every tool call should be logged

### Phase 5: Memory System

Goal: remember review outcomes and human feedback, not casual conversation.

Recommended memory tables or JSONL stores:

- `review_runs`: request, timestamp, selected topics, final report
- `human_feedback`: assessment ID, user correction, accepted status
- `retrieval_feedback`: query, expected file, actual rank, notes
- `clause_overrides`: approved summary, expected evidence, search terms
- `action_followups`: finding, owner, due date, closure evidence

Memory write policy:

- never auto-approve new compliance rules
- store model outputs separately from human-approved facts
- keep source document references with every memory item
- allow deletion and export

### Phase 6: Streamable HTTP And UI

Goal: make the assistant usable without reading terminal output.

Recommended path:

1. use LangGraph Studio for near-term debugging
2. expose a small API for review runs
3. stream progress events to the frontend
4. add a lightweight review UI

Useful streamed events:

- request parsed
- topics selected
- clauses loaded
- official evidence retrieved
- internal evidence retrieved
- structured report generated
- Markdown rendered
- warnings and limitations

The UI should show the evidence package before the final conclusion. For compliance work, transparency is more valuable than a flashy chat screen.

### Phase 7: Harness Engineering

Goal: build an evaluation harness so improvements do not rely on vibe checks.

Recommended test sets:

- 10 ISO 13485 MVP topic requests
- expected topic selection
- expected standard clause IDs
- expected internal files in top 3 or top 5
- manually scored report quality

Metrics:

- topic selection accuracy
- standard clause hit rate
- internal main-file hit rate
- evidence coverage
- citation correctness
- unsupported compliance claim count
- schema validation pass rate

This is where the project becomes genuinely impressive: not just an agent demo, but an agent system with measurable quality.

### Phase 8: Better File Coverage

Goal: reduce missing evidence caused by file format limitations.

Actions:

- convert legacy `.doc` to `.docx` or PDF
- add `.xls` support
- add `.pptx` support
- add OCR for scanned PDFs
- add a skipped-file review report after each indexing run

### Phase 9: Multi-Agent Platform

Only after retrieval, schema, and evaluation are stable, upgrade to a multi-agent system.

Possible agents:

- Standard Clause Agent
- Internal Evidence Agent
- Risk Judgment Agent
- Remediation Planning Agent
- Report Generation Agent
- Human Review Coordinator

The important architectural idea:

```text
Agents should share evidence objects, not vague chat messages.
```

## Near-Term Next Steps

Recommended next coding order:

1. Fix the missing ISO 14971 structured clause extraction around risk management sections.
2. Add stricter validation rules for impossible or unsupported conclusions.
3. Add human feedback files for retrieval corrections and accepted findings.
4. Start a simple UI or LangGraph Studio workflow after the output artifacts are stable.
5. Add streamable progress events for topic selection, evidence retrieval, and report generation.

## Current Status

The project has moved from “RAG over internal files” to the beginning of a real clause-driven compliance review system.

The strongest current achievement is:

```text
ISO clause object
+ official standard evidence
+ internal QMS evidence
+ stable evidence_id traceability
+ structured assessment schema
+ rendered audit-style Markdown
```

This is the right foundation for tool calling, memory, streaming UI, and eventually multi-agent collaboration.

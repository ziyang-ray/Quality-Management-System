# QMS Compliance Agent Architecture, TODO, And Acceptance Checklist

Date: 2026-05-28

## 1. Current Architecture

The project is now a clause-driven compliance review system built on top of `open_deep_research-main`.

Current flow:

```text
Official standards + internal QMS documents
-> document loading
-> chunking with traceable metadata
-> local JSONL index
-> structured standard clause library
-> review topic selection
-> clause and evidence retrieval
-> structured LLM judgment
-> guardrails and evidence hydration
-> Markdown / JSON artifacts
-> retrieval evaluation
```

The core architectural idea is:

```text
The LLM should judge only after the system has assembled clauses and traceable evidence.
```

## 2. Main Modules

### Document And Index Layer

Purpose: turn files into searchable, traceable chunks.

Files:

- `src/open_deep_research/compliance/document_loader.py`
- `src/open_deep_research/compliance/chunking.py`
- `src/open_deep_research/compliance/index_store.py`
- `scripts/build_compliance_index.py`
- `scripts/inspect_compliance_index.py`

Current capability:

- supports PDF, DOCX, XLSX, XLSM
- preserves file path, file name, page, sheet, row range
- generates stable `chunk_id`
- writes local JSONL index

Current limitation:

- legacy `.doc`, `.xls`, `.pptx`, and scanned PDFs are not fully covered

### Clause Library Layer

Purpose: turn ISO 13485 / ISO 14971 text into structured clause objects.

Files:

- `src/open_deep_research/compliance/clause_extraction.py`
- `src/open_deep_research/compliance/clause_store.py`
- `scripts/extract_standard_clauses.py`

Current capability:

- extracts candidate clauses from official PDFs
- stores clauses as JSONL
- loads clauses by `standard + clause_id`
- maps review topics to clause references

Current limitation:

- ISO 14971 risk management sections still need cleanup
- clauses are candidate quality, not fully approved

### Review Topic Layer

Purpose: map user requests to bounded audit topics.

Files:

- `src/open_deep_research/compliance/review_topics.py`

Current capability:

- supports 10 ISO 13485 MVP topics
- stores standard query, internal query, expected evidence, aliases, preferred internal terms
- maps topics to structured standard clause references

Current limitation:

- topic selection is rule-based
- no clarification step if the request is ambiguous

### Retrieval Layer

Purpose: retrieve official and internal evidence with traceable IDs.

Files:

- `src/open_deep_research/compliance/retrieval.py`
- `scripts/preview_compliance_review.py`

Current capability:

- local BM25-style retrieval
- filters by `source_type`
- boosts preferred topic terms
- returns `EvidenceItem` with stable `evidence_id`

Current limitation:

- no semantic embedding retrieval yet
- no reranker yet
- no manual feedback loop for bad retrieval cases

### Judgment And Report Layer

Purpose: produce structured assessments and user-facing reports.

Files:

- `src/open_deep_research/compliance/schemas.py`
- `src/open_deep_research/compliance/prompts.py`
- `src/open_deep_research/compliance/renderers.py`
- `src/open_deep_research/compliance_reviewer.py`
- `scripts/run_compliance_review.py`

Current capability:

- generates `ComplianceReviewReport`
- renders Markdown report
- saves `evidence_package.json`, `structured_report.json`, and `report.md`
- falls back to free-text report if structured output fails
- downgrades `符合` to `缺乏证据` if no traceable internal evidence exists
- hydrates cited evidence from the retrieved evidence package by `evidence_id`
- removes invented evidence IDs

Current limitation:

- no Excel export yet
- no reviewer feedback workflow yet
- no UI evidence-click-through yet

### Evaluation Layer

Purpose: make quality measurable.

Files:

- `scripts/evaluate_compliance_retrieval.py`
- `tests/test_compliance_index.py`

Current capability:

- evaluates the 10 MVP topics
- reports clause coverage
- reports internal evidence coverage
- shows top evidence IDs and files
- focused tests currently pass

Current latest result:

```text
Topics: 10
Clause coverage: 9/10
Internal evidence coverage: 10/10
Tests: 10 passed
```

Current limitation:

- no report-quality scoring yet
- no golden dataset yet
- no citation correctness evaluation against final reports yet

## 3. Current Functional Successes

The project already has these successful foundations:

- local confidential document processing
- ISO 13485 MVP topic framework
- candidate ISO 13485 / ISO 14971 clause library
- clause-driven evidence packages
- stable `evidence_id` traceability
- structured report schema
- Markdown report rendering
- guardrails against unsupported `符合` conclusions
- CLI artifact output
- first retrieval evaluation harness

The most important success is:

```text
Evidence is now an object with an ID, not just text in a prompt.
```

That makes later UI, memory, evaluation, and multi-agent collaboration much easier.

## 4. Prioritized TODO List

### P0: Make The Current MVP Trustworthy

- [ ] Fix ISO 14971 risk management clause extraction gaps.
- [ ] Review and approve the most important clauses in `data/standard_clauses/clauses_review.md`.
- [ ] Add clause approval statuses: `approved`, `needs_fix`, `ignore`.
- [ ] Add richer `requirement_summary`, `expected_evidence`, and `search_terms` for approved clauses.
- [ ] Add validation that every final assessment cites only known `evidence_id` values.
- [ ] Add validation that a clause cannot be marked `符合` unless at least one internal evidence ID is cited.
- [ ] Add JSON artifacts to every report run by default or through a clear CLI flag.

### P1: Make Retrieval Measurable And Tunable

- [ ] Expand `evaluate_compliance_retrieval.py` into a golden-case harness.
- [ ] Add expected internal files for all 10 MVP topics.
- [ ] Score whether expected files appear in top 3 / top 5.
- [ ] Save evaluation history under `reports/evaluations/`.
- [ ] Add a retrieval feedback file for false positives and false negatives.
- [ ] Use retrieval feedback to tune topic queries and preferred terms.
- [ ] Add optional semantic retrieval or reranking after the BM25 baseline is stable.

### P2: Make Review Outputs Easier To Use

- [ ] Add Excel export for the clause compliance matrix.
- [ ] Add report metadata: run ID, timestamp, model, index path, clause library path.
- [ ] Add one folder per review run containing evidence package, structured report, Markdown, and evaluation notes.
- [ ] Add a simple command to open or inspect evidence by `evidence_id`.
- [ ] Add summary tables by status: `符合`, `需澄清`, `缺乏证据`, `未提及`.

### P3: Add Human Feedback And Memory

- [ ] Add `data/review_memory/` or `runs/feedback/` structure.
- [ ] Store human corrections separately from model output.
- [ ] Store accepted findings with source evidence IDs.
- [ ] Store retrieval tuning notes by topic.
- [ ] Store clause summary overrides only after human approval.
- [ ] Add a script to apply approved feedback to future runs.

### P4: Add Tool Calling And ReAct-Like Evidence Gathering

- [ ] Convert compliance retrieval operations into first-class tools.
- [ ] Add tool for `get_review_topic`.
- [ ] Add tool for `search_standard_clauses`.
- [ ] Add tool for `search_internal_evidence`.
- [ ] Add tool for `get_evidence_by_id`.
- [ ] Add bounded ReAct-style evidence gathering with max tool calls.
- [ ] Log every tool call and result.
- [ ] Keep final compliance judgment schema-based, not free-form agent chatter.

### P5: Add Streamable API And Frontend

- [ ] Add a small API endpoint for review runs.
- [ ] Stream progress events: request parsed, topics selected, clauses loaded, evidence retrieved, report rendered.
- [ ] Build a minimal UI showing topics, clause matrix, evidence excerpts, and final report.
- [ ] Add click-through from report evidence ID to evidence excerpt.
- [ ] Add human feedback buttons: accept, reject, needs clarification.

### P6: Improve File Coverage

- [ ] Add `.pptx` parsing.
- [ ] Add legacy `.xls` support.
- [ ] Add legacy `.doc` conversion guidance or converter integration.
- [ ] Add OCR for scanned PDFs.
- [ ] Add skipped-file report with recommended remediation.

### P7: Multi-Agent Extension

- [ ] Split roles into Standard Clause Agent, Internal Evidence Agent, Judgment Agent, Remediation Agent, Report Agent.
- [ ] Share structured evidence packages between agents.
- [ ] Add human review coordinator.
- [ ] Add run-level audit logs.
- [ ] Compare multi-agent output with the current single-graph baseline.

## 5. Acceptance Checklist

### Acceptance 1: Index Build

Command:

```powershell
python scripts\build_compliance_index.py
```

Pass criteria:

- index folder is created
- `chunks.jsonl` exists
- `index_metadata.json` exists
- indexed file count is non-zero
- skipped files are listed with reasons

### Acceptance 2: Clause Extraction

Command:

```powershell
python scripts\extract_standard_clauses.py
```

Pass criteria:

- `data/standard_clauses/clauses.jsonl` exists
- `data/standard_clauses/clauses_review.md` exists
- ISO 13485 key clauses exist:
  - 4.2.4
  - 4.2.5
  - 8.2.4
  - 8.5.2
  - 8.5.3
- ISO 14971 risk management clauses needed by the MVP exist or are explicitly documented as needing manual fix

### Acceptance 3: CAPA Preview

Command:

```powershell
python scripts\preview_compliance_review.py --request "Please review CAPA" --standard-top-k 2 --internal-top-k 3
```

Pass criteria:

- selected topic is CAPA
- structured clauses include ISO 13485 8.5.2 and 8.5.3
- internal evidence includes CAPA-related files
- every retrieved evidence row shows an `evidence_id`

### Acceptance 4: MVP Retrieval Evaluation

Command:

```powershell
python scripts\evaluate_compliance_retrieval.py --internal-top-k 3
```

Pass criteria:

- all 10 MVP topics are evaluated
- internal evidence coverage is 10/10
- clause coverage is at least 9/10 before ISO 14971 cleanup
- after ISO 14971 cleanup, clause coverage should be 10/10 or all missing clauses must have documented reasons

### Acceptance 5: Structured Review Artifacts

Command:

```powershell
python scripts\run_compliance_review.py --request "Please review CAPA" --artifacts-dir runs
```

Pass criteria:

- a new run folder is created
- `evidence_package.json` exists
- `structured_report.json` exists
- `report.md` exists
- cited evidence IDs in `structured_report.json` exist in `evidence_package.json`
- the Markdown report contains a clause matrix

### Acceptance 6: Evidence Guardrail

Command:

```powershell
python -m pytest tests\test_compliance_index.py -q
```

Pass criteria:

- tests pass
- a `符合` assessment without traceable internal evidence is downgraded
- invented evidence IDs are removed
- valid evidence IDs are hydrated from the evidence package

### Acceptance 7: Report Quality Manual Review

Manual check:

- pick one generated report
- open the evidence package
- verify every cited evidence ID points to the right file and excerpt
- verify no conclusion is stronger than the evidence supports
- verify limitations are honest

Pass criteria:

- no unsupported `符合` conclusion
- no invented file names
- no invented page numbers
- no missing evidence IDs for cited internal evidence

### Acceptance 8: Git Hygiene

Command:

```powershell
git status --short
```

Pass criteria:

- source code and documentation changes are visible
- official ISO files are not staged
- internal QMS files are not staged
- generated local indexes are not staged
- reports or run artifacts are only committed if explicitly intended and sanitized

## 6. Suggested Execution Order

Recommended next sequence:

1. Run current tests and retrieval evaluation.
2. Fix ISO 14971 clause extraction until risk management reaches acceptable coverage.
3. Approve the most important clause objects.
4. Add expected internal-file golden cases for the 10 MVP topics.
5. Add report artifact validation.
6. Add Excel export.
7. Add review memory for human corrections.
8. Add streamable API and frontend.
9. Add bounded tool-calling / ReAct evidence gathering.
10. Consider multi-agent orchestration after the single-graph baseline is measurable.

## 7. Definition Of Done For MVP

The MVP is done when:

- the 10 ISO 13485 MVP topics can be reviewed end to end
- each topic has approved clause references
- each report cites traceable internal evidence IDs
- unsupported `符合` conclusions are blocked
- retrieval evaluation is reproducible
- reports are saved as structured JSON and Markdown
- a human reviewer can inspect evidence without reading raw code


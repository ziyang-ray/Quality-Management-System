# Compliance Reviewer Usage

This project currently has three practical ways to use the compliance work.

## 1. Build The Local Evidence Index

Run this first whenever official or internal files change:

```powershell
python scripts\build_compliance_index.py
```

Current expected result is roughly:

```text
Indexed files: 118/148
Chunks: 1177
Skipped files: 30
```

Skipped files are mostly legacy `.doc`, `.xls`, `.pptx`, or PDFs with no extractable text.

## 2. Preview Evidence Before Calling An LLM

Use this to inspect whether each review topic retrieves the right standard clauses and internal QMS files:

```powershell
python scripts\preview_compliance_review.py --request "Please review CAPA, internal audit, and DHR" --standard-top-k 3 --internal-top-k 5
```

Add `--full` to print excerpts:

```powershell
python scripts\preview_compliance_review.py --request "Please review CAPA" --full
```

This is the best first step for debugging retrieval quality. If evidence is wrong here, fix topic queries, preferred terms, chunking, or document loading before testing prompts.

## 3. Evaluate MVP Retrieval Coverage

Use this to check all 10 MVP topics without calling an LLM:

```powershell
python scripts\evaluate_compliance_retrieval.py --internal-top-k 3
```

Optional JSON output:

```powershell
python scripts\evaluate_compliance_retrieval.py --internal-top-k 3 --json-output reports\retrieval_eval.json
```

This reports clause coverage, internal evidence coverage, top evidence IDs, and topics that need attention.

## 4. Extract Candidate Standard Clauses

Use this to turn official standard PDFs into a candidate clause library:

```powershell
python scripts\extract_standard_clauses.py
```

It writes:

```text
data/standard_clauses/clauses.jsonl
data/standard_clauses/clauses_review.md
```

The output is intentionally marked as `candidate`. Review the Markdown file to catch table-of-content rows, annex rows, or clauses that need better summaries/evidence expectations.

## 5. Generate A Compliance Report From CLI

Set your model API key first, for example:

```powershell
$env:OPENAI_API_KEY="..."
```

Then run:

```powershell
python scripts\run_compliance_review.py --request "Please review CAPA, internal audit, and DHR" --output reports\capa_audit.md
```

To save the evidence package, structured JSON report, and rendered Markdown together:

```powershell
python scripts\run_compliance_review.py --request "Please review CAPA" --artifacts-dir runs
```

If the base Anaconda environment fails on `torch` or `transformers`, run the project from a clean `uv` environment instead.

## 6. Use LangGraph Studio

The graph is registered in `langgraph.json` as `Compliance Reviewer`.

Start LangGraph Studio with the project environment:

```powershell
uvx --refresh --from "langgraph-cli[inmem]" --with-editable . --python 3.11 langgraph dev --allow-blocking
```

Then open the Studio URL printed by the command and select `Compliance Reviewer`.

## Recommended Workflow

1. Build the index.
2. Preview evidence for the target topics.
3. Run the retrieval evaluation script for the MVP topics.
4. Tune retrieval if evidence is wrong.
5. Run the CLI or LangGraph Studio to generate the report.
6. Review the report manually before treating any finding as a quality-system conclusion.

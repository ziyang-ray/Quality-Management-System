# Internal Compliance Assistant MVP

This project has been adapted from a general deep research agent into an internal compliance triage assistant for Siemens Healthineers-style use cases.

## What Changed

- External web search is disabled by default.
- The agent has an internal compliance role, risk-oriented output structure, and citation requirements.
- A local internal knowledge base search tool is available through `internal_policy_search`.
- Final reports are expected to include a conclusion, risk level, evidence, next actions, source list, and disclaimer.

## Configure Local Internal Documents

1. Create a folder for approved internal reference documents, for example:

```powershell
mkdir G:\compliance_assistant\internal_kb
```

2. Put approved `.md`, `.txt`, or `.pdf` documents in that folder.

3. Set this in `.env`:

```env
INTERNAL_KNOWLEDGE_BASE_PATH=G:\compliance_assistant\internal_kb
EXTERNAL_SEARCH_ALLOWED=false
SEARCH_API=none
```

## Run Locally

```powershell
cd G:\compliance_assistant\open_deep_research-main
uv sync
uvx --refresh --from "langgraph-cli[inmem]" --with-editable . --python 3.11 langgraph dev --allow-blocking
```

## MVP Behavior

The assistant should:

- Ask clarification questions when region, business context, product scope, document type, or intended audience materially affect the answer.
- Search internal documents first.
- Say "insufficient evidence" when internal sources do not support a conclusion.
- Avoid treating its response as final legal or compliance approval.
- Preserve citations to internal document paths or source identifiers.

## Two Available Graphs

- `Deep Researcher`: general internal compliance Q&A and triage. It uses `internal_policy_search` and, when available, indexed QMS tools.
- `Compliance Reviewer`: focused ISO/QMS pre-audit review. It uses the local compliance index to produce a clause/topic matrix with statuses such as `符合`, `需澄清`, `缺乏证据`, and `未提及`.

Set `COMPLIANCE_INDEX_PATH` to the folder that contains `chunks.jsonl` and `index_metadata.json`.

## Next Hardening Steps

- Replace local file search with Azure AI Search, SharePoint, Confluence, or an authenticated MCP server.
- Replace Supabase authentication with corporate SSO such as Microsoft Entra ID.
- Add audit logging for user, query, sources used, answer, risk level, and escalation recommendation.
- Add regression tests using approved sample policies and expected risk outcomes.

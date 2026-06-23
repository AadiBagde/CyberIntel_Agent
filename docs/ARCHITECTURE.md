# CyberIntel Agent — Architecture

## Design principles

1. **Structured data only** — Pydantic v2 schemas are the contract between API, database, agents, and reports. No unvalidated LLM text crosses service boundaries.
2. **Orchestration ≠ intelligence** — LangGraph owns workflow state and transitions; agents are pluggable nodes registered over time.
3. **Hybrid stack** — FastAPI for HTTP, PostgreSQL for transactional memory, Qdrant for semantic recall (Phase 5+), n8n for scheduling only (Phase 7+).
4. **Async-first I/O** — SQLAlchemy async sessions, async Qdrant client, async agent nodes in later phases.
5. **Deep MVP** — Phase 0 establishes production seams without implementing research, validation, or memory writes.

## Layered architecture

```
┌─────────────────────────────────────────────────────────────┐
│  API (FastAPI) — versioning, middleware, exception mapping   │
├─────────────────────────────────────────────────────────────┤
│  Services — investigation lifecycle, health aggregation      │
├─────────────────────────────────────────────────────────────┤
│  Workflows (LangGraph) — state, registry, graph builder        │
├─────────────────────────────────────────────────────────────┤
│  Agents (Phase 1+) — research, analysis, validation nodes    │
├─────────────────────────────────────────────────────────────┤
│  Persistence — SQLAlchemy ORM + repositories                 │
│  Memory — Qdrant abstraction (Phase 5+)                      │
└─────────────────────────────────────────────────────────────┘
```

## Request lifecycle

1. Client `POST /api/v1/investigate` with `InvestigationRequest`.
2. Middleware assigns `X-Trace-Id` (or accepts client-provided).
3. `InvestigationService` validates the CVE query, persists a row as `queued`, and runs the Phase 2 LangGraph pipeline synchronously.
4. On success, response includes `InvestigationRecord` with `ThreatResearch` and `ThreatAssessment`.
5. Client may re-fetch via `GET /api/v1/investigation/{id}` at any time.

## LangGraph strategy

| Phase | Graph behavior |
|-------|----------------|
| 0 | Bootstrap-only graph; `PIPELINE_NODES` documents future topology |
| 1 | `bootstrap → research → persist` |
| 2 (current) | `bootstrap → research → analyze → persist` |
| 3+ | `deduplicate`, `validate`, `persist_memory`, `generate_report` added per phase |

`InvestigationGraphState` is the single source of truth during workflow execution. Structured outputs are copied into PostgreSQL after validation (Phase 4–5).

## Database model

`investigations` table stores:

- Identity: `id`, `trace_id`, `query`, `query_type`
- Pipeline: `status`
- Artifacts: `research`, `assessment`, `validation` as JSONB
- Memory: `memory_context`, `report_path`

Alembic manages schema evolution; `init_db()` also supports dev bootstrap via metadata create.

## Configuration

`backend.core.config.Settings` (Pydantic Settings) loads `.env` with environment-aware defaults. Secrets are never hardcoded.

## Phase 1 — Intelligence ingestion (implemented)

```
InvestigationService
  → ResearchAgent
  → ThreatIntelProvider[] (NVD required, CISA optional)
  → intelligence_normalizer.merge_provider_results()
  → ThreatResearch
```

See **[PHASE1.md](PHASE1.md)** for API examples and error semantics.

## Phase 2 — Threat analysis (implemented)

```
InvestigationService
  → LangGraph (bootstrap → research → analyze → persist)
  → ResearchAgent → ThreatResearch
  → ThreatAnalysisAgent (Gemini LLM, structured output)
  → ThreatAssessment
  → PostgreSQL JSONB (research + assessment)
```

`ThreatAnalysisAgent` grounds reasoning in the `ThreatResearch` payload. The LLM must return a validated `ThreatAssessment` (severity, confidence 0–100, reasoning, remediation, uncertainty notes). Schema validation failures trigger up to three retries before the workflow fails with a structured error; research artifacts are still persisted on analysis failure.

## Extension points

| Module | Phase | Responsibility |
|--------|-------|----------------|
| `backend/agents/` | 1–4 | `ResearchAgent`, `ThreatAnalysisAgent`, future validation agent |
| `backend/services/llm/` | 2+ | Gemini provider with Pydantic response validation |
| `backend/services/providers/` | 1+ | NVD, CISA KEV, future OTX/MITRE feeds |
| `backend/workflows/registry.py` | 1+ | Node registration |
| `backend/validators/` | 4 | Rule-based + LLM validation |
| `backend/memory/` | 5 | Qdrant upsert/search |
| `backend/reports/` | 6 | Markdown report templates |
| `n8n/` | 7 | Scheduled triggers |

## Why no agents in Phase 0

Implementing stub agents would create technical debt and demo misleading behavior. Phase 0 instead delivers:

- Runnable API and database
- Compilable LangGraph bootstrap
- Enums and schemas aligned with cybersecurity domains
- Vector store interface ready for Phase 5

This matches the project goal: **reliability-aware agent pipelines**, not a chatbot.

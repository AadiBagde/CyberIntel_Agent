# CyberIntel Agent — Phase 0 Architecture

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

## Request lifecycle (Phase 0)

1. Client `POST /api/v1/investigate` with `InvestigationRequest`.
2. Middleware assigns `X-Trace-Id` (or accepts client-provided).
3. `InvestigationService` classifies query type, persists row as `queued`.
4. Response `202 Accepted` with investigation id (no agent execution yet).
5. Client polls `GET /api/v1/investigation/{id}` for status and future artifacts.

## LangGraph strategy

| Phase | Graph behavior |
|-------|----------------|
| 0 | Bootstrap-only graph; `PIPELINE_NODES` documents future topology |
| 1+ | Register `research`, `deduplicate`, … via `NodeRegistry` |
| 2+ | Full linear pipeline with retries/branching added per phase |

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
  → LangGraph (bootstrap → research → persist)
  → ResearchAgent
  → ThreatIntelProvider[] (NVD required, CISA optional)
  → intelligence_normalizer.merge_provider_results()
  → ThreatResearch → PostgreSQL JSONB
```

See **[PHASE1.md](PHASE1.md)** for API examples and error semantics.

## Extension points

| Module | Phase | Responsibility |
|--------|-------|----------------|
| `backend/agents/` | 1–4 | `AgentNode` / `ResearchAgent` implementations |
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

# CyberIntel Agent

Autonomous threat intelligence with multi-agent reasoning, structured outputs, validation guardrails, and persistent memory—not a thin LLM wrapper.

**Current status: Phase 1 complete** (Research Agent + NVD + CISA KEV).

## Architecture

```
User / Scheduler → n8n (Phase 7) → FastAPI → LangGraph
  → Research → Dedup → Analysis → Validation
  → Memory (Postgres + Qdrant) → Report → API
```

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — system design
- **[docs/PHASE1.md](docs/PHASE1.md)** — research agent & providers
- **[docs/IMPLEMENTATION_PHASES.md](docs/IMPLEMENTATION_PHASES.md)** — full roadmap

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

Or local dev:

```bash
pip install -r requirements.txt
docker compose up -d postgres qdrant
alembic upgrade head
uvicorn backend.api.main:app --reload
```

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Quick status |
| GET | `/api/v1/health` | Postgres + Qdrant health |
| POST | `/api/v1/investigate` | Run CVE research pipeline |
| GET | `/api/v1/investigation/{id}` | Fetch investigation |

### Investigate a CVE

```bash
curl -X POST http://localhost:8000/api/v1/investigate \
  -H "Content-Type: application/json" \
  -H "X-Trace-Id: demo-001" \
  -d "{\"query\": \"CVE-2024-3094\"}"
```

Returns `InvestigationResponse` with `ThreatResearch` when successful.

## Phase 1 capabilities

- CVE validation (`CVE-YYYY-NNNN`)
- Async NVD CVE 2.0 API integration (retries, rate-limit handling)
- CISA KEV catalog (cached, degrades gracefully)
- Provider abstraction for future feeds
- LangGraph pipeline: `bootstrap → research → persist_artifact`
- Structured `ThreatResearch` persisted to PostgreSQL

## Tests

```bash
pytest
```

## Next phase

**Phase 2 — Threat Analysis Agent**: LangGraph analysis node, `ThreatAssessment`, reasoning with confidence scores.

Say **"implement Phase 2"** when ready.

## MVP progress

| Component | Status |
|-----------|--------|
| Phase 0 Foundation | Done |
| Research Agent (NVD + CISA KEV) | Done |
| Threat Analysis Agent | Planned |
| Validation Agent | Planned |
| Deduplication Layer | Planned |
| Memory Layer | Planned |
| Report Generator | Planned |
| Basic n8n trigger | Planned |

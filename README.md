# CyberIntel Agent

Autonomous threat intelligence with multi-agent reasoning, structured outputs, validation guardrails, and persistent memory—not a thin LLM wrapper.

**Current status: Phase 2 complete** (Research Agent + Threat Analysis Agent + NVD + CISA KEV).

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
| POST | `/api/v1/investigate` | Run CVE research + analysis pipeline |
| GET | `/api/v1/investigation/{id}` | Fetch investigation |

### Investigate a CVE

```bash
curl -X POST http://localhost:8000/api/v1/investigate \
  -H "Content-Type: application/json" \
  -H "X-Trace-Id: demo-001" \
  -d "{\"query\": \"CVE-2024-3094\"}"
```

Returns `InvestigationResponse` with `ThreatResearch` and `ThreatAssessment` when successful.

## Current capabilities

**Research (Phase 1)**

- CVE validation (`CVE-YYYY-NNNN`)
- Async NVD CVE 2.0 API integration (retries, rate-limit handling)
- CISA KEV catalog (cached, degrades gracefully)
- Provider abstraction for future feeds
- Structured `ThreatResearch` persisted to PostgreSQL

**Analysis (Phase 2)**

- `ThreatAnalysisAgent` reasons over `ThreatResearch` via Gemini LLM
- Structured `ThreatAssessment`: severity, confidence (0–100), reasoning, remediation, uncertainty notes
- LangGraph pipeline: `bootstrap → research → analyze → persist_artifact`
- Analysis failures surface as structured workflow errors; research is still persisted

## Tests

```bash
pytest
```

## Next phase

**Phase 3 — Deduplication Layer**: fingerprint hashing, fuzzy matching, and short-circuit on repeat CVE investigations.

Say **"implement Phase 3"** when ready.

## MVP progress

| Component | Status |
|-----------|--------|
| Phase 0 Foundation | Done |
| Research Agent (NVD + CISA KEV) | Done |
| Threat Analysis Agent | Done |
| Validation Agent | Planned |
| Deduplication Layer | Planned |
| Memory Layer | Planned |
| Report Generator | Planned |
| Basic n8n trigger | Planned |

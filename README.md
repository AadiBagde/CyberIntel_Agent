# CyberIntel Agent

Autonomous threat intelligence with multi-agent reasoning, structured outputs, validation guardrails, and persistent memory—not a thin LLM wrapper.

**Current status: Phase 3 complete** (Research + Deduplication + Threat Analysis + NVD + CISA KEV).

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
| POST | `/api/v1/investigate` | Run CVE research + dedup + analysis pipeline |
| GET | `/api/v1/investigation/{id}` | Fetch investigation |

### Investigate a CVE

```bash
curl -X POST http://localhost:8000/api/v1/investigate \
  -H "Content-Type: application/json" \
  -H "X-Trace-Id: demo-001" \
  -d "{\"query\": \"CVE-2024-3094\"}"
```

Returns `InvestigationResponse` with `research`, `assessment`, and `deduplication` when successful.

### Fetch an investigation

```bash
curl http://localhost:8000/api/v1/investigation/{id}
```

Response includes first-class artifacts:

```json
{
  "investigation": {
    "id": "...",
    "status": "completed",
    "research": { },
    "assessment": { },
    "deduplication": {
      "is_duplicate": true,
      "similarity_score": 1.0,
      "method": "exact_match"
    }
  }
}
```

## Current capabilities

**Research (Phase 1)**

- CVE validation (`CVE-YYYY-NNNN`, case/space tolerant)
- Async NVD CVE 2.0 API integration (retries, rate-limit handling)
- CISA KEV catalog (cached, degrades gracefully)
- Provider abstraction for future feeds
- Structured `ThreatResearch` persisted to PostgreSQL

**Analysis (Phase 2)**

- `ThreatAnalysisAgent` reasons over `ThreatResearch` via Gemini LLM
- Structured `ThreatAssessment`: severity, confidence (0–100), reasoning, remediation, uncertainty notes
- Analysis failures surface as structured workflow errors; research is still persisted

**Deduplication (Phase 3)**

- SHA-256 fingerprinting on normalized CVE queries
- PostgreSQL lookup before analysis; skips LLM on exact duplicate
- Reuses prior `ThreatResearch` + `ThreatAssessment` from matched investigation
- LangGraph pipeline: `bootstrap → research → deduplicate → analyze → persist_artifact`
- Safe DB-failure fallback; structured `deduplication` metadata on every investigation

## Tests

```bash
pytest
```

## Next phase

**Phase 4 — Validation Agent**: guardrails for hallucinated CVEs, unsupported exploit claims, and CVSS mismatches.

Say **"implement Phase 4"** when ready.

## MVP progress

| Component | Status |
|-----------|--------|
| Phase 0 Foundation | Done |
| Research Agent (NVD + CISA KEV) | Done |
| Threat Analysis Agent | Done |
| Deduplication Layer | Done |
| Validation Agent | Planned |
| Memory Layer | Planned |
| Report Generator | Planned |
| Basic n8n trigger | Planned |

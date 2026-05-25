# Phase 1 — Research Agent

## Overview

Phase 1 delivers autonomous **CVE intelligence retrieval** via a provider-based architecture. Outputs are strictly normalized into `ThreatResearch` — never raw NVD/KEV JSON.

## Flow

```
POST /api/v1/investigate
  → InvestigationService.run_investigation()
  → LangGraph: bootstrap → research → persist_artifact
  → ResearchAgent
  → NvdProvider + CisaKevProvider (parallel)
  → merge_provider_results()
  → PostgreSQL JSONB (research column)
  → InvestigationResponse
```

## Providers

| Provider | Source | Required |
|----------|--------|----------|
| `NvdProvider` | NVD CVE 2.0 API | Yes |
| `CisaKevProvider` | CISA KEV JSON feed | No (degraded OK) |

Add future providers under `backend/services/providers/` implementing `ThreatIntelProvider`.

## Environment

```env
NVD_API_KEY=optional_but_recommended
NVD_API_BASE_URL=https://services.nvd.nist.gov/rest/json/cves/2.0
CISA_KEV_URL=https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
HTTP_TIMEOUT_SECONDS=30
HTTP_MAX_RETRIES=3
```

## Example request

```bash
curl -X POST http://localhost:8000/api/v1/investigate \
  -H "Content-Type: application/json" \
  -H "X-Trace-Id: demo-trace-001" \
  -d '{"query": "CVE-2024-3094"}'
```

## Example response (shape)

```json
{
  "investigation": {
    "id": "uuid",
    "trace_id": "demo-trace-001",
    "query": "CVE-2024-3094",
    "query_type": "cve",
    "status": "completed",
    "research": {
      "cve_id": "CVE-2024-3094",
      "query": "CVE-2024-3094",
      "summary": "...",
      "cvss_score": 10.0,
      "severity": "CRITICAL",
      "exploit_available": true,
      "known_exploited": true,
      "affected_products": ["cpe:..."],
      "references": ["https://..."],
      "cwe": ["CWE-506"],
      "published_date": "2024-03-29T10:15:18.133000",
      "last_modified_date": "...",
      "data_sources": ["nvd", "cisa_kev"]
    }
  }
}
```

## Error behavior

| Condition | HTTP | Investigation row |
|-----------|------|-------------------|
| Invalid CVE | 422 | Not created |
| NVD failure | 503 | `failed` + error_message |
| CISA failure | — | Completes with NVD only |
| Missing research at persist | — | `failed` |

## Tests

```bash
pytest tests/test_cve.py tests/test_nvd_parser.py tests/test_cisa_parser.py
pytest tests/test_normalizer.py tests/test_research_agent.py
```

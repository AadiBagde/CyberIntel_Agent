# Signature Demo Script

Run this after **Phase 5 (Memory)** is complete. Optional: Phase 6 for markdown report output.

## Scenario: Agentic second investigation

### Investigation 1 — Initial CVE

```bash
curl -X POST http://localhost:8000/investigate \
  -H "Content-Type: application/json" \
  -d '{"query": "CVE-2024-3094"}'
```

**Expected:**

- Structured `ThreatResearch` from NVD + KEV
- `ThreatAssessment` with severity and confidence
- `ValidationResult` with `valid: true` (or documented issues)
- Record stored in Postgres; embedding in Qdrant
- Investigation id in response

Save `investigation_id_1` from response.

### Investigation 2 — Related query (same entity family)

```bash
curl -X POST http://localhost:8000/investigate \
  -H "Content-Type: application/json" \
  -d '{"query": "xz backdoor CVE-2024-3094"}'
```

**Expected (agentic behaviors):**

- Memory recall references Investigation 1
- Severity not incorrectly downgraded vs prior finding
- Dedup skips redundant NVD fetches where fingerprint matches
- Report or API payload includes **historical context** section
- Validation still runs (no bypass because of cache)

### What to show interviewers

1. Langfuse trace: research → dedup → analysis → validation → memory write
2. Validation catching an unsupported exploit claim (inject test in dev)
3. Side-by-side API responses: first vs second investigation showing memory fields
4. Generated `investigation_report.md` with prior context (Phase 6+)

## Failure modes to rehearse

| Symptom | Likely cause |
|---------|----------------|
| Second run ignores memory | Phase 5 retrieval not wired in graph |
| Duplicate NVD calls | Phase 3 dedup not in graph path |
| Exploit claim not caught | Phase 4 rules incomplete |
| Raw LLM text in API | Schema bypass—fix before demo |

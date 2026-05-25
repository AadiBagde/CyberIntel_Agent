# n8n workflows (Phase 7+)

n8n is used **only** for scheduling, triggers, and notifications—not for agent reasoning.

Planned flows:

- Cron → fetch new CVEs → `POST /api/v1/investigate`
- On completion → webhook / email stub
- Failure → log + alert

Export workflow JSON files here when Phase 7 begins.

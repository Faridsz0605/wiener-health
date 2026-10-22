# wiener TODO

## Reminders

- [ ] **Define SLAs** — trigger: once the wiener data extraction process (Open Wearables ingestion) is automated and running end to end. Candidate SLAs: data freshness (event → gold latency), ingestion completeness, pipeline success rate, FastAPI read API availability/latency.
- [ ] **FastAPI** — deferred. Build only when a real consumer exists (dashboard, LLM tool over pgvector).
- [ ] **Databricks PAT rotation** — every 90 days; update SSM SecureString.
- [ ] **Verify before build** — Databricks Free Edition file-arrival triggers on UC Volumes (fallback: scheduled job); Google Health API OAuth scope class + refresh-token expiry under Testing publishing status.

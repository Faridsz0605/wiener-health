# wiener

Personal health data lakehouse: extracts wearable data from external systems and refines it through medallion layers for personal analysis.

## Language

**Data Source**:
An external system the pipeline extracts from. Open Wearables is the first.
_Avoid_: Source API, upstream, provider

**Open Wearables**:
The self-hosted health platform that aggregates Provider data into one schema; the first Data Source and the transactional store of record for raw health data.
_Avoid_: OW API, wearables API

**Provider**:
A wearable vendor or health platform that Open Wearables connects to (e.g. Google Health, Garmin, Oura).
_Avoid_: Source, Data Source, vendor

**Subject**:
The person whose health data is collected.
_Avoid_: User, patient, account

**Raw Archive**:
The immutable, Subject-owned copy of every extraction exactly as received from a Data Source; the source of truth the lakehouse can be rebuilt from.
_Avoid_: Landing zone, raw bucket, dump

**Extraction**:
One run of pulling data from a Data Source into the Raw Archive (the wiener data extraction process).
_Avoid_: Ingestion run, sync, fetch

**Extraction Window**:
The rolling time range an Extraction re-pulls so late-arriving data is caught.
_Avoid_: Watermark, lookback, delta

**Health Summary**:
A templated text description of one Subject's day or night, derived from gold data, used for retrieval by the agent.
_Avoid_: Report, digest, document

**Analysis Store**:
The Postgres database holding gold-layer data and embeddings for ad hoc analysis.
_Avoid_: Serving DB, final Postgres, warehouse

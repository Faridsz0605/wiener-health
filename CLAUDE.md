# Project Description

Data engineering focused project implementing automated adata extraction for a final medallion architecture and data lakehousing using databricks and AWS hosting.

# Texh-stack

- Backend: Python [FastAPI, Polars, pyspark]
- DB: PostgreSQL [docker, pgvector] 
- contenarization: Docker.
- Cloud AWS
- Diagramming: Mermaid/excalidraw
- Shell: bash [ripgrep(rg)]

# conventions

- `wiener` is project branding for docs and process names (e.g. "wiener data extraction process"). Not used in code identifiers or catalog/schema names.
- snake_case naming.
- polars for extraction/landing and single-node utilities. spark (pyspark) for all distributed processing inside the medallion layers.
- uv packagemanager.

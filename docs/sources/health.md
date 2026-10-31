# Fuente Health (ex Wiener Health)

## Origen

Wiener Health nacio como una app para atletas: registrar alimentacion, entrenamiento e indicadores de salud es tedioso y rompe la constancia. La idea era resolverlo con una llamada o un mensaje de texto. El proyecto se fusiono en Wiener-Data ([ADR 0003](../adr/0003-fusion-wiener-data.md)).

## Estado actual

Implementado como lakehouse de salud de un solo sujeto ([catalogo](../catalog/health-metrics.md)):

- **M1 Extraccion** (desplegado): Terraform base (S3, EC2, SSM), Open Wearables con `google_health`, extraccion al Raw Archive.
- **M2 Lakehouse** (desplegado): Lambda S3 -> Volume, pipeline Lakeflow bronze/silver/gold, trigger por llegada de archivos.
- **M3 Analysis Store**: recarga de Gold, Health Summaries, embeddings (codigo en `extraction/load_gold.py`).
- **M4 Agente**: servidor MCP con `search_health_summaries` y `query_analysis_store` (`agent/mcp_server.py`).
- **M5 CI**: GitHub Actions; `terraform apply` automatizado pendiente.

## Vision que sigue vigente (fases siguientes)

- Registro de alimentacion por lenguaje natural con RAG sobre una base nutricional, para no digitar comidas.
- Sugerencias proactivas de alimentos segun requerimientos y preferencias.
- Llamada/entrevista programada por el agente (el usuario elige horario).
- Dashboard de progreso estilo MyFitnessPal.
- Integridad de la data alimenticia como prioridad, con validez y rigurosidad cientifica.

## Cambios respecto al plan original

- El homelab k3s quedo descartado: AWS (box EC2, S3, Lambda) + Databricks Free Edition ([ADR 0001](../adr/0001-aws-hosts-services-databricks-free-edition-hosts-lakehouse.md)).
- Postgres + pgvector se mantiene, como Analysis Store en el box.

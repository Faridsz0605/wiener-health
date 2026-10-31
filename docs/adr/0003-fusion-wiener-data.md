# 0003 - Fusion en Wiener-Data

Estado: aceptado

## Contexto

En el repo convivian dos lineas:

- **Wiener Health**: vision original (nutricion, agente con RAG, homelab k3s) que ya evoluciono a un lakehouse de salud desplegado: Fitbit via Google Health -> Open Wearables en EC2 -> S3 Raw Archive -> Lambda -> Volume -> pipeline Lakeflow -> Analysis Store (Postgres + pgvector) -> agente MCP ([0001](0001-aws-hosts-services-databricks-free-edition-hosts-lakehouse.md), [0002](0002-event-driven-micro-batch-lambda-only-on-s3-events.md)). M1 y M2 desplegados.
- **Lakehouse personal**: diseno para Gmail + Google Photos con cliente local y computo efimero en Databricks Free, retencion cero ([0000](0000-supuestos-falsados.md)).

Ambas extraen y modelan datos personales sobre Databricks Free Edition.

## Decision

- Un solo proyecto: **Wiener-Data**, centrado en extraccion de datos personales e ingenieria de datos, tiers gratis, fase de aprendizaje, portfolio con camino a catalogo de servicios.
- Health sigue como esta: **fuente desplegada** (wearables) + **app** (agente MCP sobre el Analysis Store). No se reescribe.
- Gmail y Photos se agregan como servicios nuevos con su propio patron ([0008](0008-fuentes-google-efimeras.md)). Primer hito nuevo: Gmail end to end.
- El homelab k3s del README original queda descartado; ya lo reemplazo [0001](0001-aws-hosts-services-databricks-free-edition-hosts-lakehouse.md).
- El nombre del repo en GitHub no cambia en esta fase (accion manual del propietario).

## Consecuencias

- README reescrito; diagramas k3s eliminados. Contenido operativo del lakehouse de salud (runbook, operaciones, privacidad) se conserva.
- Dos patrones conviven: persistente de un solo sujeto (health) y efimero (fuentes Google). Ver [retencion](../retention.md).

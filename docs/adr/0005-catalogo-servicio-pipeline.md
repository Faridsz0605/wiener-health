# 0005 - Catalogo: servicio = pipeline

Estado: aceptado

## Contexto

El proyecto busca ser portfolio y, a futuro, un catalogo de servicios que resuelva problemas de otras personas. Hace falta una unidad clara de "servicio".

## Decision

Una entrada del catalogo = **un pipeline fuente -> Gold -> entrega**, documentado con una ficha en `docs/catalog/` segun [la plantilla](../catalog/_template.md): problema que resuelve, fuente, patron de ingesta, grano Silver, tablas Gold, metricas, entrega, estado y `REVIEW` abiertos.

## Consecuencias

- Cada nuevo servicio empieza por su ficha.
- Las apps (agente MCP, dashboards) no son servicios: consumen Gold de uno o varios.

# 0004 - Monorepo por capas

Estado: aceptado

## Contexto

Varias fuentes (Health, Gmail, Photos) comparten etapas: extraccion, medallion en Databricks, entrega de Gold y apps. El repo ya tiene carpetas por capa para health.

## Decision

Se reutilizan las capas existentes y se agregan solo las que faltan. Dentro de cada capa, un modulo por fuente.

| Capa | Carpeta | Contenido |
|---|---|---|
| Extraccion | `extraction/` | Open Wearables (box), Gmail (cliente local) |
| Medallion | `lakehouse/` | Bundle Databricks: pipeline Lakeflow de health, export de Gold, job efimero de Gmail |
| Entrega | `serving/` (nueva) | Export de Gold a destinos del usuario |
| Apps | `agent/` | Servidor MCP sobre el Analysis Store |
| Nucleo cliente | `core/` (nueva) | Config, secretos en keyring, estado SQLite, `run_id` |
| Infra | `infra/`, `lambda_src/`, `box/`, `scripts/` | Terraform, Lambda, box EC2, despliegue |
| Experimentos | `spikes/` (nueva) | Scripts desechables numerados |
| Tests | `tests/`, `tests/fixtures/` | Solo datos sinteticos |

## Consecuencias

- Agregar una fuente = un modulo por capa + ficha de catalogo.
- Las dependencias del cliente local van en el grupo `client` de `uv`, para no inflar el box (`uv sync --no-dev`).

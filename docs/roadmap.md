# Roadmap

Estados: `desplegado` / `codigo en main` / `hecho` / `en PR` / `pendiente de ejecucion` (codigo listo, falta credencial) / `pendiente`.

## Health (lakehouse de un solo sujeto, ya en `main`)

| Hito | Contenido | Estado |
|---|---|---|
| M1 Extraccion | Terraform base (S3, EC2, SSM), Open Wearables con `google_health`, extraccion al Raw Archive | desplegado |
| M2 Lakehouse | Lambda S3 -> Volume, pipeline Lakeflow, trigger por llegada de archivos | desplegado |
| M3 Analysis Store | Recarga de Gold, Health Summaries, embeddings | codigo en main (despliegue `REVIEW`) |
| M4 Agente | MCP con `search_health_summaries` y `query_analysis_store` | codigo en main (despliegue `REVIEW`) |
| M5 CI | GitHub Actions (checks + `databricks bundle deploy`); `terraform apply` automatizado | CI en main; `terraform apply` pendiente |

## F0 - Planning de la fusion

Salida: README EN/ES, ADRs 0003-0008, catalogo, modelo, retencion, diagramas, scaffold del cliente.

| Item | Estado |
|---|---|
| Workflow del repo (CONTRIBUTING, PR template, `.gitignore`, proteccion de `main`) | en PR |
| Fusion Wiener-Data: docs, ADRs, catalogo | en PR |
| Diagramas SVG | en PR |
| Scaffold del cliente local (`core/`, estado SQLite, keyring, linter, CI) | en PR |

## F1 - Spikes de plataforma (1-7)

Salida: cada spike con resultado en `docs/spikes.md`; decisiones confirmadas o plan B activado.

| # | Spike | Si falla | Estado |
|---|---|---|---|
| 1 | Subir JSON a Volume desde local (SDK/Files API) | Bronze por otro camino | pendiente de ejecucion (ver [spikes](spikes.md)) |
| 2 | Leer Gold desde local via SQL warehouse a Parquet | Pull por Files API (ya usado por health) | pendiente de ejecucion (ver [spikes](spikes.md)) |
| 3 | `run-now` por Jobs API con PAT | Disparo manual en MVP | pendiente de ejecucion (ver [spikes](spikes.md)) |
| 4 | Job con scratch por `run_id` + cleanup; listar y afirmar vacio | Revisar modelo de retencion | pendiente de ejecucion (ver [spikes](spikes.md)) |
| 5 | Inspeccionar `_delta_log` de tabla temporal | Justifica borrar path entero | pendiente de ejecucion (ver [spikes](spikes.md)) |
| 6 | Excepcion con valor reconocible; buscar fuga en logs/output | Reforzar sanitizacion | pendiente de ejecucion (ver [spikes](spikes.md)) |
| 7 | `display()` en run; confirmar persistencia en historial | Linter en CI | pendiente de ejecucion (ver [spikes](spikes.md)) |

Spike 1 esta parcialmente validado por M2 (la Lambda sube a un Volume) y el pull de Parquet por Files API por M3; los spikes confirman el camino desde el cliente local.

## F2 - Gmail end to end

Salida: un comando del cliente sube el lote, ejecuta el job, descarga Gold a Parquet/DuckDB y verifica cero objetos remotos.

| Item | Estado |
|---|---|
| Ingesta Gmail (OAuth BYO, `historyId`, resync 404, dump local) | en PR (probado con mocks) |
| Pipeline Bronze -> Silver -> Gold | pendiente |
| Orquestador CLI + export | pendiente |
| Spike 8: sync inicial, cambio de label, borrado, re-sync, forzar 404 | pendiente de ejecucion (ver [spikes](spikes.md)) |
| Spike 10: Silver con 5 correos patologicos | pendiente |
| Spike 13: token OAuth a 8 dias | pendiente de ejecucion (ver [spikes](spikes.md)) |
| Spike 14: keyring en SO objetivo | parcial: WSL sin backend (ver [spikes](spikes.md)) |

## F3 - Photos

Salida: inventario desde Takeout con diff entre dos snapshots. Spikes 9 (match sidecar), 11 (diff alta + baja), 12 (estado C con duplicado).

## F4 - Health: nutricion

Salida: fuente de datos nutricionales (`REVIEW`) modelada en Gold junto a los wearables.

## F5 - Apps

Salida: agente de salud (M4) con registro de comidas por lenguaje natural; dashboards.

## F6 - Multiusuario / broker / SaaS

Fuera de dev. BYO-cloud, BYO OAuth client, revision legal y de privacidad (`REVIEW`) antes de abrir a otros usuarios.

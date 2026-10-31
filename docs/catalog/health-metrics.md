# Metricas de salud

| Campo | Valor |
|---|---|
| Problema que resuelve | Vista 360 de la salud: actividad, ritmo cardiaco, sueno y entrenamientos en un solo modelo, consultable por un agente |
| Fuente | Fitbit via Google Health API, normalizado por Open Wearables (EC2) |
| Patron de ingesta | Micro-batch por eventos: timer de extraccion cada 6h (ventana movil de 3 dias) -> S3 Raw Archive -> Lambda -> Volume `landing` -> file arrival -> Lakeflow `Trigger.AvailableNow` |
| Grano Silver | Muestra de serie temporal, sueno, entrenamiento; dedup por clave natural (gana la extraccion mas reciente) |
| Tablas Gold | `daily_health_summary`, `sleep_nightly`, `workout_summary`, `trend_baselines` |
| Metricas | Totales/promedios diarios, sueno por noche, entrenamientos, lineas base 7d/30d y desviacion % |
| Entrega | Parquet en Volume `gold_export` -> loader en el box -> Analysis Store (Postgres + pgvector) + Health Summaries embebidos (Bedrock Titan v2) -> agente MCP |
| Estado | M1 y M2 desplegados; M3-M5 con codigo en `main` |

Patron persistente de un solo sujeto: ver [ADR 0001](../adr/0001-aws-hosts-services-databricks-free-edition-hosts-lakehouse.md) y [ADR 0002](../adr/0002-event-driven-micro-batch-lambda-only-on-s3-events.md).

## REVIEW abiertos

- Estado real de despliegue de M3 (Analysis Store), M4 (agente) y M5 (`terraform apply` automatizado).
- Fuente de datos nutricionales con validez cientifica (fase siguiente).

Ver [fuente health](../sources/health.md).

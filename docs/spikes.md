# Spikes

Cada spike falsa una decision. Scripts en `spikes/`, solo datos sinteticos (marcador `wd-canary-<run_id>`). Todos limpian `scratch/<run_id>/` en `finally`.

## Como ejecutar

Requisitos: el workspace Databricks Free Edition del proyecto (el mismo de health), el Volume `scratch` (lo crea el bundle: `./scripts/deploy_bundle.sh`), un PAT y (spike 2) el HTTP path del SQL warehouse.

```sh
uv sync --group client --group spikes
export DATABRICKS_HOST=https://<workspace>.cloud.databricks.com
export SCRATCH_VOLUME=/Volumes/workspace/wiener/scratch           # default
export DATABRICKS_WAREHOUSE_HTTP_PATH=/sql/1.0/warehouses/<id>   # solo spike 2
uv run python spikes/00_store_token.py                           # PAT al keyring del SO
uv run python spikes/01_volume_upload.py                         # ... hasta 07
```

Cada script imprime `spike NN: PASS|FAIL - detalle`. Copiar el resultado a la tabla.

## Resultados

| # | Spike | Script | Estado | Resultado |
|---|---|---|---|---|
| 1 | Subir JSON a Volume (Files API) y leerlo | `01_volume_upload.py` | pendiente de ejecucion | M2 ya sube a un Volume desde la Lambda (REST `fs/files`); falta desde el cliente local |
| 2 | Leer resultado del SQL warehouse a Parquet local | `02_sql_pull.py` | pendiente de ejecucion | - |
| 3 | `run-now` de job serverless con PAT | `03_run_now.py` | pendiente de ejecucion | - |
| 4 | Job escribe Delta en scratch, borra en `finally`; cero objetos | `04_scratch_cleanup.py` | pendiente de ejecucion | - |
| 5 | Stats de contenido en `_delta_log` | `05_delta_log_stats.py` | pendiente de ejecucion | - |
| 6 | Fuga de valores en excepciones (error / trace del run) | `06_exception_leak.py` | pendiente de ejecucion | - |
| 7 | Persistencia de `print()`/`show()` en logs del run | `07_display_persistence.py` | pendiente de ejecucion | - |
| 8 | Gmail: sync inicial, cambio de label, borrado, re-sync, forzar 404 | `08_gmail_sync.py` | pendiente de ejecucion (logica cubierta con mocks en `tests/test_gmail_ingest.py`) | - |
| 13 | Token OAuth a 8 dias (app en "Testing") | `08_gmail_sync.py` repetido al dia 8 | pendiente de ejecucion | - |
| 14 | Keyring en SO objetivo | (observado al preparar spikes) | parcial | WSL/Linux sin escritorio: `keyring.errors.NoKeyringError` (sin backend). Windows/macOS: `REVIEW`. Plan B: fallback cifrado local o ejecutar el cliente en el SO host |

Bloqueo actual de 1-7: sin credenciales de Databricks en el entorno de desarrollo del cliente (sin `DATABRICKS_HOST` ni PAT en el keyring).

## Gmail (spikes 8 y 13)

1. Google Cloud Console, cuenta de prueba (nunca la personal): habilitar Gmail API en un proyecto, pantalla de consentimiento en modo "Testing" con el propio usuario como tester, crear OAuth client tipo "Desktop" y descargar `client_secret.json` fuera del repo. Puede ser el mismo proyecto de Google Health, con un client distinto.
2. `uv run python spikes/08_gmail_sync.py ~/client_secret.json` -> modo `full`.
3. En Gmail: cambiar un label, borrar un correo, recibir uno nuevo. Ejecutar de nuevo -> modo `incremental` con registros `history` y `message`.
4. `uv run python spikes/08_gmail_sync.py --expire` -> modo `full` (404 por `historyId` viejo).
5. Spike 13: repetir el paso 3 al dia 8 sin reautorizar. Si falla, el refresh token caduca en "Testing".

Los dumps quedan en `~/.wiener-data/bronze/gmail/` (fuera del repo). El script solo imprime conteos.

## Notas de diseno

- `core/jobs.run_script` sube `job.py` al scratch, crea un job serverless (`environment client 2`, igual que el job `wiener_lakehouse` del bundle), ejecuta `run-now`, lee salida/estado y borra el job. Si borrar el job purga el historial de runs: `REVIEW`.
- Spike 4 usa `shutil.rmtree` sobre la ruta `/Volumes/...` dentro del job (acceso FUSE: `REVIEW`).
- Spikes 5-7 responden una pregunta; `PASS` = respuesta obtenida, el detalle dice si hubo fuga.

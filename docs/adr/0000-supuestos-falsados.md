# 0000 - Supuestos falsados (registro historico)

Registro de supuestos del diseno original del Lakehouse personal (Gmail + Google Photos) refutados antes de la fusion, y la decision tomada. Cada cambio de decision nuevo agrega una fila y, si aplica, un ADR propio. `REVIEW` = no verificado en docs oficiales.

| # | Supuesto original | Refutacion | Decision |
|---|---|---|---|
| 1 | "Databricks Community" + S3 propio + JDBC a RDS | Free Edition: solo serverless, salida a internet restringida a dominios de confianza, sin storage custom de workspace. Verificacion LinkedIn desbloquea salida | Inversion a pull/push desde cliente local. JDBC saliente descartado |
| 2 | Postgres serving obligatorio | Power BI/cliente leen SQL warehouse directo. Reverse ETL = copia extra | Serving = capa de export (Parquet/CSV/DuckDB/SQLite/Postgres opcional) |
| 3 | Watermark `updatedMin`/`pageToken` | `pageToken` es paginacion. Calendar usa `syncToken` (excluyente con `updatedMin`, 410 = resync). Gmail usa `historyId` (404 = resync). `REVIEW` vs docs | Camino de full resync obligatorio en diseno |
| 4 | Refresh token eterno | App OAuth en "Testing": token caduca a 7 dias. `REVIEW` | Spike a 8 dias. BYO OAuth client por usuario |
| 5 | Bronze "strict typing", dedup ciego en Silver | Bronze es crudo. Dedup sin orden es no determinista: eventos/mensajes mutan | Tipado en Silver. MERGE ordenado por version/updated. Borrados = flag |
| 6 | Photos por API incremental | Desde 2025-03-31 la Library API solo ve contenido creado por la app. Picker API es seleccion manual | Photos solo via Google Takeout (snapshot batch) |
| 7 | App solicita Takeout sola | No hay API publica de Takeout (`REVIEW`). Data Portability API: sin scope de Photos en el listado recuperado (parcial), requiere verificacion de app, billing, region, 18+ | Takeout guiado: app abre Takeout preconfigurado, usuario lo programa, app vigila carpeta local |
| 8 | Calendar/Gmail en MVP | Ambiguo y Calendar fuera de scope ahora | Fuentes: Gmail + Photos |
| 9 | Spark necesario por volumen | Metadatos caben en pandas/DuckDB | Spark = objetivo de aprendizaje. Declarado |
| 10 | Tokens en RDS del dev | Contradice "no guardo nada" | Keyring local del usuario. Ingesta corre en cliente |
| 11 | "Nada se almacena" | Delta, `_delta_log` (stats min/max = metadata de contenido), historial de runs, logs, backups persisten | Ver [retencion](../retention.md) |

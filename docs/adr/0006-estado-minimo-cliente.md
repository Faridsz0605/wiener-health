# 0006 - Estado minimo en el cliente (opcion C)

Estado: aceptado (dev). Aplica a fuentes efimeras ([0008](0008-fuentes-google-efimeras.md)).

## Contexto

El MERGE de Silver necesita historial, pero el contrato de retencion cero impide guardar tablas en la nube entre runs. Opciones:

- A. El cliente guarda Silver/Gold y lo reenvia en cada run (crece mal).
- B. Reproceso completo en cada run (simple, caro).
- C. El cliente conserva solo estado minimo (`historyId`, hashes vistos), el job procesa solo el lote nuevo y el merge ocurre en el destino del usuario.

## Decision

Opcion **C** para dev. SQLite local guarda watermarks, `historyId`, hashes vistos y lotes/snapshots procesados.

## Consecuencias

- Separa estado (usuario) de computo (plataforma).
- El destino debe soportar upsert (DuckDB/SQLite) o el usuario acepta archivos por lote (Parquet/CSV).
- Spike 12 (lote 2 con foto duplicada) valida la opcion; si falla, cambiar a B.

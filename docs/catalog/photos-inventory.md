# Inventario de fotos

| Campo | Valor |
|---|---|
| Problema que resuelve | Inventario de la biblioteca: fotos por mes/camara, duplicados entre albumes, altas y bajas entre exportaciones |
| Fuente | Google Takeout (guiado: la app abre Takeout preconfigurado, el usuario lo programa, la app vigila la carpeta local) |
| Patron de ingesta | Snapshot batch: sidecar JSON + EXIF + hash de contenido (calculado en local) |
| Grano Silver | Una fila por `content_hash`; diff entre snapshots |
| Tablas Gold | `dim_date`, `fact_photo` |
| Metricas | Fotos por mes, por camara, duplicados |
| Export | Parquet / CSV / DuckDB / SQLite |
| Estado | Planificado (F3) |

## REVIEW abiertos

- No hay API publica de Takeout; Data Portability API sin scope de Photos en el listado recuperado.
- % de match sidecar-media (nombres truncados, `(1)`, `-edited`); spike 9.
- Binarios nunca suben: solo metadatos y hashes.

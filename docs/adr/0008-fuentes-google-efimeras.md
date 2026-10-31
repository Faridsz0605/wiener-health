# 0008 - Fuentes Google personales: cliente local + computo efimero

Estado: aceptado (dev)

## Contexto

Health usa un patron persistente en la cuenta AWS propia: Raw Archive en S3 para siempre, lakehouse en Databricks, Analysis Store ([0001](0001-aws-hosts-services-databricks-free-edition-hosts-lakehouse.md), [0002](0002-event-driven-micro-batch-lambda-only-on-s3-events.md)). Es aceptable para un solo sujeto (el dev).

Gmail y Photos tienen otro perfil: mas sensibles, pensados para ser un servicio para otras personas, y Gmail es scope restringido. Guardar copias en infraestructura del dev no escala ni en confianza ni en cumplimiento.

## Decision

- Extraccion en el **cliente local** del usuario (tokens en keyring, estado en SQLite, dump crudo local = Bronze del usuario).
- Computo en Databricks Free con **scratch por `run_id`**: upload del lote -> `run-now` de un job efimero -> pull de Gold -> borrado y verificacion de cero objetos ([0006](0006-estado-minimo-cliente.md), [0007](0007-entrega-salida.md)).
- Sin S3 propio ni Raw Archive para estas fuentes. Binarios (fotos, adjuntos) nunca suben; solo metadatos y hashes.
- Spark se usa como objetivo de aprendizaje: el volumen de metadatos cabe en DuckDB.

## Consecuencias

- Mismo workspace Free Edition que health: sin aislamiento de tenants; un bug de path mezcla datos. `run_id` validado antes de construir rutas.
- Dependencia de los spikes de plataforma 1-7 ([roadmap](../roadmap.md)).

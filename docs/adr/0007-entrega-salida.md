# 0007 - Entrega de salida

Estado: aceptado (dev). Aplica a fuentes efimeras ([0008](0008-fuentes-google-efimeras.md)).

## Contexto

Gold queda en la nube al terminar el job. Hay que entregarlo al usuario sin dejar copia.

## Decision

- **Pull inmediato** desde el cliente (Files API) seguido de **borrado confirmado** del path `scratch/<run_id>/` y verificacion de cero objetos.
- **TTL de 24h** como red de seguridad para runs abortados (`REVIEW`: mecanismo concreto en Free Edition).
- Alternativa descartada en dev: staging con URL firmada (requiere broker).

## Consecuencias

- El cliente debe estar en linea durante el run.
- Invariante de test: tras cada run, listar Volume por `run_id` -> cero objetos. Ver [retencion](../retention.md).

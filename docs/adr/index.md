---
title: Índice de decisiones de arquitectura (HIST)
owner: Federico Degiovanni
status: vigente
last_reviewed: 2026-10-29
---

# Decisiones de arquitectura — `proyecto-embolsadora`

Un archivo por decisión, formato MADR, inmutable: una decisión no se edita, se crea otra que la reemplaza y la anterior queda con `superseded_by`. Prefijo `HIST-`; las decisiones de sistema (`SYS-`) viven en el hub.

Merece ADR una decisión difícil de revertir que afecte contratos, persistencia, seguridad o despliegue. La **constitution** (`.specify/memory/constitution.md`) sigue siendo la autoridad sobre el stack; estas ADR registran decisiones puntuales.

## Decisiones

| ID | Título | Estado | Fecha |
|---|---|---|---|
| [HIST-ADR-001](./HIST-ADR-001-semantica-aas-en-tags-de-influxdb.md) | La semántica AAS viaja en los tags de InfluxDB, definida por `aas_mapping.yaml` | accepted | 2026-04-07 |
| [HIST-ADR-002](./HIST-ADR-002-xml-aas-runtime-reescrito-por-ciclo.md) | El XML AAS runtime se reescribe completo en cada ciclo y lo sirve FA³ST | accepted | 2026-04-06 |
| [HIST-ADR-003](./HIST-ADR-003-docker-first-arm64.md) | Docker-first y objetivo Raspberry Pi (ARM64) | accepted | 2026-02-16 |

## Origen

Las tres se registraron el 2026-10-29, **retrospectivamente**, a partir del código, `git log` y la constitution. El repo no tenía ADR previas; las fechas son las de los commits que introdujeron cada cosa.

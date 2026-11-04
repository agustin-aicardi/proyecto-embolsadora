---
title: Índice de specs de proyecto-embolsadora
owner: Federico Degiovanni
last_reviewed: 2026-10-29
---

# Specs de `proyecto-embolsadora`

Índice curado a mano. La referencia entre repos es siempre `<repo>#NNN` (por ejemplo `proyecto-embolsadora#001`). El próximo número libre es **002**.

## Índice

| # | Título | Tier | Estado | Veredicto | Fecha | PRs |
|---|---|---|---|---|---|---|
| [001](./001-historian-semantico/spec.md) | Historian semántico — PLC a InfluxDB y AAS | change | done | A | 2026-10-29 | — |

**Veredicto** = resultado de la reconciliación contra el código (harness documental §6.1): A implementado como se especificó, B implementado distinto, C descartado, D todavía querido, E basura. La 001 es **retrospectiva**: se escribió leyendo el código, así que su A es trivial (todos sus `RF` son `origen: derivado`). Lo que importa de ella son los desvíos contra la constitution.

## Pendientes (veredicto D: exigido por la constitution, nunca construido)

No tienen directorio en `specs/` porque no hay spec propia; figuran acá hasta que se abra una. No se crearon issues de GitHub: es una acción visible para el resto del equipo.

| Pendiente | Origen | Evidencia |
|---|---|---|
| **Tipo `int32`** | Constitution, «Data Handling» (soporte obligatorio) | `read_tag` lanza `ValueError` para tipos fuera de `bool`/`int16`/`float32` |
| **Reintento de escritura en InfluxDB cada 5 s** | Constitution, principio V | Solo la lectura Modbus se reintenta; un `influx.write_failed` descarta el punto |
| **Healthcheck / métricas del historian** | Ninguno: observación al derivar la 001 | El proceso no expone endpoint alguno |

## Notas

- Numeración: el repo no tenía specs (tenía 18 archivos de speckit y cero specs; se eliminaron). La 001 es la primera.
- Las specs nuevas se escriben con `superpowers:brainstorming` en `specs/NNN-slug/`, con las plantillas de `.specify/templates/`.

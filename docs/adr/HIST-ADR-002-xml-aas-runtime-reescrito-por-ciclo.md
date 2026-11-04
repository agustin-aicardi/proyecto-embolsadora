---
id: HIST-ADR-002
title: "El XML AAS runtime se reescribe completo en cada ciclo y lo sirve FA³ST"
status: accepted
date: 2026-04-06
deciders: [Agustín Aicardi]
supersedes:
superseded_by:
owner: Federico Degiovanni
last_reviewed: 2026-10-29
---

# HIST-ADR-002 — El XML AAS runtime se reescribe completo en cada ciclo y lo sirve FA³ST

> **Registrada retrospectivamente el 2026-10-29** desde el código y `git log` (commit `c6a9ba8`, 2026-04-06). La decisión es anterior; no se encontró un documento que la registre.

## Contexto y problema

Además de la serie temporal, el sistema mantiene una representación AAS viva de la máquina. FA³ST (`fraunhoferiosb/faaast-service`) carga un XML inicial y lo sirve por HTTP.

## Decisión

Con `AAS_XML_PATH`, `AAS_MAPPING_PATH` y `AAS_OUTPUT_PATH` definidas, `AASUpdater` actualiza las properties del `Embolsadora_V3.xml` con los valores `GOOD` de cada ciclo y **guarda el XML completo** en `runtime/Embolsadora_runtime.xml`, que es el `initialModelFile` de FA³ST (`faaast/config.json`). El compose de este repo lo tiene activado.

## Consecuencias

- Costo de escritura alto: el XML pesa ~548 KB y se reescribe en cada ciclo de 1 s (~47 GB/día según la estimación del bundle). En una tarjeta SD de Raspberry Pi es desgaste innecesario si nadie consume el XML.
- Por eso `embolsadora-bundle` deja esta función **apagada** en el stack base y la ofrece como override opcional ([BUNDLE-ADR-004](https://github.com/fdegiovanni/embolsadora-bundle/blob/main/docs/adr/BUNDLE-ADR-004-fa3st-como-override.md)). Este repo no la desactivó por defecto.
- Pregunta abierta: ahora que el edge lee el catálogo directo de `aas_mapping.yaml`, si el XML runtime sigue teniendo un consumidor real. Si no, corresponde una ADR que reemplace esta.

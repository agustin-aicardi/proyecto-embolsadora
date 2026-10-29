---
id: HIST-ADR-001
title: "La semántica AAS viaja en los tags de InfluxDB, definida por aas_mapping.yaml"
status: accepted
date: 2026-04-07
deciders: [Agustín Aicardi]
supersedes:
superseded_by:
owner: Federico Degiovanni
last_reviewed: 2026-10-29
---

# HIST-ADR-001 — La semántica AAS viaja en los tags de InfluxDB, definida por aas_mapping.yaml

> **Registrada retrospectivamente el 2026-10-29**, reconstruida desde el código y `git log` (commits `c6a9ba8`, `ce4cd7b`, tag `v0.3-historian-semantic`). El repo no tenía ADR; la decisión es anterior y no se encontró un documento que la registre. Si el autor recuerda alternativas que se evaluaron, hay que agregarlas.

## Contexto y problema

El proyecto busca separar el **dato histórico** (InfluxDB) de la **estructura semántica** (AAS) sin perder la relación entre ambos. Un nombre de variable plano (`peso`) no dice a qué submodelo ni colección del AAS pertenece.

## Decisión

`src/historian/aas_mapping.yaml` es la fuente del mapeo tag → AAS. Para cada tag habilitado define el measurement (`historian_semantic` por defecto) y los tags de InfluxDB `aas_submodel`, `aas_collection` (cuando existe) y `aas_property`; el field lleva el nombre del tag. Un tag sin entrada **no se escribe** (`mapping.missing_for_tag`).

## Consecuencias

- El esquema de InfluxDB y `aas_mapping.yaml` son un **contrato externo** consumido por otros repos: `embolsadora-edge` los lee para agrupar y reenviar (monta el mismo archivo), y el frontend referencia variables por `aasPath`. Renombrar una property rompe esos consumidores en silencio. Un cambio en el mapping es un cambio de contrato: coordinar con esos repos.
- Sin `AAS_MAPPING_PATH` el historian no escribe nada en InfluxDB. Es fácil de olvidar en un despliegue nuevo.
- `runtime/catalog.json` es derivado del YAML; la fuente es el YAML.

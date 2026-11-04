---
id: "NNN"                       # próximo número libre de specs/README.md
title: <título corto>
tier: feature                   # feature | change
status: draft                   # draft | approved | in-progress | done | partial | abandoned | superseded
owner: <persona>
date: AAAA-MM-DD
repos: [proyecto-embolsadora]
origin: nuevo                   # speckit | superpowers | nuevo
issues: []
prs: []
adrs: []
veredicto:                      # A | B | C | D | E (§6.1) — resultado de reconciliar la spec con el código; vacío hasta reconciliar
reconciliado:                   # AAAA-MM-DD de esa reconciliación; va siempre junto con veredicto
divergencia:                    # ref a la bitácora de alcance; obligatorio si veredicto es B o C, o si status es partial, abandoned o superseded
supersedes:
superseded_by:
---

# NNN — <título>

## Contexto y problema

<!-- Narrativa libre, escalada a la complejidad real. Causa raíz cuando aplica.
     Los casos de uso se REFERENCIAN al hub (UC-xx), no se copian. -->

## Alcance

<!-- Qué entra y, explícitamente, qué no. -->

## Requisitos

<!-- RF-NNN funcional, RNF-NNN no funcional. Cada uno con su procedencia y su trazabilidad.
     `original`: estaba escrito en el documento de origen (con su fecha).
     `derivado`: se reconstruyó leyendo código, PRs y tests. Un RF derivado nunca se presenta como previo. -->

- **RF-001** `origen: original` — El sistema DEBE … → UC-xx

## Criterios de éxito

<!-- CE-NNN, medibles y verificables. -->

- **CE-001** — …

## Decisiones

<!-- Decisión, alternativas consideradas y porqué. Si es difícil de revertir, enlazá su ADR en docs/adr/. -->

| Decisión | Alternativas | Porqué |
|---|---|---|

## Riesgos y preguntas abiertas

<!-- Secciones opcionales a continuación: «Entidades clave» y «Modelo de datos». -->

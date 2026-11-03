---
id: "007"
title: Publicar la imagen multi-arch del historian
tier: change
status: in-progress
owner: Federico Degiovanni
date: 2026-11-02
repos: [proyecto-embolsadora, embolsadora-bundle]
origin: nuevo
issues: []
prs: []
adrs: [HIST-ADR-004]
veredicto:
reconciliado:
divergencia:
supersedes:
superseded_by:
last_reviewed: 2026-11-02
---

# 007 — Publicar la imagen multi-arch del historian

## Contexto y problema

La CI publicaba `ghcr.io/<repo>:latest` desde un paso dentro del job `test-and-build`, con tres limitaciones:

1. **Solo arm64.** Una imagen amd64 (para probar en un portátil o en un servidor) no sale de la CI.
2. **Antes de la integración.** El paso corría antes del job `integration` (que levanta InfluxDB y comprueba que el historian escribe). Una imagen que no pasa esa prueba igual quedaba publicada como `latest`.
3. **Sin forma de fijar una versión.** Solo existía `latest`, que se mueve con cada merge.

Con esto, instalar el stack en una Raspberry Pi obliga a clonar el repo y compilar la imagen ahí. `embolsadora-bundle` quiere un modo «solo imágenes» (sin clonar ni compilar) que necesita una imagen publicada, multi-arch y con una versión fijable.

## Alcance

Entra: un job `publish` en `.github/workflows/ci.yml` y el retiro del paso de publicación anterior. No entra: cambiar el `Dockerfile`, firmar ni escanear la imagen, ni qué ocurre en un pull request (que no publica, como antes).

## Requisitos

- **RF-001** `origen: original` — En un push a `main`, DEBE publicarse `ghcr.io/<repo>` para `linux/amd64` y `linux/arm64` en una sola etiqueta (manifiesto multi-arch).
- **RF-002** `origen: original` — La publicación DEBE ocurrir solo si el job `integration` pasó.
- **RF-003** `origen: original` — DEBE publicar `latest` y `sha-<corto>`; esta última permite fijar una versión exacta.
- **RF-004** `origen: original` — Un pull request NO DEBE publicar.
- **RF-005** `origen: original` — NO DEBE existir otro paso que publique `latest` (se retira el anterior, que era arm64-only y previo a la integración).
- **RF-006** `origen: original` — DEBE seguir usando `CR_PAT` si está cargado y, si no, `GITHUB_TOKEN` (comportamiento anterior), con `packages: write` declarado de forma explícita.

## Criterios de éxito

- **CE-001** — `actionlint` no marca nada en el job nuevo. **Cumplido** (v1.7.7). Marca avisos **previos** en acciones viejas del workflow (`setup-python@v4`, `setup-qemu-action@v2`, `setup-buildx-action@v2`) que no se tocaron.
- **CE-002** — Tras mergear a `main`, `docker buildx imagetools inspect ghcr.io/<repo>:latest` lista `linux/amd64` y `linux/arm64`. **Pendiente**: el job nunca corrió.
- **CE-003** — La imagen amd64 arranca (`docker run` con el mock) y la arm64 en una Raspberry Pi real. **Pendiente.**

## Decisiones

| Decisión | Alternativas | Porqué |
|---|---|---|
| Un job aparte con `needs: integration` | Dejar el paso donde estaba y agregarle amd64 | Garantiza que lo publicado pasó la prueba de integración |
| Manifiesto multi-arch con buildx | Dos etiquetas (`-arm64`, `-amd64`) | Un `docker pull` elige la arquitectura sola |
| Etiquetas `latest` + `sha-<corto>` | Etiquetas de versión | No hay tags de release en el repo; el `sha` permite fijar |
| Se conserva el nombre `ghcr.io/<repo>` | Un nombre nuevo | Quien ya usaba `latest` sigue funcionando |

## Riesgos y preguntas abiertas

- **El job nunca corrió.** Si falla el login, los permisos o el build con QEMU, se ve en la primera corrida en `main`.
- **Visibilidad del paquete.** Este repo es público, pero un paquete de GHCR puede quedar privado hasta que se cambie su visibilidad (o se lo enlace al repo). Hay que comprobar, después de la primera publicación, que `docker pull` anda sin `docker login`.
- **El `ci.yml` solo se dispara para PRs con base `main` o `master`**: un PR apilado sobre otra rama no corre los tests ni el build en la CI (solo el workflow `harness`). Es una limitación previa, no de esta spec.
- Acciones viejas en el workflow (ver CE-001): hoy funcionan; conviene actualizarlas antes de que GitHub deje de aceptarlas.
- Sin firma ni escaneo de la imagen.

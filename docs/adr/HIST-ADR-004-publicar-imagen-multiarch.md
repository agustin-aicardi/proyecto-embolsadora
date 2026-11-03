---
id: HIST-ADR-004
title: "Publicar la imagen multi-arch con la integración como condición"
status: accepted
date: 2026-11-02
deciders: [Federico Degiovanni]
supersedes:
superseded_by:
owner: Federico Degiovanni
last_reviewed: 2026-11-02
---

# HIST-ADR-004 — Publicar la imagen multi-arch con la integración como condición

## Contexto y problema

[HIST-ADR-003](./HIST-ADR-003-docker-first-arm64.md) registra que la CI publica `ghcr.io/<repo>:latest`, **solo arm64**, sin etiquetas de versión. En la práctica el paso corría antes del job de integración, así que una imagen que no escribía en InfluxDB igual quedaba como `latest`, y no había forma de fijar una versión ni de usar la imagen en amd64. Más detalle en la [spec 007](../../specs/007-imagen-multiarch/spec.md).

## Decisión

Esta decisión **reemplaza el tercer punto de la «Decisión» de HIST-ADR-003** (lo referente a la publicación); el resto de esa ADR (Docker-first, imagen base `slim`, objetivo Raspberry Pi) sigue vigente, por eso HIST-ADR-003 no queda marcada como reemplazada.

La CI publica `ghcr.io/<repo>` en un job aparte que corre **después** de `integration` y solo en un push a `main`, para `linux/amd64` y `linux/arm64` en un único manifiesto, con las etiquetas `latest` y `sha-<corto>`. Un pull request no publica.

## Consecuencias

- Se puede usar la imagen en amd64 (portátil, servidor) y en la Pi con el mismo `docker pull`, y fijar una versión exacta con `sha-<corto>`.
- Una imagen que no pasó la integración no se publica.
- El tiempo de la CI en `main` crece (build multi-arch con QEMU).
- El paquete puede requerir un cambio manual de visibilidad la primera vez (ver spec 007).
- No hay firma ni escaneo de vulnerabilidades.

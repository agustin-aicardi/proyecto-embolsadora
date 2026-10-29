---
id: HIST-ADR-003
title: "Docker-first y objetivo Raspberry Pi (ARM64)"
status: accepted
date: 2026-02-16
deciders: [Agustín Aicardi]
supersedes:
superseded_by:
owner: Federico Degiovanni
last_reviewed: 2026-10-29
---

# HIST-ADR-003 — Docker-first y objetivo Raspberry Pi (ARM64)

> Esta decisión **sí está escrita** en `.specify/memory/constitution.md` (principios III y IV, ratificada el 2026-02-16). Esta ADR solo la hace visible como decisión de despliegue y registra cómo se cumple hoy.

## Contexto y problema

El historian corre junto a la máquina, en una Raspberry Pi. Hace falta un empaquetado reproducible, liviano y para ARM64.

## Decisión

- El sistema se orquesta con Docker Compose y los servicios se hablan por **nombre de servicio**, no por IP ni `localhost`.
- La imagen base es `python:3.11-slim-bookworm`.
- La CI construye `linux/arm64` con QEMU/Buildx y, en `main`, publica `ghcr.io/<repo>:latest`. **Solo arm64**, sin etiquetas de versión.

## Consecuencias

- Una imagen amd64 (para desarrollo en un portátil) no sale de la CI: se construye local con `docker compose build`.
- `latest` es lo único publicado: no hay forma de fijar una versión de la imagen.
- La instalación en una Pi real junto al edge la cubre `embolsadora-bundle`, que construye esta imagen desde el código en lugar de bajarla de GHCR.

---
id: "002"
title: INFLUX_TOKEN obligatorio, sin valor por defecto
tier: change
status: in-progress
owner: Federico Degiovanni
date: 2026-11-02
repos: [proyecto-embolsadora]
origin: nuevo
issues: []
prs: []
adrs: []
veredicto:
reconciliado:
divergencia:
supersedes:
superseded_by:
last_reviewed: 2026-11-02
---

# 002 — INFLUX_TOKEN obligatorio, sin valor por defecto

## Contexto y problema

Si `INFLUX_TOKEN` no está definido, `main.py` usaba el valor `"my-token"`. El historian arrancaba "bien" y recién fallaba en la primera escritura con un 401 (`influx.write_failed`), un mensaje que apunta a un token *incorrecto* y no a uno *ausente*. Con `docker compose` el caso es todavía más engañoso: `INFLUX_TOKEN=${INFLUX_TOKEN}` entrega una cadena vacía cuando falta en el `.env`, y un valor por defecto que no autentica oculta el error de configuración.

Es el desvío «Token por defecto» que dejó anotado la [spec 001](../001-historian-semantico/spec.md).

## Alcance

Entra: `INFLUX_TOKEN` pasa a ser obligatorio. No entra: el resto de las variables (`INFLUX_URL`, `INFLUX_ORG`, `INFLUX_BUCKET` mantienen sus valores por defecto), la rotación del token ni cómo se guarda.

## Requisitos

- **RF-001** `origen: original` — Si `INFLUX_TOKEN` no está definida, está vacía o tiene solo espacios, el historian NO DEBE arrancar: DEBE registrar `config.invalid` (con el nombre de la variable que falta, nunca su valor) y terminar con código de salida 1.
- **RF-002** `origen: original` — El historian NO DEBE usar ningún valor por defecto para el token.

## Criterios de éxito

- **CE-001** — Los tests de `require_env` (`tests/test_config.py`) pasan con `python3 run_tests.py`.
- **CE-002** — Arrancar el contenedor sin `INFLUX_TOKEN` termina de inmediato con `config.invalid` en el log. **Cumplido** (imagen construida y corrida con `docker run` sin token: `config.invalid`, exit 1).
- **CE-003** — El job `integration` de la CI (que define `INFLUX_TOKEN=ci-token`) sigue escribiendo puntos. **Se verifica en la CI de este PR.**

## Decisiones

| Decisión | Alternativas | Porqué |
|---|---|---|
| Fallar al arrancar con `SystemExit(1)` | Seguir arrancando y solo avisar con un `warning` | Un historian que no puede autenticar no hace nada útil, y arrancar «en silencio» es lo que ocultaba el error. Con `restart: unless-stopped` el reinicio en bucle deja el motivo visible en `docker compose logs` |
| La validación vive en `config.py`, no en `main.py` | Dejarla inline | `main.py` importa pymodbus e influxdb-client; en módulo aparte se testea sin esas dependencias |

## Riesgos y preguntas abiertas

- **Cambio de comportamiento:** quien hoy corre el historian sin `INFLUX_TOKEN` (y por lo tanto sin que nada se escriba) ahora verá que no arranca. Es el efecto buscado. Las configuraciones del repo ya lo definen: `docker-compose.yml` y la CI.
- El arranque fallido en bucle de reinicios consume poco, pero es ruidoso; si molestara, se puede pasar a `restart: on-failure:5`.

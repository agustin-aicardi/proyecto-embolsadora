---
id: "005"
title: Healthcheck del historian
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

# 005 — Healthcheck del historian

## Contexto y problema

El historian es un solo proceso con un solo bucle y no expone nada: ni un puerto, ni un archivo, ni una métrica. Si se cuelga (una lectura Modbus que no vuelve, un bloqueo en la escritura) o muere sin que Docker lo note, el contenedor sigue figurando como `Up` y solo se descubre mirando los logs, o cuando el edge reporta que ya no llegan datos. `docker compose ps` no puede decir si el historian está vivo de verdad.

Es el desvío «Sin healthcheck ni métricas» de la [spec 001](../001-historian-semantico/spec.md).

## Alcance

Entra: un latido por ciclo y un `HEALTHCHECK` de Docker que lo comprueba. No entra: métricas (Prometheus), un endpoint HTTP, ni medir que el PLC o InfluxDB estén bien (eso es otra pregunta).

## Requisitos

- **RF-001** `origen: original` — El historian DEBE actualizar un archivo de latido (`HEARTBEAT_FILE`, por defecto `historian.alive` en el directorio temporal del sistema) al final de cada ciclo, sin importar si las lecturas o las escrituras fallaron.
- **RF-002** `origen: original` — Un fallo al escribir el latido NO DEBE detener el historian: DEBE avisar una sola vez con `heartbeat.failed`.
- **RF-003** `origen: original` — `python -m src.historian.heartbeat` DEBE salir con 0 si el latido existe y es más reciente que el máximo, y con 1 si no existe o es más viejo, imprimiendo el motivo.
- **RF-004** `origen: original` — El máximo DEBE ser `HEALTH_MAX_AGE_S` si está definida; si no, el mayor entre 120 s y 3 × `POLL_INTERVAL`.
- **RF-005** `origen: original` — La imagen DEBE declarar un `HEALTHCHECK` que ejecute esa comprobación (intervalo 30 s, 60 s de gracia al arrancar, 3 fallos para `unhealthy`), sin depender de `curl` ni de otro paquete.
- **RF-006** `origen: original` — "Sano" significa **que el proceso sigue ciclando**, no que el PLC o InfluxDB estén bien: con el PLC o InfluxDB caídos el ciclo se completa (specs 003 y 004) y el contenedor sigue `healthy`.

## Criterios de éxito

- **CE-001** — `tests/test_heartbeat.py` (7 tests) pasa con `python3 run_tests.py`. **Cumplido.**
- **CE-002** — La imagen construye y, levantada con el mock y un InfluxDB inexistente, pasa a `healthy`. **Cumplido** (build local en amd64, `docker inspect`: `healthy`, último latido hace 8 s).
- **CE-003** — Con un latido viejo, el comando de salud sale con 1. **Cumplido** (`HEALTH_MAX_AGE_S=0` dentro del contenedor: `unhealthy`, exit 1).
- **CE-004** — Un historian realmente colgado (bloqueado en una lectura) pasa a `unhealthy` y Docker lo reporta. **Sin evidencia directa**: se probó el comando con un latido viejo, no con un proceso bloqueado.
- **CE-005** — Build y healthcheck en arm64. **Sin evidencia**: solo se probó en amd64.

## Decisiones

| Decisión | Alternativas | Porqué |
|---|---|---|
| Latido en un archivo | Servidor HTTP con `/health`; chequear que el proceso exista | No agrega puertos ni dependencias y el servicio sigue siendo un solo bucle. Un chequeo de "proceso existe" no detecta un bucle bloqueado |
| La comprobación es un módulo Python de la propia imagen | `curl`, `test -f`/`find -mmin` | La imagen slim no trae `curl`, y `python` ya está. Se testea con tests unitarios |
| Sano = sigue ciclando, no "todo está bien" | Marcar `unhealthy` si el PLC o InfluxDB fallan | Reiniciar el historian no arregla un PLC caído, y un contenedor que se reinicia en bucle por un problema externo tapa el motivo real. Los problemas externos se ven en los logs (`cycle.reads_skipped`, `cycle.writes_skipped`) |
| Máximo de 120 s | Un valor más ajustado | Un ciclo con el PLC y InfluxDB caídos puede llegar a ~20 s; 120 s deja margen sin tardar en detectar un cuelgue |

## Riesgos y preguntas abiertas

- `docker compose` (v2) muestra `healthy`/`unhealthy` pero **no reinicia** un contenedor `unhealthy` por sí solo. Esta spec da la señal; actuar sobre ella (por ejemplo con `autoheal`, o `depends_on: condition: service_healthy` en otros servicios) es decisión de quien opere el stack.
- El latido se escribe en el sistema de archivos del contenedor (un archivo de 0 bytes por ciclo, solo se actualiza su mtime): es un cambio de metadatos mínimo. En una tarjeta SD, 1 escritura de metadatos por segundo es poco comparado con el log; si importara, puede apuntarse `HEARTBEAT_FILE` a `/dev/shm`.
- Si un ciclo dura más de 120 s por una causa no prevista (p. ej. `AASUpdater` muy lento), el contenedor pasaría a `unhealthy` sin estar colgado. Se ajusta con `HEALTH_MAX_AGE_S`.

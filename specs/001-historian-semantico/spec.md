---
id: "001"
title: Historian semántico — PLC a InfluxDB y AAS
tier: change
status: done
owner: Federico Degiovanni
date: 2026-10-29
repos: [proyecto-embolsadora]
origin: nuevo
issues: []
prs: []
adrs: [HIST-ADR-001, HIST-ADR-002, HIST-ADR-003]
veredicto: A
reconciliado: 2026-10-29
divergencia:
supersedes:
superseded_by:
last_reviewed: 2026-10-29
---

# 001 — Historian semántico: PLC a InfluxDB y AAS

> **Spec retrospectiva.** El repo no tenía ninguna spec: la constitution y el README describen el sistema, pero no hay requisitos numerados. Esta se escribió el 2026-10-29 **leyendo el código** (`src/historian/`), no un documento previo; por eso todos los requisitos son `origen: derivado` y ninguno debe citarse como especificado por adelantado. El veredicto A significa «el código hace lo que acá se describe», que es trivial en una spec derivada; los desvíos contra la **constitution** están en «Riesgos y preguntas abiertas».

## Contexto y problema

El proyecto es la capa de adquisición y de información semántica de una embolsadora (tesis de Informática Industrial). Un servicio Python (el *historian*) lee variables del PLC por Modbus TCP, las guarda en InfluxDB con tags semánticos derivados del Asset Administration Shell (AAS) y, opcionalmente, mantiene un XML AAS en runtime que sirve FA³ST. La separación buscada es: **datos históricos** en InfluxDB, **estructura semántica** en el AAS, y una relación consistente entre ambas dada por `aas_mapping.yaml`.

Hoy el PLC es simulado (`MODBUS_HOST=mock`). Lo consumen: `embolsadora-edge` (lee el measurement y el catálogo para reenviar al cloud) y, a través del cloud, el frontend (que referencia cada variable por su `aasPath`).

## Alcance

Entra: el ciclo de lectura/escritura del historian, el mapeo de tags, el esquema que se escribe en InfluxDB, el AAS updater opcional y el generador de catálogo. No entra: el edge, el cloud, el frontend, el empaquetado para la Raspberry Pi (`embolsadora-bundle`) ni un PLC real (no hay evidencia de que se haya probado contra uno).

## Requisitos

- **RF-001** `origen: derivado` — El historian DEBE cargar los tags desde un YAML (`HISTORIAN_TAGS`, por defecto `./tags.yaml`), cada uno con `name`, `type`, `address`, y opcionalmente `unit` (default 1), `byteorder` (default `big`) y `scale`. → `tag_loader.py`
- **RF-002** `origen: derivado` — DEBE leer por ciclo cada tag por Modbus TCP según su tipo: `bool` (coil), `int16` (1 registro) y `float32` (2 registros, con orden de palabras `big`/`little`). Un tipo distinto DEBE fallar con `ValueError`. → `modbus_reader.py`, `parsers.py`
- **RF-003** `origen: derivado` — Si `MODBUS_HOST=mock`, DEBE usar el cliente simulado en lugar de abrir una conexión Modbus. → `main.py`, `mock_modbus.py`
- **RF-004** `origen: derivado` — Ante un error de lectura DEBE reintentar hasta 3 veces por tag, esperando 5 s entre intentos; si no obtiene valor, DEBE marcar el tag `BAD` y seguir con el siguiente. → `main.py`
- **RF-005** `origen: derivado` — DEBE escribir cada valor leído en InfluxDB 2.x en el measurement definido por `aas_mapping.yaml` (`historian_semantic` por defecto), con los tags `aas_submodel`, `aas_collection` (cuando existe) y `aas_property`, un field cuyo nombre es el del tag y el timestamp del ciclo en nanosegundos. Tipos: `bool`, `int` y `float` se escriben tal cual; cualquier otro, como string. → `influx_writer.py`, `aas_mapping.yaml`
- **RF-006** `origen: derivado` — Un tag sin entrada habilitada en `aas_mapping.yaml` (o sin `AAS_MAPPING_PATH`) NO DEBE escribirse en InfluxDB: DEBE registrar `mapping.missing_for_tag` y continuar. → `main.py`
- **RF-007** `origen: derivado` — Un fallo de escritura en InfluxDB NO DEBE detener el ciclo: DEBE marcar el tag `INFLUX_WRITE_FAILED` y registrar `influx.write_failed`. → `main.py`
- **RF-008** `origen: derivado` — Si están definidas las tres variables `AAS_XML_PATH`, `AAS_MAPPING_PATH` y `AAS_OUTPUT_PATH`, DEBE actualizar las properties del XML AAS con los valores `GOOD` de cada ciclo y guardar el XML en `AAS_OUTPUT_PATH`. Antes DEBE validar la estructura del mapping (destinos existentes, sin duplicados, nombres presentes en `tags.yaml`). → `aas_updater.py`
- **RF-009** `origen: derivado` — DEBE poder generar un catálogo de variables (`runtime/catalog.json` y `runtime/catalog.md`) a partir de `aas_mapping.yaml`. → `generate_catalog.py`
- **RF-010** `origen: derivado` — DEBE emitir logs estructurados en JSON (una línea por evento, con `ts`, `level`, `msg` y campos) a la salida estándar. → `main.py`
- **RNF-001** `origen: derivado` — La imagen DEBE construirse para `linux/arm64` sobre `python:3.11-slim-bookworm`. → `Dockerfile`, `ci.yml`

## Criterios de éxito

- **CE-001** — Los tests unitarios (`python3 run_tests.py`) pasan. **Cumplido** (verificado 2026-10-29: «All tests passed», con parsers y mock Modbus).
- **CE-002** — En el job `integration` de la CI, el historian contra InfluxDB 2.6 escribe al menos un punto de `historian_semantic` en los últimos 10 min (`ci_verify.py`). **No verificado hoy**: se ejecuta en GitHub Actions.
- **CE-003** — El historian corre contra un PLC Modbus real. **Sin evidencia**: todo el historial de pruebas usa el mock.

## Decisiones

| Decisión | Alternativas | Porqué |
|---|---|---|
| Los tags de InfluxDB salen de `aas_mapping.yaml` ([HIST-ADR-001](../../docs/adr/HIST-ADR-001-semantica-aas-en-tags-de-influxdb.md)) | Nombres de tag planos sin AAS | Reconstruir la jerarquía AAS desde la base de datos |
| El XML AAS se reescribe completo por ciclo y lo sirve FA³ST ([HIST-ADR-002](../../docs/adr/HIST-ADR-002-xml-aas-runtime-reescrito-por-ciclo.md)) | Actualizar FA³ST por su API | Simplicidad; tiene un costo de escritura alto |
| Docker-first, ARM64, imágenes slim ([HIST-ADR-003](../../docs/adr/HIST-ADR-003-docker-first-arm64.md)) | Instalación nativa | Target: Raspberry Pi |

## Riesgos y preguntas abiertas

Desvíos entre el código y la constitution (`.specify/memory/constitution.md`), detectados al derivar esta spec:

- **Tipo `int32` no soportado.** La constitution lo declara obligatorio («`bool`, `int16`, `int32` y `float32`»); `read_tag` lanza `ValueError` para cualquier tipo que no sea `bool`, `int16` o `float32`. Ningún tag actual lo usa.
- **Sin reintento de escritura en InfluxDB.** El principio V exige reintentos de 5 s en Modbus **y** en InfluxDB; el código reintenta solo la lectura Modbus. Un fallo de escritura pierde el punto de ese ciclo.
- **Un tag caído frena el ciclo.** 3 intentos × 5 s = hasta 15 s por tag que falla, en serie. Con un PLC caído y 18 tags, un ciclo puede tardar más de 4 minutos y retrasa la escritura de los tags que vienen después en la lista.
- **Token por defecto.** ~~Si falta `INFLUX_TOKEN`, el código usa `my-token` en vez de fallar.~~ Corregido en la [spec 002](../002-influx-token-obligatorio/spec.md).
- **Sin healthcheck ni métricas.** El proceso no expone ningún endpoint; un historian colgado solo se ve en los logs.
- **Sin evidencia de PLC real** (CE-003).
- ¿`AASUpdater` sigue haciendo falta ahora que el edge lee el catálogo directamente? Con el XML reescrito a ~548 KB por ciclo, el bundle lo deja apagado por defecto.

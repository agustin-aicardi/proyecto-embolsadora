---
title: Arquitectura del historian
owner: Federico Degiovanni
status: vigente
last_reviewed: 2026-10-29
---

# Arquitectura

Arquitectura **interna** del historian. La vista de sistema (edge, cloud, frontend) vive en el hub [`embolsadora-docs`](https://github.com/fdegiovanni/embolsadora-docs). El comportamiento requerido, derivado del código, está en la [spec 001](../specs/001-historian-semantico/spec.md).

## Pipeline

```text
PLC (Modbus TCP)  ──►  historian (Python)  ──►  InfluxDB 2.x  (historian_semantic)
  o mock_modbus            │                          ▲
                           │ (opcional)               └── lo lee embolsadora-edge
                           └──► runtime/Embolsadora_runtime.xml ──► FA³ST (:8081)
        tags.yaml (qué leer)  +  aas_mapping.yaml (cómo etiquetar)
```

El historian es **un solo proceso de un solo hilo** (`python -m src.historian.main`): un bucle que, cada `POLL_INTERVAL` segundos, lee todos los tags y los escribe.

## Módulos (`src/historian/`)

| Archivo | Rol |
|---|---|
| `main.py` | Bucle principal: carga config por variables de entorno, lee, escribe, actualiza el AAS y emite los logs JSON |
| `tag_loader.py`, `models.py` | Cargan `tags.yaml` como `TagConfig` (`name`, `type`, `address`, `unit`, `byteorder`, `scale`) |
| `modbus_reader.py` | `read_tag`: una lectura según el tipo (`bool`, `int16`, `float32`); otro tipo lanza `ValueError` |
| `parsers.py` | Conversión pura registros → valor (signo de int16, float32 con orden de palabras). Es lo más testeado |
| `mock_modbus.py` | PLC simulado (`MODBUS_HOST=mock`) |
| `influx_writer.py` | Un `Point` por valor, escritura síncrona |
| `aas_updater.py` | Valida el mapping y actualiza las properties del XML AAS |
| `generate_catalog.py` | Genera `runtime/catalog.json` y `catalog.md` desde `aas_mapping.yaml` |

## Un ciclo

1. Por cada tag: leer con hasta 3 intentos y 5 s de espera entre ellos. Sin valor → calidad `BAD` y se sigue. Si un tag agota los intentos por excepción (PLC sin respuesta), **los tags restantes de ese ciclo no se leen** (`reason: plc_unreachable`, log `cycle.reads_skipped`) y el ciclo siguiente reintenta desde el primero ([spec 003](../specs/003-ciclo-acotado-plc-caido/spec.md)). La lógica está en `read_policy.py`.
2. Buscar el tag en `aas_mapping.yaml`. Sin entrada habilitada → `mapping.missing_for_tag`, no se escribe.
3. Escribir el punto en InfluxDB. Si falla → calidad `INFLUX_WRITE_FAILED` y se sigue (no se reintenta).
4. Si el AAS updater está activo: actualizar el XML con los valores `GOOD` y guardarlo completo.
5. Registrar `cycle.completed` con `tags_ok` y `tags_bad`, y dormir `POLL_INTERVAL`.

## Esquema en InfluxDB (contrato que consumen otros repos)

| Elemento | Valor |
|---|---|
| Measurement | `historian_semantic` (configurable en `aas_mapping.yaml: defaults.historian.measurement`) |
| Tags | `aas_submodel`, `aas_collection` (puede faltar), `aas_property` |
| Field | nombre = tag; valor `bool`/`int`/`float`, o string para cualquier otro |
| Time | timestamp del ciclo, en ns |

`aas_mapping.yaml` define 18 variables: 16 de clase `runtime` y 2 de clase `alarm`. Ver [HIST-ADR-001](./adr/HIST-ADR-001-semantica-aas-en-tags-de-influxdb.md).

## Lo que este diseño no tiene

Contrastado con la constitution (detalle en la spec 001): no hay tipo `int32`, no se reintenta la escritura en InfluxDB, no hay healthcheck ni métricas. La constitution es la autoridad; estos puntos están en el índice de specs como pendientes.

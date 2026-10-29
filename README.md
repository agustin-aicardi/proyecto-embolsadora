# Proyecto Embolsadora – IIoT Historian & Asset Administration Shell

## Qué es y dónde corre

El *historian* de la máquina embolsadora: un servicio Python que lee variables del PLC por **Modbus TCP**, las guarda en **InfluxDB 2.x** con tags semánticos derivados del **Asset Administration Shell (AAS)** y, opcionalmente, mantiene un XML AAS en runtime que sirve **FA³ST**. Forma parte de una tesis de maestría en Informática Industrial (AAS, IIoT, series temporales, RAMI 4.0). Uso académico.

Corre en contenedores Docker sobre una **Raspberry Pi** (imagen `linux/arm64`, base `python:3.11-slim-bookworm`). Hoy el PLC es **simulado** (`MODBUS_HOST=mock`); no hay evidencia de pruebas contra un PLC real.

## Quickstart

Requisitos: Docker con Compose v2.

```bash
git clone https://github.com/agustin-aicardi/proyecto-embolsadora.git
cd proyecto-embolsadora
cp .env.example .env        # completar INFLUX_TOKEN (openssl rand -hex 32)
docker compose up -d --build
docker compose logs --tail 20 app    # deben verse "point.written" y "cycle.completed"
```

InfluxDB queda en `http://localhost:8086` (org `org`, bucket `bucket`). Último valor de una variable:

```flux
from(bucket: "bucket")
  |> range(start: -10m)
  |> filter(fn: (r) => r._measurement == "historian_semantic")
  |> filter(fn: (r) => r._field == "peso")
  |> last()
```

Para correr junto a `embolsadora-edge` en una Pi con **una sola** InfluxDB, no levantar este compose: usar [`embolsadora-bundle`](https://github.com/fdegiovanni/embolsadora-bundle).

## Arquitectura

Un único proceso en bucle: lee cada tag del PLC, lo etiqueta con `aas_mapping.yaml` y lo escribe en InfluxDB; opcionalmente actualiza el XML AAS. Detalle y esquema en [`docs/architecture.md`](./docs/architecture.md); lo que el código hace, en la [spec 001](./specs/001-historian-semantico/spec.md).

## Contratos

- **Expone:** el esquema de InfluxDB (measurement `historian_semantic`, tags `aas_submodel`/`aas_collection`/`aas_property`) y `src/historian/aas_mapping.yaml`, que consumen `embolsadora-edge` y, vía el cloud, el frontend. **Cambiarlos es cambiar un contrato** ([HIST-ADR-001](./docs/adr/HIST-ADR-001-semantica-aas-en-tags-de-influxdb.md)). Catálogo derivado de las variables: [`runtime/catalog.md`](./runtime/catalog.md).
- **Consume:** Modbus TCP del PLC; el mapa de registros está en `src/historian/tags.yaml`.
- Variables de entorno: [`.env.example`](./.env.example).

## Operación

Despliegue, logs, troubleshooting y seguridad: [`docs/operations.md`](./docs/operations.md). Setup local y tests: [`docs/development.md`](./docs/development.md).

## Estado y enlaces

- **Rama activa:** `main`. Último tag: `v0.3-historian-semantic`.
- **Specs:** [`specs/README.md`](./specs/README.md) · **Decisiones:** [`docs/adr/index.md`](./docs/adr/index.md) · **Reglas para agentes:** [`AGENTS.md`](./AGENTS.md) · **Constitution:** [`.specify/memory/constitution.md`](./.specify/memory/constitution.md).
- **Hub de documentación del sistema:** [`embolsadora-docs`](https://github.com/fdegiovanni/embolsadora-docs).

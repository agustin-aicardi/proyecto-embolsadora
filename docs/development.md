---
title: Desarrollo del historian
owner: Federico Degiovanni
status: vigente
last_reviewed: 2026-10-29
---

# Desarrollo

Setup local, tests y regeneración de artefactos derivados. Para desplegar, ver [`operations.md`](./operations.md).

## Requisitos

- Python 3.11 (el del `Dockerfile` y la CI). Los tests también corrieron con 3.10.
- Docker con Compose v2 para el stack completo.
- Dependencias fijadas en `requirements.txt` (`pymodbus==3.1.0`, `influxdb-client==1.33.0`, `PyYAML`, `python-dotenv`, `pytest`). La constitution exige **Pymodbus v3.1.0 o superior** y prohíbe las APIs viejas (`pymodbus.client.sync`).

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
```

## Tests

```bash
python3 run_tests.py
```

`run_tests.py` es un runner propio que importa los módulos de `tests/` y ejecuta las funciones `test_*`, para no depender de pytest. Cubre `parsers` y `mock_modbus`; **no** hay tests de `main.py`, `influx_writer.py` ni `aas_updater.py`. Salida esperada: `All tests passed.`

La CI además corre un job `integration` que levanta InfluxDB 2.6, corre el historian en un contenedor con `MODBUS_HOST=mock` y verifica con `ci_verify.py` que hayan llegado puntos.

## Correr el historian

La forma soportada es el compose (levanta también InfluxDB y FA³ST):

```bash
cp .env.example .env     # completar INFLUX_TOKEN
docker compose up -d --build
docker compose logs -f app
```

Fuera de Docker hace falta una InfluxDB accesible y las variables exportadas:

```bash
MODBUS_HOST=mock HISTORIAN_TAGS=src/historian/tags.yaml \
AAS_MAPPING_PATH=src/historian/aas_mapping.yaml \
INFLUX_URL=http://localhost:8086 INFLUX_TOKEN=... INFLUX_ORG=org INFLUX_BUCKET=bucket \
python3 -m src.historian.main
```

**`AAS_MAPPING_PATH` es obligatoria en la práctica**: sin ella no se escribe ningún punto (cada tag cae en `mapping.missing_for_tag`).

## Variables de entorno

Todas se leen en `src/historian/main.py`; el ejemplo comentado está en [`.env.example`](../.env.example).

| Variable | Por defecto | Para qué |
|---|---|---|
| `HISTORIAN_TAGS` | `./tags.yaml` | Qué leer del PLC |
| `MODBUS_HOST` / `MODBUS_PORT` | `plc` / `502` | `mock` simula el PLC |
| `POLL_INTERVAL` | `1.0` | Segundos entre ciclos |
| `HEARTBEAT_FILE` / `HEALTH_MAX_AGE_S` | tmp del sistema + `historian.alive` / mayor entre 120 y 3 × `POLL_INTERVAL` | Archivo de latido y su antigüedad máxima para el `HEALTHCHECK` de Docker |
| `INFLUX_URL` / `INFLUX_ORG` / `INFLUX_BUCKET` | `http://influxdb:8086` / `org` / `bucket` | Destino |
| `INFLUX_TOKEN` | — (obligatoria) | Sin ella el historian no arranca (`config.invalid`, salida 1) |
| `AAS_MAPPING_PATH` | — | Cómo etiquetar cada tag |
| `AAS_XML_PATH`, `AAS_OUTPUT_PATH` | — | Con las tres `AAS_*` activa el AAS updater |

## Tocar el mapping o los tags

- `tags.yaml` (qué leer) y `aas_mapping.yaml` (cómo etiquetar) se validan en el arranque del AAS updater: destinos existentes, sin duplicados, nombres de mapping presentes en los tags.
- **Cambiar `aas_mapping.yaml` es cambiar un contrato**: lo leen `embolsadora-edge` y, vía el cloud, el frontend (por `aasPath`). Renombrar una property rompe esos consumidores en silencio. Coordinar antes ([HIST-ADR-001](./adr/HIST-ADR-001-semantica-aas-en-tags-de-influxdb.md)).
- Después de cambiarlo, regenerar el catálogo: `python3 -m src.historian.generate_catalog` (reescribe `runtime/catalog.json` y `runtime/catalog.md`, que están versionados).

## Verificar la documentación

```bash
HARNESS_EXPOSES_HTTP=0 bash scripts/harness/check-layout.sh   # layout, prohibiciones, front-matter, specs
bash scripts/harness/test-check-layout.sh                     # los tests del propio verificador
bash scripts/harness/docs-freshness.sh                        # páginas con last_reviewed > 120 días
```

`check-layout.sh` es una **copia** del verificador de `embolsadora-edge`. Si se corrige un bug allá, hay que traerlo acá.

## Specs y ADR

Una feature nueva arranca con `superpowers:brainstorming`, que escribe en `specs/NNN-slug/spec.md` (próximo número en [`specs/README.md`](../specs/README.md)). Una decisión difícil de revertir va a un ADR `HIST-` en `docs/adr/`. La constitution (`.specify/memory/constitution.md`) manda sobre ambas.

## Qué no hacer

- No commitear `.env`, `.venv/`, `__pycache__/`, logs ni binarios: la CI lo bloquea.
- No usar `localhost` ni IP fijas entre servicios del compose (constitution, principio III).

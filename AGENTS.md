# AGENTS.md — proyecto-embolsadora

Fuente única de reglas para agentes (Claude Code, Copilot, Codex). `CLAUDE.md` es un adaptador delgado que incluye este archivo. Si algo se contradice con el código, gana el código: corregí este archivo. La **constitution** ([`.specify/memory/constitution.md`](./.specify/memory/constitution.md)) es la autoridad máxima sobre el stack.

## Qué es

El *historian*: servicio Python que lee el PLC por Modbus TCP, escribe en InfluxDB 2.x con tags semánticos del AAS y, opcionalmente, actualiza un XML AAS que sirve FA³ST. Un solo proceso, un solo bucle. Arquitectura en [`docs/architecture.md`](./docs/architecture.md).

## Comandos

| Qué | Comando |
|---|---|
| Tests | `python3 run_tests.py` (runner propio, sin pytest) → debe decir `All tests passed.` |
| Levantar el stack | `cp .env.example .env` (completar `INFLUX_TOKEN`), luego `docker compose up -d --build` |
| Logs | `docker compose logs -f app` |
| Regenerar el catálogo | `python3 -m src.historian.generate_catalog` (reescribe `runtime/catalog.*`, versionados) |
| Verificador documental | `HARNESS_EXPOSES_HTTP=0 bash scripts/harness/check-layout.sh` |
| Tests del verificador | `bash scripts/harness/test-check-layout.sh` |

Setup completo y variables en [`docs/development.md`](./docs/development.md) y [`.env.example`](./.env.example).

## Reglas del código

- **Pymodbus ≥ 3.1.0**; prohibidas las APIs viejas (`pymodbus.client.sync`, `ModbusSlaveContext`). El orden de palabras (`byteorder`) se maneja en todo tipo de 32 bits. (Constitution, principio II.)
- Los servicios del compose se hablan por **nombre de servicio**, nunca por IP ni `localhost` (principio III). Imágenes `slim`, compatibles con ARM64 (principio IV).
- `aas_mapping.yaml` y el esquema de InfluxDB son un **contrato externo**: los consumen `embolsadora-edge` y, vía el cloud, el frontend (`aasPath`). Un cambio de nombre o de estructura requiere coordinar con esos repos; no renombrar properties «por prolijidad».
- Sin `AAS_MAPPING_PATH` el historian no escribe nada: no hagas que parezca que funciona sin él.
- Un tipo de tag nuevo se agrega en `modbus_reader.py` y `parsers.py` **con test en `tests/`**. Hoy solo hay `bool`, `int16` y `float32`; `int32` falta aunque la constitution lo exige.
- Logs estructurados JSON vía `struct_log`; no usar `print` en el ciclo principal.
- **Nunca commitear `.env`, `.venv/`, `__pycache__/`, binarios ni logs.** El `.env` de este repo estuvo versionado: su historial hay que considerarlo expuesto; no pegues ni muestres credenciales de ahí.
- Los defectos conocidos contra la constitution (sin `int32`, sin healthcheck) están en [`specs/README.md`](./specs/README.md). No los «arregles de paso» dentro de otro cambio: abrí una spec.

## Specs

- `superpowers:brainstorming` escribe el diseño en `specs/NNN-slug/spec.md`,
  NO en `docs/superpowers/specs/`. Tomá el próximo NNN libre de `specs/README.md`.
- `superpowers:writing-plans` escribe en `specs/NNN-slug/plan.md`.
- Todo `spec.md` lleva front-matter completo y al menos un `RF-NNN`.
- Al cerrar una feature, actualizá `status` en el front-matter y la fila en `specs/README.md`.

Formato de `spec.md` y `plan.md`: plantillas en [`.specify/templates/`](./.specify/templates/). Cada requisito lleva su procedencia (`origen: original` o `origen: derivado`); un requisito derivado nunca se presenta como previo al código. La constitution pide el ciclo Specification → Plan → Tasks → Implementation: no se escribe código sin plan.

## Documentación

- Todo `.md` bajo `docs/` lleva front-matter con `title`, `owner`, `status` y `last_reviewed`. Los ADR llevan además `id`, `date`, `deciders`, `supersedes` y `superseded_by`.
- Un ADR es inmutable: una decisión no se edita, se crea otra que la reemplaza. Prefijo `HIST-`; índice en [`docs/adr/index.md`](./docs/adr/index.md). Merece ADR lo difícil de revertir que afecte contratos, persistencia, seguridad o despliegue.
- La arquitectura de **sistema** va al hub [`embolsadora-docs`](https://github.com/fdegiovanni/embolsadora-docs), no a este repo. Los contratos de otros repos se enlazan, no se copian.
- En la raíz solo se permiten `README.md`, `AGENTS.md`, `CLAUDE.md`, `CHANGELOG.md` y `LICENSE`. El resto va dentro de `docs/`.
- No agregar `docs/superpowers/`, `.specify/specs/`, `.github/agents|prompts/speckit.*`, binarios, logs ni `.env`. El workflow `harness` de CI lo verifica ([`scripts/harness/check-layout.sh`](./scripts/harness/check-layout.sh)); es una copia del verificador del edge con `HARNESS_EXPOSES_HTTP=0`.

## Commits y ramas

Conventional Commits (`feat(historian): …`, `docs(adr): …`, `fix(ci): …`). Rama desde `main` y PR.

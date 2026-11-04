@AGENTS.md

## Específico de Claude Code

- Las reglas de este repo están en `AGENTS.md`; no las dupliques acá.
- `superpowers:brainstorming` y `superpowers:writing-plans` escriben en `specs/NNN-slug/`, nunca en `docs/superpowers/` (ver la sección «Specs» de `AGENTS.md`).
- Antes de afirmar que algo funciona, corré `python3 run_tests.py`. Ojo con lo que **no** cubre: no hay tests de `main.py`, `influx_writer.py` ni `aas_updater.py`.
- No leas `.env` ni imprimas su contenido: tuvo credenciales y es de un repo público.

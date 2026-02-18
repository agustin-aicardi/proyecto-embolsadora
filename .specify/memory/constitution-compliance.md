# Constitution Compliance Report

Checked: `.github/prompts/speckit.constitution.prompt.md` (contains agent frontmatter only) and project workspace for artifacts required by the Constitution.

Summary of findings (2026-02-16):

- The project's `.specify/memory/constitution.md` exists and contains explicit rules (Pymodbus v3+, InfluxDB 2.x via `influxdb-client`, Docker-first, ARM64 target, retry logic requirement).
- No `requirements.txt` or `pyproject.toml` explicitly declaring `pymodbus` or `influxdb-client` were found prior to this report.
- No `docker-compose.yml` or Dockerfile was found prior to this report.

Actions taken automatically to help compliance:

- Added `requirements.txt` with pinned `pymodbus==3.1.0` and `influxdb-client==1.33.0`.
- Added a minimal `docker-compose.yml` that defines an `app` service and an `influxdb` service.
- Added a `.dockerignore` with common entries to keep images small.

Recommendations / Next steps:

1. Add or update a `Dockerfile` that uses an ARM64-friendly base (e.g. `python:3.11-slim-bookworm`) and verifies runtime on ARM64. If cross-building on x86_64, add `buildx` config or use multi-arch images.
2. If you use a different dependency manager (poetry, pipenv), add the equivalent manifest (`pyproject.toml`) and pin `pymodbus >=3.1.0` and `influxdb-client` there instead of `requirements.txt`.
3. Implement automated checks (CI) that validate:
   - `pymodbus` version in installed environment
   - Docker image builds successfully for ARM64
   - Presence of retry logic around network calls (unit tests / lint rules)
4. If you want, I can:
   - Create a `Dockerfile` template targeting ARM64.
   - Add a basic CI workflow that builds the Docker image and runs a small lint/test.

If you'd like me to continue and implement any of the recommended steps, tell me which one and I'll proceed.

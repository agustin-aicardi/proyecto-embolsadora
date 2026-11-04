"""Latido del historian y comprobación de salud para el HEALTHCHECK de Docker.

El historian toca un archivo al final de cada ciclo (`beat`). El healthcheck
(`python -m src.historian.heartbeat`) sale con 0 si el archivo es reciente y con 1
si no existe o está viejo: el proceso dejó de dar vueltas (colgado, bloqueado, caído).

Mide que el proceso **sigue ciclando**, no que el PLC o InfluxDB estén bien: con el
PLC caído el ciclo sigue completándose (spec 003) y el latido sigue vivo.
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from collections.abc import Mapping

DEFAULT_MAX_AGE_S = 120.0


def heartbeat_path(environ: Mapping[str, str]) -> str:
    return environ.get("HEARTBEAT_FILE") or os.path.join(tempfile.gettempdir(), "historian.alive")


def max_age_s(environ: Mapping[str, str]) -> float:
    """Antigüedad máxima aceptable del latido. `HEALTH_MAX_AGE_S` la fija a mano.

    Por defecto 120 s, o 3 ciclos de `POLL_INTERVAL` si eso es más: un ciclo con el PLC
    o InfluxDB caídos dura ~10 s cada uno, así que 120 s deja margen de sobra.
    """
    explicit = environ.get("HEALTH_MAX_AGE_S")
    if explicit:
        return float(explicit)
    try:
        poll = float(environ.get("POLL_INTERVAL", "1.0"))
    except ValueError:
        poll = 1.0
    return max(DEFAULT_MAX_AGE_S, 3 * poll)


def beat(path: str) -> None:
    """Marca que el historian sigue vivo (crea el archivo o actualiza su mtime)."""
    with open(path, "a"):
        os.utime(path, None)


def check(path: str, max_age: float, now: float | None = None) -> tuple[bool, str]:
    now = time.time() if now is None else now
    try:
        age = now - os.path.getmtime(path)
    except OSError:
        return False, f"no existe el latido ({path})"
    if age > max_age:
        return False, f"último latido hace {age:.0f} s (máximo {max_age:.0f} s)"
    return True, f"último latido hace {age:.0f} s"


def main(environ: Mapping[str, str] | None = None) -> int:
    environ = os.environ if environ is None else environ
    healthy, detail = check(heartbeat_path(environ), max_age_s(environ))
    print(("healthy: " if healthy else "unhealthy: ") + detail)
    return 0 if healthy else 1


if __name__ == "__main__":
    sys.exit(main())

"""Lectura de configuración obligatoria desde el entorno.

Vive aparte de `main.py` para poder testearse sin pymodbus ni influxdb-client.
"""
from __future__ import annotations

from collections.abc import Mapping


class ConfigError(Exception):
    """Falta una variable de entorno obligatoria."""


def require_env(environ: Mapping[str, str], name: str) -> str:
    """Devuelve `environ[name]`; falla si falta o está vacía (o solo espacios).

    Una variable vacía es el caso típico de `docker compose` con
    `INFLUX_TOKEN=${INFLUX_TOKEN}` cuando no se definió en el `.env`.
    """
    value = environ.get(name, "").strip()
    if not value:
        raise ConfigError(f"falta la variable de entorno obligatoria {name}")
    return value

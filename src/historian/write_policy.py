"""Política de escritura en InfluxDB: reintentos y corte del ciclo con InfluxDB caído.

Vive aparte de `main.py` para poder testearse con escrituras y `sleep` falsos,
sin influxdb-client ni esperas reales. Es la contraparte de `read_policy.py`.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

ATTEMPTS = 3
DELAY_S = 5.0


def is_transient(ex: Exception) -> bool:
    """¿Vale la pena reintentar después de este error?

    Un error HTTP con `status` 4xx (token inválido 401, request mal formado 400,
    bucket inexistente 404...) no se arregla esperando, salvo 429 (rate limit).
    Un 5xx, o un error de red que no trae `status` (conexión rechazada, timeout),
    sí puede ser transitorio.
    """
    status = getattr(ex, "status", None)
    if isinstance(status, int):
        return status >= 500 or status == 429
    return True


@dataclass(frozen=True)
class WriteResult:
    ok: bool
    # Intentos que fallaron antes de lograr (o no) escribir.
    attempts: int
    error: Exception | None = None
    # Agotó los reintentos con errores transitorios: InfluxDB no responde.
    exhausted: bool = False
    # No se intentó escribir: una escritura anterior de este ciclo ya agotó los reintentos.
    skipped: bool = False


def write_with_retry(
    write: Callable[[], Any],
    *,
    attempts: int = ATTEMPTS,
    delay: float = DELAY_S,
    sleep: Callable[[float], None] = time.sleep,
    on_failure: Callable[[int, Exception], None] | None = None,
) -> WriteResult:
    """Escribe con hasta `attempts` intentos, `delay` segundos entre uno y otro.

    Un error no transitorio (ver `is_transient`) corta de inmediato, sin reintentar.
    No espera después del último intento.
    """
    failed = 0
    while True:
        try:
            write()
            return WriteResult(True, failed)
        except Exception as ex:
            failed += 1
            if on_failure is not None:
                on_failure(failed, ex)
            if not is_transient(ex):
                return WriteResult(False, failed, ex)
            if failed >= attempts:
                return WriteResult(False, failed, ex, exhausted=True)
            sleep(delay)


class WriteGate:
    """Una por ciclo. Si una escritura agota los reintentos, las que faltan se saltan.

    Así un ciclo con InfluxDB caído dura `(attempts - 1) * delay` segundos y no N veces eso.
    """

    def __init__(
        self,
        *,
        attempts: int = ATTEMPTS,
        delay: float = DELAY_S,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._attempts, self._delay, self._sleep = attempts, delay, sleep
        self.down = False
        self.skipped = 0

    def write(
        self,
        write: Callable[[], Any],
        on_failure: Callable[[int, Exception], None] | None = None,
    ) -> WriteResult:
        if self.down:
            self.skipped += 1
            return WriteResult(False, 0, skipped=True)
        result = write_with_retry(
            write,
            attempts=self._attempts,
            delay=self._delay,
            sleep=self._sleep,
            on_failure=on_failure,
        )
        if result.exhausted:
            self.down = True
        return result

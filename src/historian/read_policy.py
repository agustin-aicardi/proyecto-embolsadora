"""Política de lectura de tags: reintentos y corte del ciclo con el PLC caído.

Vive aparte de `main.py` para poder testearse con lecturas y `sleep` falsos,
sin pymodbus ni esperas reales.
"""
from __future__ import annotations

import time
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from typing import Any

ATTEMPTS = 3
DELAY_S = 5.0


@dataclass(frozen=True)
class ReadResult:
    value: Any
    # Intentos que fallaron con excepción antes de obtener (o no) el valor.
    attempts: int
    # Agotó los reintentos por excepción (conexión caída, timeout): el PLC no responde.
    exhausted: bool = False
    # No se intentó leer: un tag anterior de este ciclo ya agotó los reintentos.
    skipped: bool = False


def read_with_retry(
    read: Callable[[Any], Any],
    tag: Any,
    *,
    attempts: int = ATTEMPTS,
    delay: float = DELAY_S,
    sleep: Callable[[float], None] = time.sleep,
    on_failure: Callable[[Any, int, Exception], None] | None = None,
) -> ReadResult:
    """Lee un tag con hasta `attempts` intentos, `delay` segundos entre uno y otro.

    No espera después del último intento: no hay nada que reintentar. Una lectura
    que devuelve `None` (respuesta de error del PLC, no una excepción) NO se
    reintenta ni cuenta como PLC caído: el PLC contestó, el problema es del tag.
    """
    failed = 0
    while failed < attempts:
        try:
            return ReadResult(read(tag), failed)
        except Exception as ex:
            failed += 1
            if on_failure is not None:
                on_failure(tag, failed, ex)
            if failed < attempts:
                sleep(delay)
    return ReadResult(None, failed, exhausted=True)


def read_cycle(
    read: Callable[[Any], Any],
    tags: Iterable[Any],
    *,
    attempts: int = ATTEMPTS,
    delay: float = DELAY_S,
    sleep: Callable[[float], None] = time.sleep,
    on_failure: Callable[[Any, int, Exception], None] | None = None,
) -> Iterator[tuple[Any, ReadResult]]:
    """Lee los tags en orden, de a uno (es un generador: el llamador escribe entre lecturas).

    En cuanto un tag agota sus reintentos por excepción, el PLC se considera caído para
    el resto del ciclo: los tags que faltan se devuelven `skipped` sin intentar leerlos.
    Así el ciclo tarda como máximo `(attempts - 1) * delay` segundos y no N veces eso.
    El ciclo siguiente vuelve a intentar desde el primer tag.
    """
    unreachable = False
    for tag in tags:
        if unreachable:
            yield tag, ReadResult(None, 0, skipped=True)
            continue
        result = read_with_retry(
            read, tag, attempts=attempts, delay=delay, sleep=sleep, on_failure=on_failure
        )
        if result.exhausted:
            unreachable = True
        yield tag, result

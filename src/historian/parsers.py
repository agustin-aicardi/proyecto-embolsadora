"""Pure parsing helpers for Modbus register to value conversions."""
from __future__ import annotations

import struct
from typing import Iterable, List


def int16_from_register(reg: int) -> int:
    """Interpret a single 16-bit register as signed int16."""
    reg = int(reg) & 0xFFFF
    if reg & 0x8000:
        return reg - 0x10000
    return reg


def float32_from_registers(hi: int, lo: int, byteorder: str = "big") -> float:
    """Convert two 16-bit registers into a float32.

    hi and lo are 16-bit register values. For byteorder 'big', hi is the high word.
    For 'little', words are swapped.
    """
    hi = int(hi) & 0xFFFF
    lo = int(lo) & 0xFFFF
    if byteorder == "big":
        raw = (hi << 16) | lo
        # big-endian float
        b = raw.to_bytes(4, "big")
        return struct.unpack(">f", b)[0]
    else:
        # little word order
        raw = (lo << 16) | hi
        b = raw.to_bytes(4, "big")
        return struct.unpack("<f", b)[0]


def bool_from_bits(bits: Iterable[int]) -> bool:
    """Return boolean from bits sequence (first bit is coil 0)."""
    bs: List[int] = list(bits)
    return bool(bs[0]) if bs else False

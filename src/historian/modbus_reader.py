from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .models import TagConfig
from .parsers import int16_from_register, float32_from_registers, bool_from_bits


@dataclass
class ReadResult:
    value: Optional[Any]
    quality: str
    reason: Optional[str] = None


def read_tag(client, tag: TagConfig) -> ReadResult:
    """Read a tag value from Modbus and return value + quality diagnosis."""

    if tag.type == "bool":
        rr = client.read_coils(address=tag.address, count=1, slave=tag.unit)

        if rr is None:
            return ReadResult(value=None, quality="BAD", reason="no_response")

        if hasattr(rr, "isError") and rr.isError():
            return ReadResult(value=None, quality="BAD", reason="modbus_error_response")

        if not hasattr(rr, "bits"):
            return ReadResult(value=None, quality="BAD", reason="missing_bits")

        if not rr.bits:
            return ReadResult(value=None, quality="BAD", reason="empty_bits")

        value = bool_from_bits(rr.bits)

    elif tag.type == "int16":
        rr = client.read_holding_registers(address=tag.address, count=1, slave=tag.unit)

        if rr is None:
            return ReadResult(value=None, quality="BAD", reason="no_response")

        if hasattr(rr, "isError") and rr.isError():
            return ReadResult(value=None, quality="BAD", reason="modbus_error_response")

        if not hasattr(rr, "registers"):
            return ReadResult(value=None, quality="BAD", reason="missing_registers")

        if len(rr.registers) < 1:
            return ReadResult(value=None, quality="BAD", reason="not_enough_registers")

        value = int16_from_register(rr.registers[0])

    elif tag.type == "float32":
        rr = client.read_holding_registers(address=tag.address, count=2, slave=tag.unit)

        if rr is None:
            return ReadResult(value=None, quality="BAD", reason="no_response")

        if hasattr(rr, "isError") and rr.isError():
            return ReadResult(value=None, quality="BAD", reason="modbus_error_response")

        if not hasattr(rr, "registers"):
            return ReadResult(value=None, quality="BAD", reason="missing_registers")

        if len(rr.registers) < 2:
            return ReadResult(value=None, quality="BAD", reason="not_enough_registers")

        value = float32_from_registers(rr.registers[0], rr.registers[1], tag.byteorder)

    else:
        return ReadResult(
            value=None,
            quality="BAD",
            reason=f"unsupported_tag_type:{tag.type}",
        )

    if tag.scale:
        value *= tag.scale

    return ReadResult(value=value, quality="GOOD")
from typing import Optional

from .models import TagConfig
from .parsers import (
    bool_from_bits,
    float32_from_registers,
    int16_from_register,
    int32_from_registers,
)


class UnsupportedTagType(ValueError):
    """El tag declara un tipo que el historian no sabe leer: error de configuración, no del PLC."""


def read_tag(client, tag: TagConfig) -> Optional[float]:
    """Read a tag value from Modbus according to its configuration."""

    if tag.type == "bool":
        rr = client.read_coils(address=tag.address, count=1, slave=tag.unit)
        if not rr or not hasattr(rr, "bits"):
            return None
        value = bool_from_bits(rr.bits)

    elif tag.type == "int16":
        rr = client.read_holding_registers(address=tag.address, count=1, slave=tag.unit)
        if not rr or not hasattr(rr, "registers"):
            return None
        value = int16_from_register(rr.registers[0])

    elif tag.type == "int32":
        rr = client.read_holding_registers(address=tag.address, count=2, slave=tag.unit)
        if not rr or not hasattr(rr, "registers"):
            return None
        value = int32_from_registers(rr.registers[0], rr.registers[1], tag.byteorder)

    elif tag.type == "float32":
        rr = client.read_holding_registers(address=tag.address, count=2, slave=tag.unit)
        if not rr or not hasattr(rr, "registers"):
            return None
        value = float32_from_registers(rr.registers[0], rr.registers[1], tag.byteorder)

    else:
        raise UnsupportedTagType(f"Unsupported tag type: {tag.type}")

    if tag.scale:
        value *= tag.scale

    return value
from typing import Optional

from .models import TagConfig
from .parsers import int16_from_register, float32_from_registers, bool_from_bits


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

    elif tag.type == "float32":
        rr = client.read_holding_registers(address=tag.address, count=2, slave=tag.unit)
        if not rr or not hasattr(rr, "registers"):
            return None
        value = float32_from_registers(rr.registers[0], rr.registers[1], tag.byteorder)

    else:
        raise ValueError(f"Unsupported tag type: {tag.type}")

    if tag.scale:
        value *= tag.scale

    return value
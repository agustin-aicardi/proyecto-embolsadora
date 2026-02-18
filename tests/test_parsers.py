import struct
from src.historian.parsers import int16_from_register, float32_from_registers, bool_from_bits


def regs_from_float(value: float, byteorder: str = "big"):
    # pack float into 4 bytes big-endian, then split into two 16-bit words
    b = struct.pack(">f", value)
    hi = int.from_bytes(b[0:2], "big")
    lo = int.from_bytes(b[2:4], "big")
    if byteorder == "big":
        return hi, lo
    else:
        return lo, hi


def test_float32_big_endian_filled_weight():
    # Use a canonical PLC value for testing
    import math

    val = 123.456
    hi, lo = regs_from_float(val, byteorder="big")
    got = float32_from_registers(hi, lo, byteorder="big")
    assert math.isclose(got, val, rel_tol=1e-6, abs_tol=1e-6)


def test_int16_pack_count_scaling_positive():
    reg = 123
    assert int16_from_register(reg) == 123


def test_int16_pack_count_scaling_negative():
    # register that represents -10 in two's complement
    reg = 0xFFF6
    assert int16_from_register(reg) == -10


def test_bool_from_bits():
    assert bool_from_bits([1, 0, 0]) is True
    assert bool_from_bits([0, 1]) is False

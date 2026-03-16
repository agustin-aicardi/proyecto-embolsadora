"""Simple deterministic Modbus client used for integration testing.

When HISTORY runs with MODBUS_HOST=mock, this client replaces the real
ModbusTcpClient. It returns hard-coded values matching the example
`tags.yaml` configuration so that the CI job can verify correct behaviour
without requiring any hardware.

The mapping is:
  * coil 0 -> True (conveyor_running)
  * register 10 -> 123 (pack_count, signed int16)
  * registers 20/21 -> 123.456 (filled_weight, float32 big-endian)
  * register 30/31 -> temperature (float32 sine wave)
  * register 40/41 -> pressure (float32 ramp)
  * register 50 -> cycle_count (int16 counter)

Additional addresses can be added if you expand `tags.yaml` in the
future; the client simply returns zeroes for any unrecognised address.
"""

import math
import struct
import time


class MockCoilsResponse:
    def __init__(self, bits):
        self.bits = bits


class MockRegistersResponse:
    def __init__(self, registers):
        self.registers = registers


class MockModbusClient:
    """Minimal stand-in for pymodbus.client.ModbusTcpClient."""

    def __init__(self, host=None, port=None):
        self.host = host
        self.port = port
        self.connected = False

    def connect(self):
        # pretend to succeed immediately
        self.connected = True
        return True

    def close(self):
        self.connected = False

    def read_coils(self, address=None, count=None, slave=None):
        # support signature used by our reader helpers: address=..., count=..., slave=...
        # `tags.yaml` uses address 0 for conveyor_running
        if address == 0 and count == 1:
            return MockCoilsResponse([True])
        # default: return False bits
        return MockCoilsResponse([False] * (count or 1))

    @staticmethod
    def _float_to_registers(value: float, byteorder: str = "big") -> tuple[int, int]:
        """Convert a float32 to two 16-bit registers.

        The returned tuple is (hi, lo) for big-endian or (lo, hi) for little-endian.
        """
        raw = struct.unpack(">I", struct.pack(">f", float(value)))[0]
        hi = (raw >> 16) & 0xFFFF
        lo = raw & 0xFFFF
        return (hi, lo) if byteorder == "big" else (lo, hi)

    def _cycle_count(self) -> int:
        """A simple counter that changes over time."""
        # Use seconds since epoch to avoid non-deterministic small deltas
        return int(time.time()) % 0x10000

    def _temperature(self) -> float:
        """Simulate a temperature sensor oscillating over time."""
        # Sine wave around 25.0°C with 5°C amplitude and 10s period.
        t = time.time()
        return 25.0 + 5.0 * math.sin(t * (2 * math.pi / 10))

    def _pressure(self) -> float:
        """Simulate a pressure sensor ramping between 1.0 and 1.5."""
        t = time.time()
        # Ramp up over 20 seconds and wrap.
        phase = (t % 20) / 20
        return 1.0 + 0.5 * phase

    def read_holding_registers(self, address=None, count=None, slave=None):
        # address 10 => signed int16 123
        if address == 10 and count == 1:
            return MockRegistersResponse([123])
        # address 20 => float32 123.456, big-endian split
        if address == 20 and count == 2:
            # filled_weight: float32 123.456 in big-endian format
            # 0x42F6E979 -> registers [0x42F6, 0xE979]
            return MockRegistersResponse([0x42F6, 0xE979])
        # address 30 => temperature (sine wave)
        if address == 30 and count == 2:
            hi, lo = self._float_to_registers(self._temperature())
            return MockRegistersResponse([hi, lo])
        # address 40 => pressure (ramp)
        if address == 40 and count == 2:
            hi, lo = self._float_to_registers(self._pressure())
            return MockRegistersResponse([hi, lo])
        # address 50 => cycle count (int16)
        if address == 50 and count == 1:
            return MockRegistersResponse([self._cycle_count() & 0xFFFF])
        # otherwise return zeros
        return MockRegistersResponse([0] * (count or 1))

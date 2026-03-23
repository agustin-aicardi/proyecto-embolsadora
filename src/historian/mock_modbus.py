"""Simple deterministic Modbus client used for integration testing.

When HISTORY runs with MODBUS_HOST=mock, this client replaces the real
ModbusTcpClient. It returns simulated values matching the example
`tags.yaml` configuration so that the CI job can verify correct behaviour
without requiring any hardware.
"""

import math
import random
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
        self.connected = True
        return True

    def close(self):
        self.connected = False

    def read_coils(self, address=None, count=None, slave=None):
        if address == 0 and count == 1:
            return MockCoilsResponse([self._conveyor_running()])
        return MockCoilsResponse([False] * (count or 1))

    @staticmethod
    def _float_to_registers(value: float, byteorder: str = "big") -> tuple[int, int]:
        raw = struct.unpack(">I", struct.pack(">f", float(value)))[0]
        hi = (raw >> 16) & 0xFFFF
        lo = raw & 0xFFFF
        return (hi, lo) if byteorder == "big" else (lo, hi)

    def _cycle_count(self) -> int:
        return int(time.time()) % 0x10000

    def _pack_count(self) -> int:
        return int(time.time() * 2) % 1000

    def _temperature(self) -> float:
        t = time.time()
        return 25.0 + 4.0 * math.sin(t * (2 * math.pi / 12))

    def _pressure(self) -> float:
        t = time.time()
        base = 1.2 + 0.15 * math.sin(t * (2 * math.pi / 8))
        noise = random.uniform(-0.02, 0.02)
        return base + noise

    def _filled_weight(self) -> float:
        t = time.time()
        base = 49.8 + 0.4 * math.sin(t * (2 * math.pi / 6))
        noise = random.uniform(-0.08, 0.08)
        return base + noise

    def _conveyor_running(self) -> bool:
        phase = int(time.time()) % 15
        return phase < 10

    def read_holding_registers(self, address=None, count=None, slave=None):
        if address == 10 and count == 1:
            return MockRegistersResponse([self._pack_count() & 0xFFFF])

        if address == 20 and count == 2:
            hi, lo = self._float_to_registers(self._filled_weight())
            return MockRegistersResponse([hi, lo])

        if address == 30 and count == 2:
            hi, lo = self._float_to_registers(self._temperature())
            return MockRegistersResponse([hi, lo])

        if address == 40 and count == 2:
            hi, lo = self._float_to_registers(self._pressure())
            return MockRegistersResponse([hi, lo])

        if address == 50 and count == 1:
            return MockRegistersResponse([self._cycle_count() & 0xFFFF])

        return MockRegistersResponse([0] * (count or 1))
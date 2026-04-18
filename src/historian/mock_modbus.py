"""Mock Modbus client for integration testing and thesis demos.

Behavior model:
- One production iteration every 10 seconds
- Batch size: 100 bags, then reset counters
- Deterministic values derived from current time so behavior is reproducible

Address map:
COILS
  0   -> estado
  1   -> paradaEmergencia
  2   -> alimentacionTolva

HOLDING REGISTERS
  10  -> cantidadPesadas (int16)
  20  -> peso / pesoBruto (float32, 2 regs)
  30  -> tiempoCicloActual (float32, 2 regs)
  40  -> consumoElectrico (float32, 2 regs)
  50  -> cantidadLlenadas (int16)

  60  -> Tara (float32, 2 regs)
  70  -> pesoNeto (float32, 2 regs)
  80  -> pesoTotal (float32, 2 regs)

  90  -> tiempoPreparacion (float32, 2 regs)
  100 -> tiempoLlenado (float32, 2 regs)
  110 -> tiempoCiclo (float32, 2 regs)
  120 -> horasProduccion (float32, 2 regs)

  130 -> hora (int16, HHMM)
  140 -> fecha (int16, DDMM)
"""

from __future__ import annotations

import math
import random
import struct
import time
from datetime import datetime


class MockCoilsResponse:
    def __init__(self, bits):
        self.bits = bits


class MockRegistersResponse:
    def __init__(self, registers):
        self.registers = registers


class MockModbusClient:
    """Minimal stand-in for pymodbus.client.ModbusTcpClient."""

    ITERATION_SECONDS = 10
    MAX_BAGS = 100
    TARA_KG = 1.0

    def __init__(self, host=None, port=None):
        self.host = host
        self.port = port
        self.connected = False

    def connect(self):
        self.connected = True
        return True

    def close(self):
        self.connected = False

    @staticmethod
    def _float_to_registers(value: float, byteorder: str = "big") -> tuple[int, int]:
        raw = struct.unpack(">I", struct.pack(">f", float(value)))[0]
        hi = (raw >> 16) & 0xFFFF
        lo = raw & 0xFFFF
        return (hi, lo) if byteorder == "big" else (lo, hi)

    def _now(self) -> float:
        return time.time()

    def _iteration_index_global(self) -> int:
        return int(self._now() // self.ITERATION_SECONDS)

    def _iteration_in_batch_zero_based(self) -> int:
        return self._iteration_index_global() % self.MAX_BAGS

    def _bag_number(self) -> int:
        return self._iteration_in_batch_zero_based() + 1

    def _rng_for_bag(self, bag_idx_zero_based: int) -> random.Random:
        return random.Random(1000 + bag_idx_zero_based)

    def _peso_bruto_for_bag(self, bag_idx_zero_based: int) -> float:
        rng = self._rng_for_bag(bag_idx_zero_based)
        return round(50.0 + rng.uniform(-0.35, 0.35), 3)

    def _peso_bruto(self) -> float:
        return self._peso_bruto_for_bag(self._iteration_in_batch_zero_based())

    def _peso(self) -> float:
        return self._peso_bruto()

    def _tara(self) -> float:
        return self.TARA_KG

    def _peso_neto(self) -> float:
        return round(self._peso_bruto() - self._tara(), 3)

    def _peso_total(self) -> float:
        current_idx = self._iteration_in_batch_zero_based()
        completed_minute_marks = current_idx // 6

        total = 0.0
        for minute_idx in range(completed_minute_marks + 1):
            sample_bag_idx = min(minute_idx * 6, self.MAX_BAGS - 1)
            total += self._peso_bruto_for_bag(sample_bag_idx)

        return round(total, 3)

    def _tiempo_preparacion_for_bag(self, bag_idx_zero_based: int) -> float:
        rng = self._rng_for_bag(bag_idx_zero_based)
        return round(rng.uniform(20.0, 30.0), 3)

    def _tiempo_llenado_for_bag(self, bag_idx_zero_based: int) -> float:
        rng = random.Random(2000 + bag_idx_zero_based)
        return round(rng.uniform(25.0, 30.0), 3)

    def _tiempo_preparacion(self) -> float:
        return self._tiempo_preparacion_for_bag(self._iteration_in_batch_zero_based())

    def _tiempo_llenado(self) -> float:
        return self._tiempo_llenado_for_bag(self._iteration_in_batch_zero_based())

    def _tiempo_ciclo_actual_for_bag(self, bag_idx_zero_based: int) -> float:
        return round(
            self._tiempo_preparacion_for_bag(bag_idx_zero_based)
            + self._tiempo_llenado_for_bag(bag_idx_zero_based),
            3,
        )

    def _tiempo_ciclo_actual(self) -> float:
        return self._tiempo_ciclo_actual_for_bag(self._iteration_in_batch_zero_based())

    def _tiempo_ciclo(self) -> float:
        current_idx = self._iteration_in_batch_zero_based()
        values = [self._tiempo_ciclo_actual_for_bag(i) for i in range(current_idx + 1)]
        return round(sum(values) / len(values), 3)

    def _cantidad_llenadas(self) -> int:
        return self._bag_number()

    def _cantidad_pesadas(self) -> int:
        return self._bag_number()

    def _horas_produccion(self) -> float:
        current_idx = self._iteration_in_batch_zero_based()
        total_seconds = sum(self._tiempo_ciclo_actual_for_bag(i) for i in range(current_idx + 1))
        return round(total_seconds / 3600.0, 4)

    def _consumo_electrico(self) -> float:
        t = self._now()
        base = 1.20 + 0.08 * math.sin(t * (2 * math.pi / 90.0))
        factor = 0.005 * self._tiempo_ciclo_actual()
        return round(base + factor, 4)

    def _estado(self) -> bool:
        return True

    def _parada_emergencia(self) -> bool:
        return int(self._now()) % 420 in range(0, 5)

    def _alimentacion_tolva(self) -> bool:
        return int(self._now()) % 180 in range(0, 12)

    def _hora_hhmm(self) -> int:
        now = datetime.now()
        return now.hour * 100 + now.minute

    def _fecha_ddmm(self) -> int:
        now = datetime.now()
        return now.day * 100 + now.month

    def read_coils(self, address=None, count=None, slave=None):
        if address == 0 and count == 1:
            return MockCoilsResponse([self._estado()])

        if address == 1 and count == 1:
            return MockCoilsResponse([self._parada_emergencia()])

        if address == 2 and count == 1:
            return MockCoilsResponse([self._alimentacion_tolva()])

        return MockCoilsResponse([False] * (count or 1))

    def read_holding_registers(self, address=None, count=None, slave=None):
        if address == 10 and count == 1:
            return MockRegistersResponse([self._cantidad_pesadas() & 0xFFFF])

        if address == 20 and count == 2:
            hi, lo = self._float_to_registers(self._peso())
            return MockRegistersResponse([hi, lo])

        if address == 30 and count == 2:
            hi, lo = self._float_to_registers(self._tiempo_ciclo_actual())
            return MockRegistersResponse([hi, lo])

        if address == 40 and count == 2:
            hi, lo = self._float_to_registers(self._consumo_electrico())
            return MockRegistersResponse([hi, lo])

        if address == 50 and count == 1:
            return MockRegistersResponse([self._cantidad_llenadas() & 0xFFFF])

        if address == 60 and count == 2:
            hi, lo = self._float_to_registers(self._tara())
            return MockRegistersResponse([hi, lo])

        if address == 70 and count == 2:
            hi, lo = self._float_to_registers(self._peso_neto())
            return MockRegistersResponse([hi, lo])

        if address == 80 and count == 2:
            hi, lo = self._float_to_registers(self._peso_total())
            return MockRegistersResponse([hi, lo])

        if address == 90 and count == 2:
            hi, lo = self._float_to_registers(self._tiempo_preparacion())
            return MockRegistersResponse([hi, lo])

        if address == 100 and count == 2:
            hi, lo = self._float_to_registers(self._tiempo_llenado())
            return MockRegistersResponse([hi, lo])

        if address == 110 and count == 2:
            hi, lo = self._float_to_registers(self._tiempo_ciclo())
            return MockRegistersResponse([hi, lo])

        if address == 120 and count == 2:
            hi, lo = self._float_to_registers(self._horas_produccion())
            return MockRegistersResponse([hi, lo])

        if address == 130 and count == 1:
            return MockRegistersResponse([self._hora_hhmm() & 0xFFFF])

        if address == 140 and count == 1:
            return MockRegistersResponse([self._fecha_ddmm() & 0xFFFF])

        return MockRegistersResponse([0] * (count or 1))
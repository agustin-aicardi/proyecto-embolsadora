"""Simple deterministic Modbus client used for integration testing.

When HISTORY runs with MODBUS_HOST=mock, this client replaces the real
ModbusTcpClient. It returns hard-coded values matching the example
`tags.yaml` configuration so that the CI job can verify correct behaviour
without requiring any hardware.

The mapping is:
  * coil 0 -> True (conveyor_running)
  * register 10 -> 123 (pack_count, signed int16)
  * registers 20/21 -> 123.456 (filled_weight, float32 big-endian)

Additional addresses can be added if you expand `tags.yaml` in the
future; the client simply returns zeroes for any unrecognised address.
"""


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

    def read_holding_registers(self, address=None, count=None, slave=None):
        # address 10 => signed int16 123
        if address == 10 and count == 1:
            return MockRegistersResponse([123])
        # address 20 => float32 123.456, big-endian split
        if address == 20 and count == 2:
            # hex 0x3F5C28F0 -> registers [0x3F5C, 0x28F0]
            return MockRegistersResponse([0x3F5C, 0x28F0])
        # otherwise return zeros
        return MockRegistersResponse([0] * (count or 1))

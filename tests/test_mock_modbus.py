"""Unit tests for the mock Modbus client."""

from src.historian.mock_modbus import MockModbusClient


def test_mock_connect():
    client = MockModbusClient()
    assert client.connect() is True


def test_mock_coil():
    client = MockModbusClient()
    # conveyor_running coil should be True
    resp = client.read_coils(address=0, count=1, slave=1)
    assert resp.bits == [True]


def test_mock_registers():
    client = MockModbusClient()
    # pack_count at address 10
    resp = client.read_holding_registers(address=10, count=1, slave=1)
    assert resp.registers == [123]

    # filled_weight at address 20 returns two registers
    resp2 = client.read_holding_registers(address=20, count=2, slave=1)
    assert resp2.registers == [0x3F5C, 0x28F0]  # big-endian float

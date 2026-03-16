"""Unit tests for the mock Modbus client."""

from unittest.mock import patch

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
    assert resp2.registers == [0x42F6, 0xE979]  # big-endian float for 123.456

    # When time is fixed, the dynamic registers should also be deterministic
    with patch("time.time", return_value=0.0):
        # temperature at t=0 should be 25.0 -> 0x41C80000
        resp3 = client.read_holding_registers(address=30, count=2, slave=1)
        assert resp3.registers == [0x41C8, 0x0000]

        # pressure at t=0 should be 1.0 -> 0x3F800000
        resp4 = client.read_holding_registers(address=40, count=2, slave=1)
        assert resp4.registers == [0x3F80, 0x0000]

        # cycle_count at t=0 should be 0
        resp5 = client.read_holding_registers(address=50, count=1, slave=1)
        assert resp5.registers == [0]

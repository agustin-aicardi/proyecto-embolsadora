"""Unit tests for the mock Modbus client."""

from unittest.mock import patch

from src.historian.mock_modbus import MockModbusClient


def test_mock_connect():
    client = MockModbusClient()
    assert client.connect() is True


def test_mock_coil():
    client = MockModbusClient()

    with patch("time.time", return_value=100.0):
        resp = client.read_coils(address=0, count=1, slave=1)
        assert resp.bits == [True]

        resp2 = client.read_coils(address=1, count=1, slave=1)
        assert isinstance(resp2.bits[0], bool)

        resp3 = client.read_coils(address=2, count=1, slave=1)
        assert isinstance(resp3.bits[0], bool)


def test_mock_registers():
    client = MockModbusClient()

    with patch("time.time", return_value=220.0):
        # cantidadPesadas at address 10
        resp = client.read_holding_registers(address=10, count=1, slave=1)
        assert hasattr(resp, "registers")
        assert len(resp.registers) == 1
        assert isinstance(resp.registers[0], int)
        assert 1 <= resp.registers[0] <= 100

        # peso / pesoBruto at address 20 returns two registers
        resp2 = client.read_holding_registers(address=20, count=2, slave=1)
        assert hasattr(resp2, "registers")
        assert len(resp2.registers) == 2
        assert all(isinstance(r, int) for r in resp2.registers)

        # tiempoCicloActual at address 30
        resp3 = client.read_holding_registers(address=30, count=2, slave=1)
        assert len(resp3.registers) == 2

        # consumoElectrico at address 40
        resp4 = client.read_holding_registers(address=40, count=2, slave=1)
        assert len(resp4.registers) == 2

        # cantidadLlenadas at address 50
        resp5 = client.read_holding_registers(address=50, count=1, slave=1)
        assert len(resp5.registers) == 1
        assert isinstance(resp5.registers[0], int)
        assert 1 <= resp5.registers[0] <= 100

        # Tara at address 60
        resp6 = client.read_holding_registers(address=60, count=2, slave=1)
        assert len(resp6.registers) == 2

        # pesoNeto at address 70
        resp7 = client.read_holding_registers(address=70, count=2, slave=1)
        assert len(resp7.registers) == 2

        # pesoTotal at address 80
        resp8 = client.read_holding_registers(address=80, count=2, slave=1)
        assert len(resp8.registers) == 2

        # tiempoPreparacion at address 90
        resp9 = client.read_holding_registers(address=90, count=2, slave=1)
        assert len(resp9.registers) == 2

        # tiempoLlenado at address 100
        resp10 = client.read_holding_registers(address=100, count=2, slave=1)
        assert len(resp10.registers) == 2

        # tiempoCiclo at address 110
        resp11 = client.read_holding_registers(address=110, count=2, slave=1)
        assert len(resp11.registers) == 2

        # horasProduccion at address 120
        resp12 = client.read_holding_registers(address=120, count=2, slave=1)
        assert len(resp12.registers) == 2

        # hora at address 130
        resp13 = client.read_holding_registers(address=130, count=1, slave=1)
        assert len(resp13.registers) == 1
        assert isinstance(resp13.registers[0], int)

        # fecha at address 140
        resp14 = client.read_holding_registers(address=140, count=1, slave=1)
        assert len(resp14.registers) == 1
        assert isinstance(resp14.registers[0], int)


def test_mock_is_deterministic_for_fixed_time():
    client = MockModbusClient()

    with patch("time.time", return_value=220.0):
        r1 = client.read_holding_registers(address=20, count=2, slave=1).registers
        r2 = client.read_holding_registers(address=20, count=2, slave=1).registers
        assert r1 == r2

        c1 = client.read_holding_registers(address=10, count=1, slave=1).registers
        c2 = client.read_holding_registers(address=10, count=1, slave=1).registers
        assert c1 == c2

        b1 = client.read_coils(address=2, count=1, slave=1).bits
        b2 = client.read_coils(address=2, count=1, slave=1).bits
        assert b1 == b2
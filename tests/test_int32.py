from src.historian.models import TagConfig
from src.historian.modbus_reader import UnsupportedTagType, read_tag
from src.historian.parsers import int32_from_registers


def split(value: int, byteorder: str = "big"):
    """Parte un int32 en dos registros como los entregaría un PLC."""
    raw = value & 0xFFFFFFFF
    hi, lo = (raw >> 16) & 0xFFFF, raw & 0xFFFF
    return (hi, lo) if byteorder == "big" else (lo, hi)


def test_int32_positivo_big_endian():
    assert int32_from_registers(0x0001, 0x86A0, "big") == 100_000


def test_int32_negativo_big_endian():
    assert int32_from_registers(*split(-1)) == -1
    assert int32_from_registers(*split(-100_000)) == -100_000


def test_int32_limites():
    assert int32_from_registers(0x7FFF, 0xFFFF, "big") == 2_147_483_647
    assert int32_from_registers(0x8000, 0x0000, "big") == -2_147_483_648
    assert int32_from_registers(0, 0, "big") == 0


def test_int32_little_invierte_el_orden_de_las_palabras():
    for v in (0, 1, 100_000, -1, -100_000, 2_147_483_647, -2_147_483_648):
        assert int32_from_registers(*split(v, "little"), "little") == v


def test_el_mismo_par_de_registros_da_distinto_valor_segun_byteorder():
    assert int32_from_registers(0x0001, 0x0000, "big") == 65_536
    assert int32_from_registers(0x0001, 0x0000, "little") == 1


class _Regs:
    def __init__(self, registers):
        self.registers = registers


class _Client:
    """Cliente falso: devuelve los registros dados y recuerda qué se le pidió."""

    def __init__(self, registers):
        self.registers, self.calls = registers, []

    def read_holding_registers(self, address=None, count=None, slave=None):
        self.calls.append((address, count, slave))
        return _Regs(self.registers)


def _tag(**kw):
    base = dict(name="contador", type="int32", address=100, unit=1, byteorder="big", scale=None)
    base.update(kw)
    return TagConfig(**base)


def test_read_tag_int32_lee_dos_registros():
    client = _Client(list(split(123_456)))
    assert read_tag(client, _tag()) == 123_456
    assert client.calls == [(100, 2, 1)]


def test_read_tag_int32_respeta_byteorder_y_signo():
    client = _Client(list(split(-42, "little")))
    assert read_tag(client, _tag(byteorder="little")) == -42


def test_read_tag_int32_aplica_scale():
    client = _Client(list(split(1500)))
    assert read_tag(client, _tag(scale=0.1)) == 150.0


def test_read_tag_int32_respuesta_de_error_devuelve_none():
    class Err:
        pass

    class C:
        def read_holding_registers(self, **k):
            return Err()

    assert read_tag(C(), _tag()) is None


def test_un_tipo_desconocido_sigue_siendo_un_error_de_configuracion():
    try:
        read_tag(_Client([0, 0]), _tag(type="int64"))
    except UnsupportedTagType:
        return
    raise AssertionError("debió lanzar UnsupportedTagType")

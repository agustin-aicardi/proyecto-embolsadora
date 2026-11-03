from src.historian.config import ConfigError, require_env


def _raises(env, name):
    try:
        require_env(env, name)
    except ConfigError as ex:
        return str(ex)
    return None


def test_require_env_devuelve_el_valor():
    assert require_env({"INFLUX_TOKEN": "abc"}, "INFLUX_TOKEN") == "abc"


def test_require_env_falla_si_la_variable_no_existe():
    msg = _raises({}, "INFLUX_TOKEN")
    assert msg is not None and "INFLUX_TOKEN" in msg


def test_require_env_falla_si_esta_vacia():
    # docker compose con INFLUX_TOKEN=${INFLUX_TOKEN} sin definir entrega ""
    assert _raises({"INFLUX_TOKEN": ""}, "INFLUX_TOKEN") is not None


def test_require_env_falla_si_son_solo_espacios():
    assert _raises({"INFLUX_TOKEN": "   "}, "INFLUX_TOKEN") is not None


def test_require_env_no_acepta_el_viejo_valor_por_defecto_implicito():
    # Antes el código usaba "my-token" si faltaba; ahora no hay valor por defecto.
    assert _raises({"OTRA": "x"}, "INFLUX_TOKEN") is not None

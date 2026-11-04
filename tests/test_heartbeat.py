import os
import tempfile

from src.historian.heartbeat import beat, check, heartbeat_path, main, max_age_s


def _tmp():
    d = tempfile.mkdtemp()
    return os.path.join(d, "alive")


def test_sin_archivo_no_esta_sano():
    ok, detail = check(_tmp(), 120)
    assert not ok and "no existe" in detail


def test_latido_reciente_esta_sano():
    p = _tmp()
    beat(p)
    assert check(p, 120)[0]


def test_latido_viejo_no_esta_sano():
    p = _tmp()
    beat(p)
    futuro = os.path.getmtime(p) + 500       # "ahora" 500 s después del último latido
    ok, detail = check(p, 120, now=futuro)
    assert not ok and "500" in detail


def test_beat_actualiza_el_mtime():
    p = _tmp()
    beat(p)
    os.utime(p, (1000, 1000))                # latido de 1970
    assert not check(p, 120)[0]
    beat(p)
    assert check(p, 120)[0]


def test_max_age_por_defecto_y_por_poll_interval():
    assert max_age_s({}) == 120.0
    assert max_age_s({"POLL_INTERVAL": "1"}) == 120.0
    assert max_age_s({"POLL_INTERVAL": "300"}) == 900.0     # 3 ciclos si es más que 120
    assert max_age_s({"POLL_INTERVAL": "basura"}) == 120.0
    assert max_age_s({"HEALTH_MAX_AGE_S": "30", "POLL_INTERVAL": "300"}) == 30.0


def test_ruta_configurable_y_por_defecto_en_el_tmp_del_sistema():
    assert heartbeat_path({"HEARTBEAT_FILE": "/x/y"}) == "/x/y"
    assert heartbeat_path({}).endswith("historian.alive")


def test_main_devuelve_codigo_de_salida():
    p = _tmp()
    assert main({"HEARTBEAT_FILE": p}) == 1          # sin latido
    beat(p)
    assert main({"HEARTBEAT_FILE": p}) == 0
    assert main({"HEARTBEAT_FILE": p, "HEALTH_MAX_AGE_S": "-1"}) == 1

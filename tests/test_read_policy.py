from src.historian.modbus_reader import UnsupportedTagType
from src.historian.read_policy import read_cycle, read_with_retry


class Boom(Exception):
    pass


def _scripted(outcomes):
    """Devuelve un `read` que consume `outcomes` (valor o excepción) en orden."""
    it = iter(outcomes)

    def read(tag):
        o = next(it)
        if isinstance(o, Exception):
            raise o
        return o

    return read


def test_lectura_ok_al_primer_intento_no_espera():
    sleeps = []
    res = read_with_retry(_scripted([42.0]), "t", sleep=sleeps.append)
    assert (res.value, res.attempts, res.exhausted, res.skipped) == (42.0, 0, False, False)
    assert sleeps == []


def test_se_recupera_tras_dos_fallos_y_espera_5s_entre_intentos():
    sleeps, fails = [], []
    res = read_with_retry(
        _scripted([Boom(), Boom(), 7.0]), "t",
        sleep=sleeps.append, on_failure=lambda tag, n, ex: fails.append(n),
    )
    assert res.value == 7.0 and res.attempts == 2 and not res.exhausted
    assert sleeps == [5.0, 5.0]
    assert fails == [1, 2]


def test_agota_los_reintentos_y_no_espera_despues_del_ultimo():
    sleeps = []
    res = read_with_retry(_scripted([Boom(), Boom(), Boom()]), "t", sleep=sleeps.append)
    assert res.value is None and res.attempts == 3 and res.exhausted
    # 3 intentos => 2 esperas entre ellos (antes eran 3: una de 5 s de más al final)
    assert sleeps == [5.0, 5.0]


def test_respuesta_de_error_del_plc_no_se_reintenta_ni_cuenta_como_caido():
    sleeps = []
    res = read_with_retry(_scripted([None]), "t", sleep=sleeps.append)
    assert res.value is None and res.attempts == 0 and not res.exhausted
    assert sleeps == []


def test_con_el_plc_caido_el_ciclo_se_corta_en_el_primer_tag():
    leidos, sleeps = [], []

    def read(tag):
        leidos.append(tag)
        raise Boom()

    out = list(read_cycle(read, [f"t{i}" for i in range(18)], sleep=sleeps.append))
    assert len(out) == 18
    assert out[0][1].exhausted and not out[0][1].skipped
    assert all(r.skipped and r.value is None for _, r in out[1:])
    assert leidos == ["t0", "t0", "t0"]          # solo el primer tag se intentó
    assert sum(sleeps) == 10.0                    # antes: 18 tags x 15 s = 270 s


def test_un_tag_con_respuesta_de_error_no_corta_el_ciclo():
    read = _scripted([1.0, None, 3.0])
    out = list(read_cycle(read, ["a", "b", "c"], sleep=lambda s: None))
    assert [r.value for _, r in out] == [1.0, None, 3.0]
    assert not any(r.skipped for _, r in out)


def test_un_fallo_que_se_recupera_no_corta_el_ciclo():
    read = _scripted([Boom(), 1.0, 2.0])
    out = list(read_cycle(read, ["a", "b"], sleep=lambda s: None))
    assert [r.value for _, r in out] == [1.0, 2.0]
    assert out[0][1].attempts == 1


def test_el_ciclo_siguiente_vuelve_a_intentar_desde_el_primer_tag():
    # Ciclo 1: PLC caído. Ciclo 2: ya responde. El estado "caído" no se arrastra.
    ciclo1 = list(read_cycle(_scripted([Boom(), Boom(), Boom()]), ["a", "b"], sleep=lambda s: None))
    assert ciclo1[1][1].skipped
    ciclo2 = list(read_cycle(_scripted([1.0, 2.0]), ["a", "b"], sleep=lambda s: None))
    assert [r.value for _, r in ciclo2] == [1.0, 2.0]


def test_es_perezoso_el_llamador_puede_escribir_entre_lecturas():
    leidos = []

    def read(tag):
        leidos.append(tag)
        return 1.0

    gen = read_cycle(read, ["a", "b"], sleep=lambda s: None)
    next(gen)
    assert leidos == ["a"]  # "b" todavía no se leyó


def test_tipo_de_tag_no_soportado_no_se_reintenta_ni_cuenta_como_plc_caido():
    sleeps = []
    res = read_with_retry(_scripted([UnsupportedTagType("int64")]), "t", sleep=sleeps.append)
    assert res.value is None and not res.exhausted and not res.skipped
    assert sleeps == []


def test_un_tag_mal_configurado_no_tira_abajo_a_los_demas():
    read = _scripted([UnsupportedTagType("int64"), 2.0, 3.0])
    out = list(read_cycle(read, ["mal", "b", "c"], sleep=lambda s: None))
    assert [r.value for _, r in out] == [None, 2.0, 3.0]
    assert not any(r.skipped for _, r in out)

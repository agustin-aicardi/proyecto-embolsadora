from src.historian.write_policy import WriteGate, is_transient, write_with_retry


class Boom(Exception):
    pass


class Http(Exception):
    def __init__(self, status):
        super().__init__(f"HTTP {status}")
        self.status = status


def _scripted(outcomes):
    it = iter(outcomes)

    def write():
        o = next(it)
        if isinstance(o, Exception):
            raise o

    return write


def test_clasifica_errores():
    assert is_transient(Boom())          # error de red: sin status
    assert is_transient(Http(503))
    assert is_transient(Http(429))
    assert not is_transient(Http(401))   # token inválido
    assert not is_transient(Http(400))
    assert not is_transient(Http(404))


def test_escritura_ok_no_espera():
    sleeps = []
    res = write_with_retry(_scripted([None]), sleep=sleeps.append)
    assert res.ok and res.attempts == 0 and sleeps == []


def test_se_recupera_tras_un_fallo_de_red_y_espera_5s():
    sleeps, fails = [], []
    res = write_with_retry(
        _scripted([Boom(), None]), sleep=sleeps.append,
        on_failure=lambda n, ex: fails.append(n),
    )
    assert res.ok and res.attempts == 1
    assert sleeps == [5.0] and fails == [1]


def test_agota_los_reintentos_con_5xx_y_no_espera_despues_del_ultimo():
    sleeps = []
    res = write_with_retry(_scripted([Http(503)] * 3), sleep=sleeps.append)
    assert not res.ok and res.exhausted and res.attempts == 3
    assert isinstance(res.error, Http)
    assert sleeps == [5.0, 5.0]


def test_error_4xx_no_se_reintenta():
    sleeps = []
    res = write_with_retry(_scripted([Http(401)]), sleep=sleeps.append)
    assert not res.ok and not res.exhausted and res.attempts == 1
    assert sleeps == []


def test_gate_corta_el_ciclo_cuando_influx_esta_caido():
    llamadas, sleeps = [], []
    gate = WriteGate(sleep=sleeps.append)

    def w():
        llamadas.append(1)
        raise Boom()

    results = [gate.write(w) for _ in range(18)]
    assert results[0].exhausted and not results[0].skipped
    assert all(r.skipped for r in results[1:])
    assert len(llamadas) == 3                 # solo la primera escritura se intentó
    assert sum(sleeps) == 10.0                # antes de reintentar: 0; con 18 tags: 18 x 10 s
    assert gate.down and gate.skipped == 17


def test_gate_un_error_4xx_no_corta_el_ciclo():
    gate = WriteGate(sleep=lambda s: None)
    r1 = gate.write(_scripted([Http(400)]))
    r2 = gate.write(_scripted([None]))
    assert not r1.ok and not r1.exhausted
    assert r2.ok and not gate.down


def test_una_gate_nueva_por_ciclo_vuelve_a_intentar():
    g1 = WriteGate(sleep=lambda s: None)
    g1.write(_scripted([Boom()] * 3))
    assert g1.down
    g2 = WriteGate(sleep=lambda s: None)
    assert g2.write(_scripted([None])).ok

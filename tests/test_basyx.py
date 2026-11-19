import base64
import os
import tempfile
import threading
import urllib.error
import xml.etree.ElementTree as ET

from src.historian import basyx_updater as bu
from src.historian.aas_updater import AASUpdater
from src.historian.basyx_updater import BaSyxUpdater
from src.historian.basyx_worker import BaSyxWorker

SUBMODEL_ID = "https://example.com/ids/sm/operativos"

XML = f"""<?xml version="1.0" encoding="utf-8"?>
<environment xmlns="https://admin-shell.io/aas/3/0">
  <submodels>
    <submodel>
      <idShort>Operativos</idShort>
      <id>{SUBMODEL_ID}</id>
    </submodel>
  </submodels>
</environment>
"""

MAPPING = {
    "mappings": [
        {"name": "peso", "aas": {"submodel": "Operativos", "collection": "Pesada", "property": "peso"}},
        {"name": "modo", "aas": {"submodel": "Operativos", "property": "modo"}},
        {"name": "off", "enabled": False, "aas": {"submodel": "Operativos", "property": "off"}},
        {"name": "huerfano", "aas": {"submodel": "NoExiste", "property": "x"}},
    ]
}


def _updater(tmp=None):
    d = tmp or tempfile.mkdtemp()
    p = os.path.join(d, "aas.xml")
    with open(p, "w", encoding="utf-8") as f:
        f.write(XML)
    u = BaSyxUpdater("http://basyx:8081/", p, MAPPING)
    calls = []
    u._patch_property_value = lambda **kw: calls.append(kw)
    return u, calls


def test_lee_los_ids_de_submodelo_y_normaliza_la_url():
    u, _ = _updater()
    assert u.submodel_ids == {"Operativos": SUBMODEL_ID}
    assert u.base_url == "http://basyx:8081"


def test_identificador_base64url_sin_padding():
    enc = BaSyxUpdater._encode_basyx_identifier(SUBMODEL_ID)
    assert "=" not in enc and "+" not in enc and "/" not in enc
    pad = "=" * (-len(enc) % 4)
    assert base64.urlsafe_b64decode(enc + pad).decode() == SUBMODEL_ID


def test_valores_a_texto_aas():
    assert BaSyxUpdater._to_aas_string(True) == "true"
    assert BaSyxUpdater._to_aas_string(False) == "false"
    assert BaSyxUpdater._to_aas_string(1.5) == "1.5"


def test_idshort_path_con_y_sin_coleccion():
    assert BaSyxUpdater._build_idshort_path({"collection": "Pesada", "property": "peso"}) == "Pesada.peso"
    assert BaSyxUpdater._build_idshort_path({"property": "modo"}) == "modo"


def test_envia_solo_lo_mapeado_y_habilitado():
    u, calls = _updater()
    updated = u.update_from_dict({"peso": 1.0, "modo": 2, "off": 9, "otro": 3})
    assert updated == ["peso", "modo"]
    assert [c["idshort_path"] for c in calls] == ["Pesada.peso", "modo"]
    assert all(c["submodel_identifier"] == SUBMODEL_ID for c in calls)


def test_no_reenvia_valores_sin_cambio_y_tolera_ruido_de_float():
    u, calls = _updater()
    u.update_from_dict({"peso": 1.0})
    assert u.update_from_dict({"peso": 1.0004}) == []   # dentro de la tolerancia
    assert u.update_from_dict({"peso": 1.01}) == ["peso"]
    assert len(calls) == 2


def test_bool_se_compara_por_igualdad():
    u, _ = _updater()
    u.update_from_dict({"modo": True})
    assert u.update_from_dict({"modo": True}) == []
    assert u.update_from_dict({"modo": False}) == ["modo"]


def test_submodelo_inexistente_levanta_keyerror():
    u, _ = _updater()
    try:
        u.update_from_dict({"huerfano": 1})
    except KeyError:
        return
    raise AssertionError("debía levantar KeyError")


def test_un_fallo_no_marca_el_valor_como_enviado():
    u, _ = _updater()

    def boom(**kw):
        raise OSError("basyx caído")

    u._patch_property_value = boom
    try:
        u.update_from_dict({"peso": 1.0})
    except OSError:
        pass
    assert "peso" not in u.last_sent_values   # se reintenta en el próximo ciclo


class _Resp:
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_patch_arma_url_metodo_y_cuerpo():
    u, _ = _updater()
    del u._patch_property_value          # volver al método real
    seen = {}
    real = bu.urllib.request.urlopen

    def fake(req, timeout):
        seen.update(url=req.full_url, method=req.get_method(), body=req.data, timeout=timeout)
        return _Resp(204)

    bu.urllib.request.urlopen = fake
    try:
        u._patch_property_value(SUBMODEL_ID, "Pesada.peso", 1.5)
    finally:
        bu.urllib.request.urlopen = real
    enc = BaSyxUpdater._encode_basyx_identifier(SUBMODEL_ID)
    assert seen["url"] == f"http://basyx:8081/submodels/{enc}/submodel-elements/Pesada.peso/$value"
    assert seen["method"] == "PATCH"
    assert seen["body"] == b'"1.5"'
    assert seen["timeout"] == 5


def test_patch_con_status_inesperado_falla():
    u, _ = _updater()
    del u._patch_property_value
    real = bu.urllib.request.urlopen
    bu.urllib.request.urlopen = lambda req, timeout: _Resp(500)
    try:
        u._patch_property_value(SUBMODEL_ID, "modo", 1)
    except RuntimeError:
        return
    finally:
        bu.urllib.request.urlopen = real
    raise AssertionError("debía levantar RuntimeError")


# ---- BaSyxWorker -----------------------------------------------------------

class _FakeUpdater:
    def __init__(self, fail=False):
        self.batches = []
        self.fail = fail
        self.done = threading.Event()
        self.entered = threading.Event()
        self.gate = threading.Event()
        self.gate.set()

    def update_from_dict(self, values):
        self.entered.set()
        self.gate.wait(5)
        self.batches.append(dict(values))
        self.done.set()
        if self.fail:
            raise urllib.error.URLError("caído")


def test_worker_entrega_los_valores():
    up = _FakeUpdater()
    w = BaSyxWorker(up)
    w.start()
    w.submit({"peso": 1})
    assert up.done.wait(5)
    w.stop()
    assert up.batches == [{"peso": 1}]


def test_worker_fusiona_lo_pendiente_y_conserva_lo_mas_reciente():
    up = _FakeUpdater()
    up.gate.clear()                      # bloquea al worker dentro del primer envío
    w = BaSyxWorker(up)
    w.start()
    w.submit({"peso": 1})
    assert up.entered.wait(5)            # el worker ya está dentro del primer envío
    w.submit({"peso": 2, "modo": 1})     # mientras el worker está ocupado...
    w.submit({"peso": 3})                # ...se fusionan, gana el último
    up.gate.set()
    assert _wait(lambda: len(up.batches) == 2)
    w.stop()
    assert up.batches[-1] == {"peso": 3, "modo": 1}


def test_worker_informa_errores_y_sigue_vivo():
    up = _FakeUpdater(fail=True)
    errors = []
    w = BaSyxWorker(up, on_error=errors.append)
    w.start()
    w.submit({"peso": 1})
    assert _wait(lambda: len(errors) == 1)
    w.submit({"peso": 2})
    assert _wait(lambda: len(errors) == 2)
    w.stop()


def test_worker_sobrevive_a_un_on_error_que_falla():
    up = _FakeUpdater(fail=True)

    def bad(ex):
        raise ValueError("log roto")

    w = BaSyxWorker(up, on_error=bad)
    w.start()
    w.submit({"a": 1})
    w.submit({"a": 2})
    assert _wait(lambda: len(up.batches) >= 1)
    w.submit({"a": 3})
    assert _wait(lambda: len(up.batches) >= 2)
    w.stop()


def test_worker_detenido_ignora_envios():
    up = _FakeUpdater()
    w = BaSyxWorker(up)
    w.start()
    w.stop()
    w.submit({"peso": 1})
    w._thread.join(5)
    assert not w._thread.is_alive()
    assert up.batches == []


def _wait(cond, timeout=5.0):
    import time

    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.01)
    return False


# ---- AASUpdater.save (escritura atómica) -----------------------------------

def _aas(tmp):
    xml = os.path.join(tmp, "in.xml")
    with open(xml, "w", encoding="utf-8") as f:
        f.write(XML)
    u = AASUpdater.__new__(AASUpdater)     # save() solo usa self.tree
    u.tree = ET.parse(xml)
    return u


def test_save_escribe_y_no_deja_temporales():
    tmp = tempfile.mkdtemp()
    out = os.path.join(tmp, "runtime", "out.xml")
    _aas(tmp).save(out)
    assert ET.parse(out).getroot().tag.endswith("environment")
    assert os.listdir(os.path.dirname(out)) == ["out.xml"]


def test_save_fallido_conserva_el_archivo_anterior_y_limpia():
    tmp = tempfile.mkdtemp()
    out = os.path.join(tmp, "out.xml")
    with open(out, "w", encoding="utf-8") as f:
        f.write("ANTERIOR")
    u = _aas(tmp)

    class Boom:
        def write(self, *a, **k):
            raise OSError("disco lleno")

    u.tree = Boom()
    try:
        u.save(out)
    except OSError:
        pass
    assert open(out, encoding="utf-8").read() == "ANTERIOR"
    assert sorted(os.listdir(tmp)) == ["in.xml", "out.xml"]

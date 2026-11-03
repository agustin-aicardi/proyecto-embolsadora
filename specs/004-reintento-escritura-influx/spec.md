---
id: "004"
title: Reintento de escritura en InfluxDB
tier: change
status: in-progress
owner: Federico Degiovanni
date: 2026-11-02
repos: [proyecto-embolsadora]
origin: nuevo
issues: []
prs: []
adrs: []
veredicto:
reconciliado:
divergencia:
supersedes:
superseded_by:
last_reviewed: 2026-11-02
---

# 004 — Reintento de escritura en InfluxDB

## Contexto y problema

La constitution (principio V) exige que toda operación de red, **Modbus TCP o escritura en InfluxDB**, tenga reintentos con intervalo de 5 s. El código reintenta solo la lectura Modbus. Si una escritura en InfluxDB falla (un corte de red, un reinicio de InfluxDB, un 503), el punto de ese ciclo se descarta sin reintentar: queda marcado `INFLUX_WRITE_FAILED` y el historial tiene un agujero que nadie vuelve a llenar.

Es el desvío «Sin reintento de escritura en InfluxDB» de la [spec 001](../001-historian-semantico/spec.md). Su contraparte de lectura está en la [spec 003](../003-ciclo-acotado-plc-caido/spec.md).

## Alcance

Entra: reintentar la escritura ante errores transitorios y acotar el ciclo cuando InfluxDB no responde. No entra: guardar en memoria o en disco los puntos que no se pudieron escribir para enviarlos después (ver «Riesgos»), el healthcheck, ni el tipo `int32`.

## Requisitos

- **RF-001** `origen: original` — Ante un error transitorio al escribir en InfluxDB (error de red sin código HTTP, HTTP 5xx o 429), el historian DEBE reintentar hasta 3 veces con 5 s entre intentos, conservando el timestamp original del punto.
- **RF-002** `origen: original` — Ante un error HTTP 4xx distinto de 429 (token inválido 401, request mal formado 400, bucket inexistente 404...), NO DEBE reintentar: esperar no lo arregla.
- **RF-003** `origen: original` — NO DEBE esperar después del último intento fallido.
- **RF-004** `origen: original` — Cuando una escritura agota los reintentos por errores transitorios, InfluxDB se considera caído **para el resto de ese ciclo**: las escrituras restantes NO DEBEN intentarse; sus tags DEBEN quedar `INFLUX_WRITE_FAILED` con `reason: influx_unreachable`, y el ciclo DEBE registrar `cycle.writes_skipped`.
- **RF-005** `origen: original` — El ciclo siguiente DEBE volver a intentar desde la primera escritura; el estado «caído» no se arrastra entre ciclos.
- **RF-006** `origen: original` — Con InfluxDB funcionando, el comportamiento y lo escrito NO DEBEN cambiar.

## Criterios de éxito

- **CE-001** — `tests/test_write_policy.py` (8 tests) pasa con `python3 run_tests.py`. **Cumplido.**
- **CE-002** — Con InfluxDB caído (error de red), un ciclo de 18 tags dura 10 s: 3 intentos en la primera escritura y las otras 17 saltadas. **Cumplido** (corrida de `main()` con un escritor falso).
- **CE-003** — Con un 401, la escritura falla de inmediato (1 intento, sin esperas). **Cumplido** (misma corrida).
- **CE-004** — Con el escritor funcionando, se escriben los 18 tags como antes. **Cumplido.**
- **CE-005** — Contra un InfluxDB real que se reinicia a mitad de un ciclo. **Sin evidencia**: no se probó contra uno real con `influxdb-client`.

## Decisiones

| Decisión | Alternativas | Porqué |
|---|---|---|
| Reintentar solo errores transitorios | Reintentar todo | Un 401 o un 400 reintentado 3 veces solo agrega 10 s de espera sin ninguna chance de éxito |
| Distinguir por el atributo `status` del error (duck typing) | `isinstance(ex, ApiException)` | Se puede testear sin `influxdb-client` instalado, y los errores de red (urllib3) no tienen `status` y son justo los transitorios |
| Cortar las escrituras del ciclo cuando una agota los reintentos | Reintentar cada tag por separado | Sin el corte, con InfluxDB caído y 18 tags un ciclo duraría 18 × 10 s = 180 s: el mismo problema que la spec 003 corrigió para la lectura |
| Política en `write_policy.py` (`write_with_retry` + `WriteGate`) | Inline en `main.py` | Se testea con escrituras y `sleep` falsos |

## Riesgos y preguntas abiertas

- **Un corte largo de InfluxDB sigue perdiendo puntos.** Reintentar 3 veces cubre un reinicio o un corte de segundos. Si InfluxDB está caído varios minutos, los puntos de esos ciclos se pierden igual (no hay buffer). Un buffer acotado en memoria, para reenviar con los timestamps originales al volver, sería una spec aparte. En el stack de la Raspberry Pi, `embolsadora-edge` lee de InfluxDB, así que un hueco acá es un hueco allá.
- **Trade-off de latencia:** con InfluxDB caído el ciclo pasa de ~0 s (antes: fallaba rápido y descartaba) a 10 s. Es el precio de reintentar.
- **No se probó contra `influxdb-client` real.** Se asume que sus errores HTTP traen `status` entero (`ApiException`), como documenta la librería; los errores de conexión llegan sin `status` y se tratan como transitorios.

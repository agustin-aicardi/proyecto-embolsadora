---
id: "003"
title: Ciclo acotado cuando el PLC no responde
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

# 003 — Ciclo acotado cuando el PLC no responde

## Contexto y problema

El historian lee los tags uno por uno. Si una lectura lanza una excepción (conexión caída, timeout) la reintenta 3 veces esperando 5 s, y **después sigue con el siguiente tag haciendo lo mismo**. Con el PLC caído, cada uno de los 18 tags cuesta 15 s: un ciclo tarda ~270 s (4,5 min) en vez de 1 s. Mientras tanto no se escribe nada, ni siquiera los tags que sí se podrían leer cuando el PLC vuelve. Además, tras el tercer intento fallido esperaba 5 s de más, sin nada que reintentar.

Es el desvío «Un tag caído frena el ciclo» que dejó anotado la [spec 001](../001-historian-semantico/spec.md). La constitution (principio V) pide reintentos cada 5 s: eso se mantiene.

## Alcance

Entra: la política de lectura por ciclo (reintentos y corte con el PLC caído) y su log. No entra: el reintento de la **escritura** en InfluxDB (otro desvío, spec aparte), el healthcheck, ni el tipo `int32`. No cambia qué se escribe en InfluxDB cuando todo funciona.

## Requisitos

- **RF-001** `origen: original` — Ante una excepción de lectura, el historian DEBE seguir reintentando hasta 3 veces por tag con 5 s entre intentos (se mantiene el principio V de la constitution).
- **RF-002** `origen: original` — NO DEBE esperar después del último intento fallido.
- **RF-003** `origen: original` — Cuando un tag agota sus reintentos por excepción, el PLC se considera caído **para el resto de ese ciclo**: los tags restantes NO DEBEN leerse; DEBEN quedar con calidad `BAD` y `reason: plc_unreachable`, y el ciclo DEBE registrar `cycle.reads_skipped` con la cantidad.
- **RF-004** `origen: original` — El ciclo siguiente DEBE volver a intentar desde el primer tag; el estado «caído» no se arrastra entre ciclos.
- **RF-005** `origen: original` — Una lectura que devuelve `None` (respuesta de error del PLC: el PLC contestó, el problema es de ese tag) NO DEBE reintentarse ni contar como PLC caído: los demás tags se siguen leyendo.
- **RF-006** `origen: original` — Con todo funcionando (o con el mock), el comportamiento y lo escrito en InfluxDB NO DEBEN cambiar.

## Criterios de éxito

- **CE-001** — `tests/test_read_policy.py` (9 tests) pasa con `python3 run_tests.py`. **Cumplido.**
- **CE-002** — Con un cliente que siempre lanza excepción, un ciclo de 18 tags dura `(3 − 1) × 5 = 10 s` en vez de ~270 s. **Cumplido** (corrida de `main()` con un cliente falso: 17 tags saltados por ciclo y ciclos separados por 10 s).
- **CE-003** — Con el mock, `main()` escribe los 18 tags por ciclo como antes. **Cumplido** (36 puntos en 2 ciclos, 18/18 `GOOD`).
- **CE-004** — Contra un PLC Modbus real que se desconecta y vuelve. **Sin evidencia**: nunca se probó contra uno.

## Decisiones

| Decisión | Alternativas | Porqué |
|---|---|---|
| Un solo tag que agota los reintentos corta el resto del ciclo | Cortar después de N tags fallidos; probar la conexión aparte (`connect()` / ping) | Es lo más simple y acota el ciclo a 10 s. Sólo cuenta la **excepción**, no la respuesta de error, así un tag mal configurado no tira abajo a los demás |
| La política vive en `read_policy.py` y `read_cycle` es un generador | Dejar el bucle inline en `main.py`; leer todo y después escribir | Se testea con lecturas y `sleep` falsos, sin pymodbus. El generador conserva el intercalado lectura→escritura de antes |
| Se mantiene el intervalo de 5 s | Reintento inmediato o con backoff | Es lo que pide la constitution (principio V) |

## Riesgos y preguntas abiertas

- **No se probó contra pymodbus real con un PLC caído.** No se sabe con certeza si `pymodbus` 3.1 lanza una excepción o devuelve un objeto de error cuando se cae la conexión. Si devolviera un error en vez de lanzar, esas lecturas ya eran rápidas (`None`, sin reintentos) y esta spec no cambia nada para ellas; el corte sólo actúa sobre la ruta lenta que hoy existe en el código. Conviene confirmarlo la primera vez que se pruebe con un PLC o un servidor Modbus de prueba apagado.
- Si el tag que agota los reintentos es el primero de la lista, **un tag lento oculta a los demás**: todos quedan `BAD` ese ciclo. Es el costo de no probar la conexión por separado.

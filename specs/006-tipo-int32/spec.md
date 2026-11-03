---
id: "006"
title: Tipo de tag int32
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

# 006 — Tipo de tag `int32`

## Contexto y problema

La constitution declara obligatorio el soporte de `bool`, `int16`, `int32` y `float32` (sección «Data Handling») y pide manejar el orden de bytes en los tipos de 32 bits. El código solo leía `bool`, `int16` y `float32`; un tag `type: int32` en `tags.yaml` hacía lanzar `UnsupportedTagType`. Ningún tag actual lo usa, así que no rompe nada hoy, pero el primer contador de 32 bits del PLC (acumuladores de piezas o de horas de producción son típicos) no se podría leer.

Es el desvío «Tipo `int32` no soportado» de la [spec 001](../001-historian-semantico/spec.md). La alternativa de enmendar la constitution quedó descartada: el tipo es corto de implementar y los contadores de 32 bits son habituales en PLC.

## Alcance

Entra: leer tags `int32` con signo, con `byteorder` y `scale`. No entra: `uint32`, `int64` ni otros tipos; agregar tags `int32` a `tags.yaml` o a `aas_mapping.yaml` (son contratos que consumen el edge y el frontend); ni corregir el orden de palabras de `float32` (ver «Riesgos»).

## Requisitos

- **RF-001** `origen: original` — Un tag `type: int32` DEBE leerse con 2 registros de 16 bits consecutivos desde `address` y devolverse como entero con signo (−2 147 483 648 a 2 147 483 647).
- **RF-002** `origen: original` — Con `byteorder: big` (por defecto, el estándar Modbus) el primer registro DEBE ser la palabra alta; con `byteorder: little` el primero DEBE ser la palabra baja. Dentro de cada palabra los bytes son big-endian.
- **RF-003** `origen: original` — `scale`, si está definido y es distinto de 0, DEBE multiplicar el valor, igual que en los otros tipos.
- **RF-004** `origen: original` — Una respuesta de error del PLC (sin `registers`) DEBE devolver `None`, igual que en los otros tipos.
- **RF-005** `origen: original` — Un tipo desconocido DEBE seguir lanzando `UnsupportedTagType`.

## Criterios de éxito

- **CE-001** — `tests/test_int32.py` (10 tests: valores positivos, negativos, límites, ambos `byteorder`, `scale`, respuesta de error y tipo desconocido) pasa con `python3 run_tests.py`. **Cumplido.**
- **CE-002** — Leer un `int32` de un PLC real con el orden de palabras que ese PLC use. **Sin evidencia**: nunca se probó contra un PLC. El orden de palabras varía entre fabricantes; hay que confirmar `byteorder` con el primer contador real.

## Decisiones

| Decisión | Alternativas | Porqué |
|---|---|---|
| Implementarlo | Enmendar la constitution para sacar `int32` | Es la regla del proyecto, es poco código (una función de 6 líneas y una rama en `read_tag`) y el caso de uso es real |
| Con signo | `uint32` | La constitution dice «Int32». Un contador que supere 2 147 483 647 es raro; si hace falta `uint32` se agrega como tipo aparte |
| `little` = palabras invertidas, bytes big-endian dentro de la palabra | Invertir también los bytes | Es lo que Modbus define (los registros viajan big-endian) y lo que describe el docstring de `float32_from_registers` |

## Riesgos y preguntas abiertas

- **Hallazgo aparte, no corregido acá:** `float32_from_registers(..., byteorder="little")` devuelve un valor incorrecto. Con los registros de `123.456` en orden invertido da `1.5e35`: invierte los bytes de todo el valor en vez de solo las palabras. **Hoy ningún tag usa `byteorder: little`** (los 18 son `big`), por eso nunca se notó. Los tests solo cubren `big`. Es otro defecto y merece su propia spec; `int32` no depende de él.
- No se agregó ningún tag `int32` al mock ni a `tags.yaml`: cambiaría el contrato con el edge y el frontend. El tipo queda disponible para cuando haga falta.
- ¿`aas_mapping.yaml` espera `xs:int` para estos tags? El catálogo lo declara por variable (`value_type`); no hay ninguna `int32` hoy, así que no se verificó.

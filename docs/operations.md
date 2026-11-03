---
title: Operación del historian
owner: Federico Degiovanni
status: vigente
last_reviewed: 2026-11-02
---

# Operación

Despliegue, observabilidad y troubleshooting **del historian**. La instalación completa en una Raspberry Pi junto al edge, con una sola InfluxDB, está en [`embolsadora-bundle`](https://github.com/fdegiovanni/embolsadora-bundle) (`docs/operations.md`); acá solo lo propio de este componente.

## Despliegue

- **Con este repo:** `docker compose up -d --build` levanta `app` (el historian), `influxdb` (2.6) y `faaast` (puerto `8081`). Las variables salen del compose y del `.env`.
- **Imagen publicada:** en un push a `main`, y solo si pasó la integración, la CI publica `ghcr.io/<repo>` para `linux/amd64` y `linux/arm64`, con las etiquetas `latest` y `sha-<corto>` (para fijar una versión) ([HIST-ADR-004](./adr/HIST-ADR-004-publicar-imagen-multiarch.md), [spec 007](../specs/007-imagen-multiarch/spec.md)).
- **Junto al edge en una Pi:** usar `embolsadora-bundle`, que reemplaza esta InfluxDB por una compartida con el edge. **No levantar ambos stacks a la vez**: pelean por el puerto `8086`.

> El compose de este repo tiene fijados en texto plano la contraseña de admin de InfluxDB y publica `8086` y `8081` en todas las interfaces. Sirve para desarrollo, no para una planta.

## Verificar que funciona

```bash
docker compose logs --tail 40 app          # deben verse point.written y cycle.completed
```

Consulta Flux del último valor de una variable (UI en `http://localhost:8086`, org `org`, bucket `bucket`):

```flux
from(bucket: "bucket")
  |> range(start: -10m)
  |> filter(fn: (r) => r._measurement == "historian_semantic")
  |> filter(fn: (r) => r._field == "peso")
  |> last()
```

## Observabilidad

El historian **no expone ningún endpoint ni métricas**. Tiene dos señales:

- **Salud (`docker compose ps`):** el contenedor figura `healthy` mientras el historian siga completando ciclos (escribe un latido al final de cada uno; spec 005). `unhealthy` significa que **el proceso dejó de ciclar** (colgado o bloqueado), no que el PLC o InfluxDB estén mal: con ellos caídos el contenedor sigue `healthy`. Docker lo informa pero no lo reinicia por sí solo. Detalle: `docker inspect <contenedor> --format '{{json .State.Health}}'`. Ajustes: `HEALTH_MAX_AGE_S` y `HEARTBEAT_FILE`.
- **Logs:** una línea JSON por evento en la salida estándar.

| Evento | Qué significa |
|---|---|
| `historian.started` | Arrancó; informa host Modbus y cantidad de tags |
| `modbus.using_mock` | Usa el PLC simulado |
| `modbus.connect_failed` / `modbus.connect_exception` | No pudo conectar al PLC. **No aborta**: el proceso sigue y cada lectura falla |
| `read.failed` | Falló un intento de lectura (hasta 3 por tag, 5 s entre intentos) |
| `cycle.reads_skipped` | Un tag agotó los intentos (PLC sin respuesta) y el resto del ciclo no se leyó |
| `value.missing` | Se agotaron los intentos: el tag queda `BAD` en ese ciclo |
| `mapping.missing_for_tag` | El tag no tiene entrada en `aas_mapping.yaml`: **no se escribe** |
| `point.written` | Punto escrito en InfluxDB |
| `influx.write_retry` | Falló un intento de escritura transitorio (hasta 3 por punto, 5 s entre intentos) |
| `influx.write_failed` | No se pudo escribir; el punto de ese ciclo se pierde |
| `cycle.writes_skipped` | InfluxDB no respondió y el resto de las escrituras del ciclo se saltó |
| `heartbeat.failed` | No se pudo escribir el archivo de latido (una sola vez); el contenedor pasará a `unhealthy` |
| `aas.updated` / `aas.update_failed` | Resultado de la actualización del XML AAS |
| `cycle.completed` | Fin de ciclo, con `tags_ok` y `tags_bad` |

## Troubleshooting

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| No hay puntos en InfluxDB y los logs dicen `mapping.missing_for_tag` | Falta `AAS_MAPPING_PATH` o el archivo no está montado | Verificar la variable y el volumen de `aas_mapping.yaml` |
| El log repite `read.failed` | PLC inalcanzable o dirección/tipo mal en `tags.yaml` | Verificar `MODBUS_HOST` y `tags.yaml`. Con `MODBUS_HOST=mock` no debería pasar |
| Los ciclos tardan ~10 s y hay `cycle.reads_skipped` / `read.failed` | El PLC (o Modbus) no responde: el primer tag agota 3 intentos y el resto se salta ese ciclo | Revisar `MODBUS_HOST`/`MODBUS_PORT` y la red; cuando el PLC vuelva, el siguiente ciclo lee todo |
| El contenedor se reinicia en bucle con `config.invalid` | Falta `INFLUX_TOKEN` (o está vacío): el historian no arranca sin él | Definirlo en `.env` y reiniciar |
| `influx.write_retry` y después `cycle.writes_skipped` | InfluxDB no responde (red, 5xx): se reintenta 3 veces cada 5 s y el resto del ciclo se salta; el ciclo dura ~10 s | Revisar que InfluxDB esté arriba y `INFLUX_URL`. Los puntos de los ciclos con fallo **no se recuperan** |
| `influx.write_failed` con 401 | `INFLUX_TOKEN` definido pero incorrecto | Corregirlo (debe ser el mismo que usó InfluxDB al inicializarse) y reiniciar |
| `Could not save environment to file .../model_persistence.xml` en FA³ST | El volumen de datos de FA³ST es de root | Aviso no fatal; no afecta al historian |
| `curl http://localhost:8081/...` falla con `HTTP/0.9` | FA³ST sirve HTTPS con certificado autofirmado, API v3.1 | `curl -sk https://localhost:8081/api/v3.1/submodels` |

## Seguridad

- `.env` **estuvo versionado** en este repo y el historial de git lo conserva aunque ya no se rastree. Este repo es público, así que toda credencial que ese archivo haya contenido hay que tratarla como expuesta. Dejar de versionarlo evita nuevas filtraciones; **no** limpia las anteriores.
- No poner credenciales reales en `.env.example`, docs ni commits.

---
title: Operación del historian
owner: Federico Degiovanni
status: vigente
last_reviewed: 2026-10-29
---

# Operación

Despliegue, observabilidad y troubleshooting **del historian**. La instalación completa en una Raspberry Pi junto al edge, con una sola InfluxDB, está en [`embolsadora-bundle`](https://github.com/fdegiovanni/embolsadora-bundle) (`docs/operations.md`); acá solo lo propio de este componente.

## Despliegue

- **Con este repo:** `docker compose up -d --build` levanta `app` (el historian), `influxdb` (2.6) y `faaast` (puerto `8081`). Las variables salen del compose y del `.env`.
- **Imagen publicada:** la CI construye `linux/arm64` y, en un push a `main`, publica `ghcr.io/<repo>:latest`. Solo `latest` y solo arm64 ([HIST-ADR-003](./adr/HIST-ADR-003-docker-first-arm64.md)).
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

El historian **no expone ningún endpoint** (ni salud ni métricas). Lo único observable son sus logs: una línea JSON por evento en la salida estándar.

| Evento | Qué significa |
|---|---|
| `historian.started` | Arrancó; informa host Modbus y cantidad de tags |
| `modbus.using_mock` | Usa el PLC simulado |
| `modbus.connect_failed` / `modbus.connect_exception` | No pudo conectar al PLC. **No aborta**: el proceso sigue y cada lectura falla |
| `read.failed` | Falló un intento de lectura (hasta 3 por tag, 5 s entre intentos) |
| `value.missing` | Se agotaron los intentos: el tag queda `BAD` en ese ciclo |
| `mapping.missing_for_tag` | El tag no tiene entrada en `aas_mapping.yaml`: **no se escribe** |
| `point.written` | Punto escrito en InfluxDB |
| `influx.write_failed` | Falló la escritura; el punto de ese ciclo se pierde |
| `aas.updated` / `aas.update_failed` | Resultado de la actualización del XML AAS |
| `cycle.completed` | Fin de ciclo, con `tags_ok` y `tags_bad` |

## Troubleshooting

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| No hay puntos en InfluxDB y los logs dicen `mapping.missing_for_tag` | Falta `AAS_MAPPING_PATH` o el archivo no está montado | Verificar la variable y el volumen de `aas_mapping.yaml` |
| El log repite `read.failed` | PLC inalcanzable o dirección/tipo mal en `tags.yaml` | Verificar `MODBUS_HOST` y `tags.yaml`. Con `MODBUS_HOST=mock` no debería pasar |
| Los ciclos se enlentecen mucho | Hay tags fallando: cada uno cuesta hasta 15 s (3 × 5 s) y se leen en serie | Arreglar la lectura o sacar el tag de `tags.yaml` |
| `influx.write_failed` con 401 | `INFLUX_TOKEN` incorrecto (el valor por defecto `my-token` no autentica) | Definir `INFLUX_TOKEN` y reiniciar |
| `Could not save environment to file .../model_persistence.xml` en FA³ST | El volumen de datos de FA³ST es de root | Aviso no fatal; no afecta al historian |
| `curl http://localhost:8081/...` falla con `HTTP/0.9` | FA³ST sirve HTTPS con certificado autofirmado, API v3.1 | `curl -sk https://localhost:8081/api/v3.1/submodels` |

## Seguridad

- `.env` **estuvo versionado** en este repo y lo conserva el historial de git aunque ya no se rastree. **Toda credencial que haya contenido debe considerarse expuesta y rotarse** (en particular el token de InfluxDB). Este repo es público.
- No poner credenciales reales en `.env.example`, docs ni commits.

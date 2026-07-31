# Uso de recursos en Raspberry Pi

## 1. Objetivo

Esta prueba tiene como finalidad cuantificar el consumo de recursos de la arquitectura edge propuesta para la digitalización de la máquina embolsadora.

El objetivo es verificar si el middleware Python, InfluxDB, BaSyx AAS Environment y BaSyx UI pueden ejecutarse simultáneamente sobre una Raspberry Pi sin requerir hardware de mayores prestaciones.

## 2. Plataforma de ensayo

| Parámetro | Valor |
|---|---|
| Equipo | Raspberry Pi 4 Model B Rev 1.4 |
| Hostname | `raspberrypi` |
| Sistema operativo | Debian GNU/Linux 12 (bookworm) |
| Arquitectura | `aarch64` |
| Kernel | `Linux 6.12.34+rpt-rpi-v8 #1 SMP PREEMPT Debian 1:6.12.34-1+rpt1~bookworm (2025-06-26) GNU/Linux` |
| Docker | `Docker version 20.10.24+dfsg1, build 297e128` |
| Docker Compose | `Docker Compose version v5.0.0` |
| Memoria RAM total | 7.64 GiB |

## 3. Arquitectura desplegada

Durante la prueba se ejecutaron simultáneamente los siguientes servicios:

- `aas_historian_middleware`: lectura, validación y procesamiento de datos.
- `proyecto-embolsadora-influxdb-1`: almacenamiento histórico.
- `basyx_aas_environment`: publicación del Asset Administration Shell.
- `basyx-ui`: visualización web del AAS.

## 4. Metodología

| Parámetro | Valor |
|---|---:|
| Fecha del ensayo | 2026-07-30T23:30:58-03:00 |
| Cantidad de muestras | 30 |
| Intervalo entre muestras | 10 segundos |
| Duración aproximada | 5.0 minutos |
| Medición de CPU | `docker stats --no-stream` |
| Medición de RAM por contenedor | Suma del RSS de los procesos del contenedor |
| Medición general de memoria | `free -b` |
| Medición de carga | `/proc/loadavg` |
| Medición de temperatura | `vcgencmd measure_temp` |

## 5. Resultados

### 5.1 Consumo de CPU

| Servicio | Función | CPU promedio | CPU máxima |
|---|---|---:|---:|
| `aas_historian_middleware` | Middleware Python e historiador | 7.47 % | 18.07 % |
| `basyx_aas_environment` | Servidor Asset Administration Shell | 3.55 % | 43.38 % |
| `basyx-ui` | Interfaz web de BaSyx | 0.00 % | 0.00 % |
| `proyecto-embolsadora-influxdb-1` | Base de datos de series temporales | 3.82 % | 10.88 % |

### 5.2 Memoria RAM por servicio

| Servicio | RAM promedio | RAM máxima |
|---|---:|---:|
| `aas_historian_middleware` | 47.50 MiB | 47.50 MiB |
| `basyx_aas_environment` | 716.44 MiB | 717.83 MiB |
| `basyx-ui` | 8.02 MiB | 8.02 MiB |
| `proyecto-embolsadora-influxdb-1` | 135.85 MiB | 136.47 MiB |

### 5.3 Recursos generales del sistema

| Indicador | Promedio | Mínimo | Máximo |
|---|---:|---:|---:|
| RAM utilizada | 1.28 GiB | 1.27 GiB | 1.30 GiB |
| RAM disponible | 6.36 GiB | 6.34 GiB | 6.37 GiB |
| Load average, 1 minuto | 0.81 | 0.49 | 1.23 |
| Load average, 5 minutos | 0.96 | 0.87 | 1.13 |
| Load average, 15 minutos | 0.79 | 0.76 | 0.83 |
| Temperatura de CPU | 33.74 °C | 32.60 °C | 34.50 °C |

## 6. Discusión

El mayor pico individual de CPU fue registrado por `basyx_aas_environment`, con un valor de **43.38 %**.

La memoria RAM disponible se mantuvo en promedio en **6.36 GiB**, equivalente aproximadamente al **83.3 %** de la memoria total.

La temperatura del procesador se mantuvo entre **32.60 °C** y **34.50 °C**, sin evidencias de sobrecarga térmica durante el ensayo.

Los valores de `load average` se mantuvieron en niveles bajos durante la prueba, lo que indica que el sistema no presentó saturación sostenida de procesamiento.

Los resultados corresponden a una prueba funcional de corta duración con datos simulados. Para una evaluación definitiva, conviene repetir el ensayo durante una operación prolongada y posteriormente con comunicación real con el PLC.

## 7. Conclusión

La arquitectura propuesta pudo ejecutar simultáneamente el middleware Python, InfluxDB, BaSyx AAS Environment y BaSyx UI sobre la Raspberry Pi, manteniendo un margen amplio de memoria disponible, una carga moderada de CPU y una temperatura de operación reducida.

En las condiciones evaluadas, la Raspberry Pi resulta adecuada como plataforma edge para el despliegue de la solución de digitalización de la máquina embolsadora.

## 8. Reproducibilidad

La medición puede repetirse ejecutando:

```bash
./tools/resource_usage.sh
python3 tools/generate_resource_report.py
```

Archivos generados:

- `docs/RESOURCE_USAGE_RPI.txt`: datos crudos del ensayo.
- `docs/RESOURCE_USAGE_RPI.md`: informe procesado.

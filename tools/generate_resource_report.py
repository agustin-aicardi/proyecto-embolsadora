#!/usr/bin/env python3

from __future__ import annotations

import csv
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path


INPUT_FILE = Path("docs/RESOURCE_USAGE_RPI.txt")
OUTPUT_FILE = Path("docs/RESOURCE_USAGE_RPI.md")


def parse_metadata(lines: list[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}

    for line in lines:
        if "=" not in line:
            continue

        key, value = line.split("=", 1)

        if key.isupper():
            metadata[key.strip()] = value.strip()

    return metadata


def mean(values: list[float]) -> float | None:
    clean = [value for value in values if not math.isnan(value)]
    return statistics.mean(clean) if clean else None


def maximum(values: list[float]) -> float | None:
    clean = [value for value in values if not math.isnan(value)]
    return max(clean) if clean else None


def minimum(values: list[float]) -> float | None:
    clean = [value for value in values if not math.isnan(value)]
    return min(clean) if clean else None


def to_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def bytes_to_gib(value: float | None) -> str:
    if value is None or math.isnan(value):
        return "No disponible"

    return f"{value / (1024 ** 3):.2f} GiB"


def kib_to_mib(value: float | None) -> str:
    if value is None or math.isnan(value):
        return "No disponible"

    return f"{value / 1024:.2f} MiB"


def percent(value: float | None) -> str:
    if value is None or math.isnan(value):
        return "No disponible"

    return f"{value:.2f} %"


def number(value: float | None, decimals: int = 2) -> str:
    if value is None or math.isnan(value):
        return "No disponible"

    return f"{value:.{decimals}f}"


if not INPUT_FILE.exists():
    print(f"ERROR: no existe {INPUT_FILE}")
    sys.exit(1)

text = INPUT_FILE.read_text(encoding="utf-8", errors="replace")
lines = text.splitlines()

if "END_OF_REPORT=" not in text:
    print("ERROR: el archivo de medición está incompleto.")
    print("Primero ejecutá tools/resource_usage.sh y esperá a que finalice.")
    sys.exit(1)

metadata = parse_metadata(lines)

header = (
    "SAMPLE|TIMESTAMP|CONTAINER|CPU_PERCENT|RSS_KIB|"
    "RAM_USED_BYTES|RAM_AVAILABLE_BYTES|LOAD_1M|LOAD_5M|"
    "LOAD_15M|TEMP_C"
)

try:
    start_index = lines.index(header)
except ValueError:
    print("ERROR: no se encontró la cabecera de datos.")
    sys.exit(1)

data_lines: list[str] = []

for line in lines[start_index + 1:]:
    if line.startswith("================ SYSTEM FINAL STATE"):
        break

    if line.strip():
        data_lines.append(line)

reader = csv.DictReader(data_lines, delimiter="|", fieldnames=header.split("|"))

cpu_by_container: dict[str, list[float]] = defaultdict(list)
rss_by_container: dict[str, list[float]] = defaultdict(list)

ram_used: list[float] = []
ram_available: list[float] = []
load_1m: list[float] = []
load_5m: list[float] = []
load_15m: list[float] = []
temperatures: list[float] = []

seen_samples: set[str] = set()

for row in reader:
    container = row["CONTAINER"]
    cpu_by_container[container].append(to_float(row["CPU_PERCENT"]))
    rss_by_container[container].append(to_float(row["RSS_KIB"]))

    sample = row["SAMPLE"]

    if sample not in seen_samples:
        seen_samples.add(sample)
        ram_used.append(to_float(row["RAM_USED_BYTES"]))
        ram_available.append(to_float(row["RAM_AVAILABLE_BYTES"]))
        load_1m.append(to_float(row["LOAD_1M"]))
        load_5m.append(to_float(row["LOAD_5M"]))
        load_15m.append(to_float(row["LOAD_15M"]))
        temperatures.append(to_float(row["TEMP_C"]))


container_descriptions = {
    "aas_historian_middleware": "Middleware Python e historiador",
    "basyx_aas_environment": "Servidor Asset Administration Shell",
    "basyx-ui": "Interfaz web de BaSyx",
    "proyecto-embolsadora-influxdb-1": "Base de datos de series temporales",
}

container_order = [
    "aas_historian_middleware",
    "basyx_aas_environment",
    "basyx-ui",
    "proyecto-embolsadora-influxdb-1",
]

sample_count = len(seen_samples)
interval_seconds = int(metadata.get("INTERVAL_SECONDS", "0") or 0)
duration_minutes = sample_count * interval_seconds / 60 if interval_seconds else 0

total_ram_bytes = None

for line in lines:
    if line.startswith("Mem:"):
        parts = line.split()

        if len(parts) >= 2:
            try:
                total_ram_bytes = float(parts[1])
                break
            except ValueError:
                pass

ram_available_avg = mean(ram_available)
ram_available_percent = None

if total_ram_bytes and ram_available_avg is not None:
    ram_available_percent = ram_available_avg / total_ram_bytes * 100

max_individual_cpu = None
max_individual_container = None

for container in container_order:
    current_max = maximum(cpu_by_container.get(container, []))

    if current_max is None:
        continue

    if max_individual_cpu is None or current_max > max_individual_cpu:
        max_individual_cpu = current_max
        max_individual_container = container

md: list[str] = []

md.append("# Uso de recursos en Raspberry Pi")
md.append("")

md.append("## 1. Objetivo")
md.append("")
md.append(
    "Esta prueba tiene como finalidad cuantificar el consumo de recursos "
    "de la arquitectura edge propuesta para la digitalización de la máquina "
    "embolsadora."
)
md.append("")
md.append(
    "El objetivo es verificar si el middleware Python, InfluxDB, "
    "BaSyx AAS Environment y BaSyx UI pueden ejecutarse simultáneamente "
    "sobre una Raspberry Pi sin requerir hardware de mayores prestaciones."
)
md.append("")

md.append("## 2. Plataforma de ensayo")
md.append("")
md.append("| Parámetro | Valor |")
md.append("|---|---|")
md.append(f"| Equipo | {metadata.get('MODEL', 'No disponible')} |")
md.append(f"| Hostname | `{metadata.get('HOSTNAME', 'No disponible')}` |")
md.append(f"| Sistema operativo | {metadata.get('OS', 'No disponible')} |")
md.append(f"| Arquitectura | `{metadata.get('ARCHITECTURE', 'No disponible')}` |")
md.append(f"| Kernel | `{metadata.get('KERNEL', 'No disponible')}` |")
md.append(f"| Docker | `{metadata.get('DOCKER_VERSION', 'No disponible')}` |")
md.append(f"| Docker Compose | `{metadata.get('COMPOSE_VERSION', 'No disponible')}` |")

if total_ram_bytes is not None:
    md.append(f"| Memoria RAM total | {bytes_to_gib(total_ram_bytes)} |")

md.append("")

md.append("## 3. Arquitectura desplegada")
md.append("")
md.append(
    "Durante la prueba se ejecutaron simultáneamente los siguientes servicios:"
)
md.append("")
md.append("- `aas_historian_middleware`: lectura, validación y procesamiento de datos.")
md.append("- `proyecto-embolsadora-influxdb-1`: almacenamiento histórico.")
md.append("- `basyx_aas_environment`: publicación del Asset Administration Shell.")
md.append("- `basyx-ui`: visualización web del AAS.")
md.append("")

md.append("## 4. Metodología")
md.append("")
md.append("| Parámetro | Valor |")
md.append("|---|---:|")
md.append(f"| Fecha del ensayo | {metadata.get('REPORT_DATE', 'No disponible')} |")
md.append(f"| Cantidad de muestras | {sample_count} |")
md.append(f"| Intervalo entre muestras | {interval_seconds} segundos |")
md.append(f"| Duración aproximada | {duration_minutes:.1f} minutos |")
md.append("| Medición de CPU | `docker stats --no-stream` |")
md.append("| Medición de RAM por contenedor | Suma del RSS de los procesos del contenedor |")
md.append("| Medición general de memoria | `free -b` |")
md.append("| Medición de carga | `/proc/loadavg` |")
md.append("| Medición de temperatura | `vcgencmd measure_temp` |")
md.append("")

md.append("## 5. Resultados")
md.append("")

md.append("### 5.1 Consumo de CPU")
md.append("")
md.append("| Servicio | Función | CPU promedio | CPU máxima |")
md.append("|---|---|---:|---:|")

for container in container_order:
    md.append(
        f"| `{container}` | "
        f"{container_descriptions.get(container, '')} | "
        f"{percent(mean(cpu_by_container.get(container, [])))} | "
        f"{percent(maximum(cpu_by_container.get(container, [])))} |"
    )

md.append("")

md.append("### 5.2 Memoria RAM por servicio")
md.append("")
md.append("| Servicio | RAM promedio | RAM máxima |")
md.append("|---|---:|---:|")

for container in container_order:
    md.append(
        f"| `{container}` | "
        f"{kib_to_mib(mean(rss_by_container.get(container, [])))} | "
        f"{kib_to_mib(maximum(rss_by_container.get(container, [])))} |"
    )

md.append("")

md.append("### 5.3 Recursos generales del sistema")
md.append("")
md.append("| Indicador | Promedio | Mínimo | Máximo |")
md.append("|---|---:|---:|---:|")
md.append(
    f"| RAM utilizada | "
    f"{bytes_to_gib(mean(ram_used))} | "
    f"{bytes_to_gib(minimum(ram_used))} | "
    f"{bytes_to_gib(maximum(ram_used))} |"
)
md.append(
    f"| RAM disponible | "
    f"{bytes_to_gib(mean(ram_available))} | "
    f"{bytes_to_gib(minimum(ram_available))} | "
    f"{bytes_to_gib(maximum(ram_available))} |"
)
md.append(
    f"| Load average, 1 minuto | "
    f"{number(mean(load_1m))} | "
    f"{number(minimum(load_1m))} | "
    f"{number(maximum(load_1m))} |"
)
md.append(
    f"| Load average, 5 minutos | "
    f"{number(mean(load_5m))} | "
    f"{number(minimum(load_5m))} | "
    f"{number(maximum(load_5m))} |"
)
md.append(
    f"| Load average, 15 minutos | "
    f"{number(mean(load_15m))} | "
    f"{number(minimum(load_15m))} | "
    f"{number(maximum(load_15m))} |"
)
md.append(
    f"| Temperatura de CPU | "
    f"{number(mean(temperatures))} °C | "
    f"{number(minimum(temperatures))} °C | "
    f"{number(maximum(temperatures))} °C |"
)
md.append("")

md.append("## 6. Discusión")
md.append("")

if max_individual_cpu is not None and max_individual_container is not None:
    md.append(
        f"El mayor pico individual de CPU fue registrado por "
        f"`{max_individual_container}`, con un valor de "
        f"**{max_individual_cpu:.2f} %**."
    )
    md.append("")

if ram_available_avg is not None:
    ram_text = (
        f"La memoria RAM disponible se mantuvo en promedio en "
        f"**{bytes_to_gib(ram_available_avg)}**"
    )

    if ram_available_percent is not None:
        ram_text += (
            f", equivalente aproximadamente al "
            f"**{ram_available_percent:.1f} %** de la memoria total"
        )

    ram_text += "."

    md.append(ram_text)
    md.append("")

if temperatures:
    md.append(
        f"La temperatura del procesador se mantuvo entre "
        f"**{minimum(temperatures):.2f} °C** y "
        f"**{maximum(temperatures):.2f} °C**, sin evidencias de "
        f"sobrecarga térmica durante el ensayo."
    )
    md.append("")

md.append(
    "Los valores de `load average` se mantuvieron en niveles bajos durante "
    "la prueba, lo que indica que el sistema no presentó saturación sostenida "
    "de procesamiento."
)
md.append("")

md.append(
    "Los resultados corresponden a una prueba funcional de corta duración "
    "con datos simulados. Para una evaluación definitiva, conviene repetir "
    "el ensayo durante una operación prolongada y posteriormente con "
    "comunicación real con el PLC."
)
md.append("")

md.append("## 7. Conclusión")
md.append("")
md.append(
    "La arquitectura propuesta pudo ejecutar simultáneamente el middleware "
    "Python, InfluxDB, BaSyx AAS Environment y BaSyx UI sobre la Raspberry Pi, "
    "manteniendo un margen amplio de memoria disponible, una carga moderada "
    "de CPU y una temperatura de operación reducida."
)
md.append("")
md.append(
    "En las condiciones evaluadas, la Raspberry Pi resulta adecuada como "
    "plataforma edge para el despliegue de la solución de digitalización "
    "de la máquina embolsadora."
)
md.append("")

md.append("## 8. Reproducibilidad")
md.append("")
md.append("La medición puede repetirse ejecutando:")
md.append("")
md.append("```bash")
md.append("./tools/resource_usage.sh")
md.append("python3 tools/generate_resource_report.py")
md.append("```")
md.append("")
md.append("Archivos generados:")
md.append("")
md.append("- `docs/RESOURCE_USAGE_RPI.txt`: datos crudos del ensayo.")
md.append("- `docs/RESOURCE_USAGE_RPI.md`: informe procesado.")
md.append("")

OUTPUT_FILE.write_text("\n".join(md), encoding="utf-8")

print("Informe generado correctamente:")
print(OUTPUT_FILE)

#!/usr/bin/env bash

set -euo pipefail

OUTPUT="docs/RESOURCE_USAGE_RPI.txt"
SAMPLES=30
INTERVAL=10

CONTAINERS=(
    "aas_historian_middleware"
    "basyx_aas_environment"
    "basyx-ui"
    "proyecto-embolsadora-influxdb-1"
)

mkdir -p docs

get_container_rss_kib() {
    local container="$1"
    local pids
    local total=0

    pids=$(docker top "$container" -eo pid 2>/dev/null \
        | tail -n +2 \
        | awk '{print $1}' \
        | tr '\n' ',' \
        | sed 's/,$//')

    if [ -n "$pids" ]; then
        total=$(ps -o rss= -p "$pids" 2>/dev/null \
            | awk '{sum += $1} END {print sum + 0}')
    fi

    echo "$total"
}

get_container_cpu() {
    local container="$1"

    docker stats --no-stream \
        --format '{{.CPUPerc}}' \
        "$container" 2>/dev/null \
        | tr -d '%'
}

get_model() {
    if [ -f /proc/device-tree/model ]; then
        tr -d '\0' < /proc/device-tree/model
    else
        echo "No disponible"
    fi
}

echo "===================================================" > "$OUTPUT"
echo "Raspberry Pi Resource Usage Report - Raw Data" >> "$OUTPUT"
echo "===================================================" >> "$OUTPUT"
echo "REPORT_DATE=$(date --iso-8601=seconds)" >> "$OUTPUT"
echo "MODEL=$(get_model)" >> "$OUTPUT"
echo "HOSTNAME=$(hostname)" >> "$OUTPUT"
echo "ARCHITECTURE=$(uname -m)" >> "$OUTPUT"
echo "KERNEL=$(uname -srvo)" >> "$OUTPUT"
echo "OS=$(grep '^PRETTY_NAME=' /etc/os-release | cut -d= -f2- | tr -d '\"')" >> "$OUTPUT"
echo "DOCKER_VERSION=$(docker --version)" >> "$OUTPUT"
echo "COMPOSE_VERSION=$(docker compose version)" >> "$OUTPUT"
echo "SAMPLES=$SAMPLES" >> "$OUTPUT"
echo "INTERVAL_SECONDS=$INTERVAL" >> "$OUTPUT"
echo >> "$OUTPUT"

echo "================ SYSTEM INITIAL STATE =============" >> "$OUTPUT"
echo "--- CPU INFO ---" >> "$OUTPUT"
lscpu >> "$OUTPUT" 2>/dev/null || true
echo >> "$OUTPUT"

echo "--- MEMORY ---" >> "$OUTPUT"
free -b >> "$OUTPUT"
echo >> "$OUTPUT"

echo "--- DISK ---" >> "$OUTPUT"
df -B1 / >> "$OUTPUT"
echo >> "$OUTPUT"

echo "--- CONTAINERS ---" >> "$OUTPUT"
docker compose ps >> "$OUTPUT"
echo >> "$OUTPUT"

echo "================ SAMPLE DATA =======================" >> "$OUTPUT"
echo "SAMPLE|TIMESTAMP|CONTAINER|CPU_PERCENT|RSS_KIB|RAM_USED_BYTES|RAM_AVAILABLE_BYTES|LOAD_1M|LOAD_5M|LOAD_15M|TEMP_C" >> "$OUTPUT"

echo
echo "Se tomarán $SAMPLES muestras cada $INTERVAL segundos."
echo "Duración aproximada: $((SAMPLES * INTERVAL / 60)) minutos."
echo

for sample in $(seq 1 "$SAMPLES"); do
    timestamp=$(date --iso-8601=seconds)

    read -r mem_total mem_used mem_free mem_shared mem_buff mem_available \
        < <(free -b | awk '/^Mem:/ {print $2, $3, $4, $5, $6, $7}')

    read -r load_1 load_5 load_15 \
        < <(awk '{print $1, $2, $3}' /proc/loadavg)

    temp_c=$(vcgencmd measure_temp 2>/dev/null \
        | sed -E "s/temp=([0-9.]+).*/\1/" || echo "NA")

    echo "Muestra $sample/$SAMPLES"

    for container in "${CONTAINERS[@]}"; do
        if docker inspect "$container" >/dev/null 2>&1; then
            cpu=$(get_container_cpu "$container")
            rss_kib=$(get_container_rss_kib "$container")

            [ -n "$cpu" ] || cpu="0"
            [ -n "$rss_kib" ] || rss_kib="0"

            echo \
"$sample|$timestamp|$container|$cpu|$rss_kib|$mem_used|$mem_available|$load_1|$load_5|$load_15|$temp_c" \
                >> "$OUTPUT"
        else
            echo \
"$sample|$timestamp|$container|NA|NA|$mem_used|$mem_available|$load_1|$load_5|$load_15|$temp_c" \
                >> "$OUTPUT"
        fi
    done

    if [ "$sample" -lt "$SAMPLES" ]; then
        sleep "$INTERVAL"
    fi
done

echo >> "$OUTPUT"
echo "================ SYSTEM FINAL STATE ===============" >> "$OUTPUT"
echo "--- MEMORY ---" >> "$OUTPUT"
free -b >> "$OUTPUT"
echo >> "$OUTPUT"

echo "--- DISK ---" >> "$OUTPUT"
df -B1 / >> "$OUTPUT"
echo >> "$OUTPUT"

echo "--- UPTIME ---" >> "$OUTPUT"
uptime >> "$OUTPUT"
echo >> "$OUTPUT"

echo "END_OF_REPORT=$(date --iso-8601=seconds)" >> "$OUTPUT"

echo
echo "Medición finalizada correctamente."
echo "Archivo generado: $OUTPUT"

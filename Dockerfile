FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src /app/src

ENV PYTHONUNBUFFERED=1
ENV HISTORIAN_TAGS=/app/src/historian/tags.yaml

# Sano = el historian completó un ciclo hace poco (ver src/historian/heartbeat.py).
# No mide que el PLC o InfluxDB estén bien, sino que el proceso sigue ciclando.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD ["python", "-m", "src.historian.heartbeat"]

CMD ["python", "-m", "src.historian.main"]

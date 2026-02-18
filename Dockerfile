FROM --platform=linux/arm64 python:3.11-slim-bookworm

WORKDIR /app

# system deps (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src /app/src
WORKDIR /app/src

ENV PYTHONUNBUFFERED=1
ENV HISTORIAN_TAGS=/app/src/historian/tags.yaml

CMD ["python", "-m", "historian"]

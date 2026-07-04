# ChorusGraph MVP scenario benchmark (FL1–HC2) — Azure ACI image
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY chorusgraph ./chorusgraph
COPY benchmark ./benchmark
COPY tests ./tests

RUN pip install -U pip setuptools wheel \
    && pip install -e ".[dev,gemini,cortex,benchmark-healthcare]" \
    && pip install azure-storage-blob

COPY benchmark/azure/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md requirements-lock.txt ./
COPY chorusgraph ./chorusgraph
COPY benchmark ./benchmark

RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -e ".[dev,gemini,benchmark-healthcare,postgres]"

ENV CHORUSGRAPH_DETERMINISTIC=0
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health')" || exit 1

CMD ["python", "-c", "from chorusgraph.observability import start_health_server; start_health_server('0.0.0.0', 8080); import time; time.sleep(10**9)"]

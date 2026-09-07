# Multi-stage, non-root, no build toolchain in the runtime layer.
# See docs/18-deployment-and-operations.md #18.2.
#
# api, worker, and scheduler all use this SAME image with different
# commands (docs/03-system-architecture.md #3.3) -- that is deliberate: it
# eliminates the "works in the API, missing in the worker" bug class
# entirely. Select the process with `command:` in docker-compose.yml, not
# by building separate images.
FROM python:3.12-slim AS builder
WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runtime
RUN groupadd -r app && useradd -r -g app app \
 && apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        nodejs \
 && rm -rf /var/lib/apt/lists/*
COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY --chown=app:app . .
USER app
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

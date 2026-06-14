# ── base: shared runtime layer ────────────────────────────────────────────────
# Installs pinned runtime dependencies so Docker can cache this layer
# independently of source-code changes.
FROM python:3.11-slim AS base

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir --no-deps -e .

# Config is copied last — it changes more frequently than deps
COPY conf/ conf/

ENV PYTHONUNBUFFERED=1

# ── dev: base + dev tools (used for PR build validation) ─────────────────────
FROM base AS dev

COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

# ── main: production image (runs on GCP Dataproc) ────────────────────────────
# Secrets and env vars are injected at runtime — never embedded in the image.
FROM base AS main

CMD ["kedro", "run", "--env", "base"]

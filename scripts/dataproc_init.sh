#!/bin/bash
# Dataproc cluster initialization script.
# Runs on ALL nodes (master + workers) during cluster creation.
# Workers get a minimal install (pyarrow, pandas for UDFs).
# Master gets the full stack (kedro, transformers, snowflake, project source).
set -euxo pipefail

ROLE=$(curl -sf \
  "http://metadata.google.internal/computeMetadata/v1/instance/attributes/dataproc-role" \
  -H "Metadata-Flavor: Google") || { echo "[init] ERROR: failed to read dataproc-role from metadata"; exit 1; }

PROJECT=$(curl -sf \
  "http://metadata.google.internal/computeMetadata/v1/instance/attributes/GCP_PROJECT_ID" \
  -H "Metadata-Flavor: Google") || { echo "[init] ERROR: failed to read GCP_PROJECT_ID from metadata"; exit 1; }

BUCKET=$(curl -sf \
  "http://metadata.google.internal/computeMetadata/v1/instance/attributes/GCS_BUCKET" \
  -H "Metadata-Flavor: Google") || { echo "[init] ERROR: failed to read GCS_BUCKET from metadata"; exit 1; }

[[ -z "${ROLE}" ]]    && { echo "[init] ERROR: ROLE is empty"; exit 1; }
[[ -z "${PROJECT}" ]] && { echo "[init] ERROR: PROJECT is empty"; exit 1; }
[[ -z "${BUCKET}" ]]  && { echo "[init] ERROR: BUCKET is empty"; exit 1; }

echo "[init] Role=${ROLE}  Project=${PROJECT}  Bucket=${BUCKET}"

# ── All nodes: set PYSPARK_PYTHON so executors can import project packages ──────
PYTHON_BIN=$(which python3)
echo "PYSPARK_PYTHON=${PYTHON_BIN}"        >> /etc/environment
echo "PYSPARK_DRIVER_PYTHON=${PYTHON_BIN}" >> /etc/environment

# ── All nodes: minimal packages needed by Spark executors ──────────────────────
pip install --quiet --no-cache-dir \
  "pandas==2.2.3" \
  "pyarrow==17.0.0" \
  "python-json-logger==2.0.7"

echo "[init] Shared packages installed"

# ── Master only: full stack + project source ────────────────────────────────────
if [[ "${ROLE}" == "Master" ]]; then
  pip install --quiet --no-cache-dir \
    "kedro==1.0.0" \
    "kedro-datasets[spark,pandas.SQLTableDataset]==8.1.0" \
    "google-cloud-secret-manager==2.21.1" \
    "snowflake-sqlalchemy==1.6.1" \
    "snowflake-connector-python[pandas]==3.12.3" \
    "duckdb==1.1.3" \
    "duckdb-engine==0.14.0"

  echo "[init] Master packages installed"

  mkdir -p /app

  echo "[init] Downloading project source from GCS..."
  gsutil -m cp -r "gs://${BUCKET}/project/src"             /app/
  gsutil -m cp -r "gs://${BUCKET}/project/conf"            /app/
  gsutil    cp    "gs://${BUCKET}/project/pyproject.toml"  /app/
  gsutil    cp    "gs://${BUCKET}/scripts/dataproc_run.py" /app/

  pip install --quiet --no-cache-dir --no-deps -e /app

  # Persist env vars so they're available when kedro runs
  echo "KEDRO_ENV=base"            >> /etc/environment
  echo "GCP_PROJECT_ID=${PROJECT}" >> /etc/environment
  echo "GCS_BUCKET=${BUCKET}"      >> /etc/environment

  echo "[init] Project installed on master"
fi

echo "[init] Done"

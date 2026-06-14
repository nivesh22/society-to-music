"""
Entry point submitted to Dataproc as a PySpark job.

Submitted by the Cloud Workflow via:
  gcloud dataproc jobs submit pyspark gs://.../scripts/dataproc_run.py

The Spark driver calls `kedro run --env base` as a subprocess so that:
  - The existing SparkSession (created by spark-submit) is reused by Kedro's
    SparkHook via SparkSession.builder.getOrCreate()
  - All Kedro hooks, logging, and catalog resolution work normally
  - Exit code propagates back to Dataproc so the job is marked DONE or ERROR
"""

import logging
import os
import subprocess
import sys

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
)
logger = logging.getLogger("dataproc_run")

import urllib.request

def _metadata(path: str) -> str:
    """Fetch a value from the GCE instance metadata server."""
    req = urllib.request.Request(
        f"http://metadata.google.internal/computeMetadata/v1/{path}",
        headers={"Metadata-Flavor": "Google"},
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.read().decode()

# Ensure env vars are set before Kedro imports hooks.py at startup.
os.environ.setdefault("KEDRO_ENV", "base")
os.environ.setdefault("KEDRO_DISABLE_TELEMETRY", "1")
os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)

# GCP_PROJECT_ID and GCS_BUCKET are required by hooks.py at import time.
# spark.yarn.appMasterEnv.* doesn't reach the Python driver in client mode,
# so fetch them directly from the metadata server instead.
if not os.environ.get("GCP_PROJECT_ID"):
    os.environ["GCP_PROJECT_ID"] = _metadata("project/project-id")
if not os.environ.get("GCS_BUCKET"):
    os.environ["GCS_BUCKET"] = _metadata("instance/attributes/GCS_BUCKET")

project_dir = "/app"
os.chdir(project_dir)

logger.info("Starting Kedro pipeline | cwd=%s | python=%s", project_dir, sys.executable)

result = subprocess.run(
    [sys.executable, "-m", "kedro", "run", "--env", "base"],
    cwd=project_dir,
    env=os.environ.copy(),
)

if result.returncode != 0:
    logger.error("Kedro pipeline failed | returncode=%d", result.returncode)
else:
    logger.info("Kedro pipeline completed successfully")

sys.exit(result.returncode)

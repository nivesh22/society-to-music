"""Kedro hooks for GCP/Dataproc Spark integration and secrets management."""

import logging
import os
from typing import Any

from kedro.framework.hooks import hook_impl

logger = logging.getLogger(__name__)

_SNOWFLAKE_SECRETS = [
    "SNOWFLAKE_ACCOUNT",
    "SNOWFLAKE_USER",
    "SNOWFLAKE_PASSWORD",
    "SNOWFLAKE_WAREHOUSE",
    "SNOWFLAKE_ROLE",
    "SNOWFLAKE_DATABASE",
    "SNOWFLAKE_SCHEMA",
]


def _load_secrets_from_secret_manager() -> None:
    """Pull Snowflake secrets from GCP Secret Manager into os.environ.

    Called at module-import time (below) so env vars are populated before
    OmegaConfigLoader resolves ${oc.env:...} interpolations in credentials.yml.
    """
    from google.cloud import secretmanager  # noqa: PLC0415

    project_id = os.environ["GCP_PROJECT_ID"]
    client = secretmanager.SecretManagerServiceClient()

    for secret_name in _SNOWFLAKE_SECRETS:
        resource = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": resource})
        os.environ[secret_name] = response.payload.data.decode("UTF-8")
        logger.info("Secrets: loaded %s from Secret Manager", secret_name)


# Run immediately on import so env vars are set before Kedro loads credentials.yml.
# OmegaConfigLoader resolves ${oc.env:...} at config-load time, which happens after
# settings.py is imported — so this is the earliest safe point to inject secrets.
if os.getenv("KEDRO_ENV") == "base":
    _load_secrets_from_secret_manager()
else:
    logger.debug("Secrets: skipping Secret Manager — KEDRO_ENV is not 'base'")


_IS_GCP = os.getenv("KEDRO_ENV") == "base"


class SparkHook:
    """Initialises and tears down a SparkSession around every pipeline run.

    Environments:
    - Local dev (KEDRO_ENV != 'base'):
        Spark runs in local[*] mode without GCS or Snowflake connectors.
        The pipeline uses local parquet files and DuckDB.
    - GCP / Dataproc (KEDRO_ENV == 'base'):
        Reuses the SparkSession already created by Dataproc (getOrCreate).
        GCS and ADC are pre-configured by the Dataproc image — no manual setup needed.
    """

    def setup_logging(self) -> None:
        """Switch to JSON logging when running on GCP (KEDRO_ENV=base).

        Cloud Logging picks up structured JSON from stdout automatically —
        no extra agent or configuration needed.
        """
        import logging.config as _lc  # noqa: PLC0415

        kedro_env = os.getenv("KEDRO_ENV", "local")

        if kedro_env == "base":
            import yaml  # noqa: PLC0415

            with open("conf/base/logging_gcp.yml") as f:
                config = yaml.safe_load(f)
            _lc.dictConfig(config)
            logging.getLogger(__name__).info(
                "Logging initialised",
                extra={"environment": "gcp", "project": os.getenv("GCP_PROJECT_ID")},
            )
        else:
            logging.getLogger(__name__).info("Logging initialised | environment=local")

    @hook_impl
    def before_pipeline_run(self, run_params: dict[str, Any]) -> None:
        """Create (or reuse) a SparkSession before the pipeline starts."""
        self.setup_logging()

        from pyspark.sql import SparkSession  # noqa: PLC0415

        spark_master = os.getenv("SPARK_MASTER", "local[*]")

        if _IS_GCP:
            # On Dataproc the SparkSession is already initialised by the cluster
            # with GCS connector and ADC pre-configured. Just reuse it.
            logger.info("SparkHook: reusing Dataproc SparkSession (master=%s)", spark_master)
            builder = SparkSession.builder.appName("society-to-music")
        else:
            logger.info(
                "SparkHook: initialising SparkSession for local dev (master=%s)",
                spark_master,
            )
            builder = (
                SparkSession.builder.appName("society-to-music")
                .master(spark_master)
                .config("spark.sql.ansi.enabled", "false")
            )

        spark = builder.getOrCreate()
        logger.info(
            "SparkHook: SparkSession ready (version=%s, master=%s)",
            spark.version,
            spark.sparkContext.master,
        )

    @hook_impl
    def after_pipeline_run(self) -> None:
        """Stop the SparkSession cleanly after the pipeline finishes."""
        from pyspark.sql import SparkSession  # noqa: PLC0415

        active = SparkSession.getActiveSession()
        if active:
            logger.info("SparkHook: stopping SparkSession")
            active.stop()

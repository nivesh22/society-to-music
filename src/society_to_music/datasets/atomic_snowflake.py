"""Atomic Snowflake dataset using staging-table + SWAP pattern.

Guarantees that the live table is never in a partially-written state:

  1. Write the full DataFrame into TABLE_STAGING (replace = safe to retry).
  2. CREATE TABLE IF NOT EXISTS TABLE LIKE TABLE_STAGING  — handles first run.
  3. ALTER TABLE TABLE_STAGING SWAP WITH TABLE  — atomic metadata-only swap.
  4. DROP TABLE IF EXISTS TABLE_STAGING  — discard old data now in the staging slot.

The live table is updated atomically at step 3; readers see either the old
snapshot or the new one, never a half-written state.
"""

import logging
from typing import Any

import pandas as pd
from kedro.io import AbstractDataset
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)


class AtomicSnowflakeDataset(AbstractDataset):
    """Kedro dataset that writes to Snowflake atomically via staging + SWAP.

    Catalog entry (conf/base/catalog.yml):

        my_table:
          type: society_to_music.datasets.AtomicSnowflakeDataset
          table_name: MY_TABLE
          credentials: snowflake_credentials
          schema: CURATED          # optional, overrides URL default
          chunksize: 10000         # optional, rows per INSERT batch
    """

    def __init__(
        self,
        table_name: str,
        credentials: dict[str, Any],
        schema: str | None = None,
        chunksize: int = 10000,
    ) -> None:
        self._table_name = table_name.upper()
        self._staging = f"{self._table_name}_STAGING"
        self._credentials = credentials  # {"con": "snowflake://..."}
        self._schema = schema
        self._chunksize = chunksize
        # Fully-qualified names for DDL (schema.TABLE or just TABLE)
        prefix = f"{schema}." if schema else ""
        self._fq_live = f"{prefix}{self._table_name}"
        self._fq_staging = f"{prefix}{self._staging}"

    def _describe(self) -> dict[str, Any]:
        return {
            "table_name": self._fq_live,
            "staging": self._fq_staging,
        }

    def _load(self) -> pd.DataFrame:
        engine = create_engine(self._credentials["con"])
        try:
            return pd.read_sql(f"SELECT * FROM {self._fq_live}", engine)
        finally:
            engine.dispose()

    def _save(self, data: pd.DataFrame) -> None:
        engine = create_engine(self._credentials["con"])
        try:
            # ── Step 0: ensure the schema exists ─────────────────────────────────
            if self._schema:
                with engine.connect() as conn:
                    conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {self._schema}"))
                    conn.commit()

            # ── Step 1: write to staging (replaces any leftover from a failed run) ──
            logger.info(
                "AtomicSnowflake: writing %d rows to staging table %s",
                len(data),
                self._staging,
            )
            data.to_sql(
                self._staging,
                engine,
                schema=self._schema,
                if_exists="replace",
                index=False,
                chunksize=self._chunksize,
            )

            with engine.connect() as conn:
                # ── Step 2: ensure live table exists (first-run only) ──────────────
                conn.execute(
                    text(
                        f"CREATE TABLE IF NOT EXISTS {self._fq_live}"
                        f" LIKE {self._fq_staging}"
                    )
                )
                conn.commit()

                # ── Step 3: atomic swap — this is the single point of visibility ──
                logger.info(
                    "AtomicSnowflake: swapping %s → %s",
                    self._fq_staging,
                    self._fq_live,
                )
                conn.execute(
                    text(f"ALTER TABLE {self._fq_staging} SWAP WITH {self._fq_live}")
                )
                conn.commit()

                # ── Step 4: drop old data (now sitting in the staging slot) ────────
                conn.execute(text(f"DROP TABLE IF EXISTS {self._fq_staging}"))
                conn.commit()

            logger.info(
                "AtomicSnowflake: %s updated atomically (%d rows)",
                self._fq_live,
                len(data),
            )
        finally:
            engine.dispose()

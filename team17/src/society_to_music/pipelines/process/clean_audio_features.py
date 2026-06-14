import logging

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from society_to_music.utils.logging import log_node

logger = logging.getLogger(__name__)

@log_node
def clean_audio_features(raw_audio_features: DataFrame, feature_columns: dict) -> DataFrame:
    """
    Owner: Nisha

    Cleans the audio/emotion features dataset to one row per track_id.

    Steps:
      1 — Extract track_id from the Spotify URI (Uri column) or rename id column
      2 — Select relevant feature columns (audio + NRC + LDA)
      2 — Deduplicate to one row per track_id
      3 — Flag rows that have NRC scores (is_scored)

    Output columns:
      track_id                              — join key
      valence, energy, danceability,
        acousticness, liveness, tempo       — audio features
      anger_norm2 … trust_norm2            — NRC emotion scores (if present)
      Celebrate … Thug                     — LDA topic scores (if present)
      is_scored                             — True if this track has NRC scores
    """
    audio_cols = feature_columns["audio"]
    tempo_col = feature_columns["tempo"]
    nrc_cols = feature_columns["nrc"]
    lda_cols = feature_columns["lda"]

    df = raw_audio_features

    # Extract track_id from Spotify URI or id column
    if "Uri" in df.columns:
        df = df.withColumn(
            "track_id",
            F.element_at(F.split(F.col("Uri"), "/"), -1),
        )
    elif "id" in df.columns:
        df = df.withColumnRenamed("id", "track_id")

    # Select only the columns we need — skip any that aren't present in this dataset
    all_wanted = ["track_id"] + audio_cols + [tempo_col] + nrc_cols + lda_cols
    cols_present = [c for c in all_wanted if c in df.columns]
    cols_missing = [c for c in all_wanted if c not in df.columns]

    if cols_missing:
        logger.info("clean_audio_features: columns not in source (skipped): %s", cols_missing)

    df = df.select(*cols_present)

    # Cast all numeric feature columns to DOUBLE (inferSchema may read them as STRING)
    numeric_cols = [c for c in audio_cols + [tempo_col] + nrc_cols + lda_cols if c in df.columns]
    for c in numeric_cols:
        df = df.withColumn(c, F.col(c).cast("double"))

    # Deduplicate — one row per track_id (audio/NRC/LDA are song-level, not country-level)
    df = df.dropDuplicates(["track_id"])

    # Flag rows that have NRC emotion scores
    nrc_proxy = next((c for c in nrc_cols if c in df.columns), None)
    if nrc_proxy:
        df = df.withColumn("is_scored", F.col(nrc_proxy).isNotNull())
    else:
        df = df.withColumn("is_scored", F.lit(False))
        logger.info("clean_audio_features: no NRC columns found — is_scored set to False")

    return df

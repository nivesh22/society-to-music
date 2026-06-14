import logging

import pandas as pd
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql import Window

from society_to_music.utils.logging import log_node

logger = logging.getLogger(__name__)

@log_node
def join_and_aggregate(
    clean_charts: DataFrame,
    clean_emotions: DataFrame,
    coverage_ok: float,
    coverage_low: float,
    feature_columns: dict,
) -> pd.DataFrame:
    """
    Owner: Nisha

    Join cleaned charts with cleaned emotions, then aggregate to one row
    per (date, country) — the final curated_music_features table.

    Steps:
      3 — LEFT join charts ← emotions on track_id
      5 — Compute emotion_coverage per (date, country):
            scored streams / total streams
      6 — Weighted-average aggregation → two output signals:
            o2_*: audio features, NRC-scored songs only
            o3_*: NRC emotions + LDA topics, scored songs only
      7 — Assign coverage_flag: OK / LOW_COVERAGE / VERY_LOW

    Output columns:
      date, country                              — identifiers
      total_streams, track_count,
        scored_track_count, emotion_coverage,
        coverage_flag                            — quality / coverage metadata
      o2_{audio}_*                               — audio feature averages (scored songs only)
      o3_{emotion}*, o3_{lda_topic}*            — NRC + LDA aggregates (scored songs only)
    """
    audio_cols = feature_columns["audio"]
    tempo_col = feature_columns["tempo"]
    nrc_cols = feature_columns["nrc"]
    lda_cols = feature_columns["lda"]

    # LEFT join: every charting song is kept; songs without emotion data get nulls
    df = clean_charts.join(clean_emotions, on="track_id", how="left")

    # emotion_coverage per (date, country): scored streams / total streams
    scored_streams_expr = F.when(F.col("is_scored"), F.col("streams")).otherwise(0)
    window_dc = Window.partitionBy("date", "country")

    df = df.withColumn(
        "emotion_coverage",
        F.sum(scored_streams_expr).over(window_dc) / F.sum(F.col("streams")).over(window_dc),
    )

    # Build aggregation expressions
    agg_exprs = [
        F.sum("streams").alias("total_streams"),
        F.count("*").alias("track_count"),
        F.sum(F.col("is_scored").cast("long")).alias("scored_track_count"),
        F.first("emotion_coverage").alias("emotion_coverage"),
    ]

    audio_present = [c for c in audio_cols if c in df.columns]
    nrc_present   = [c for c in nrc_cols   if c in df.columns]
    lda_present   = [c for c in lda_cols   if c in df.columns]

    # OUTPUT 2: audio features — NRC-scored songs only, streams-weighted
    for col in audio_present:
        agg_exprs.append(
            (
                F.sum(F.when(F.col(col).isNotNull() & F.col("is_scored"), F.col(col) * F.col("weight")))
                / F.sum(F.when(F.col(col).isNotNull() & F.col("is_scored"), F.col("weight")))
            ).alias(f"o2_{col}")
        )
    if tempo_col in df.columns:
        agg_exprs.append(
            F.avg(F.when(F.col("is_scored"), F.col(tempo_col))).alias("o2_tempo")
        )

    # OUTPUT 3: NRC emotions — scored songs only (strip _norm2 suffix)
    for col in nrc_present:
        clean_name = col.replace("_norm2", "")
        agg_exprs.append(
            (
                F.sum(F.when(F.col(col).isNotNull() & F.col("is_scored"), F.col(col) * F.col("weight")))
                / F.sum(F.when(F.col(col).isNotNull() & F.col("is_scored"), F.col("weight")))
            ).alias(f"o3_{clean_name}")
        )

    # OUTPUT 3: LDA topics — scored songs only (lowercase)
    for col in lda_present:
        agg_exprs.append(
            (
                F.sum(F.when(F.col(col).isNotNull() & F.col("is_scored"), F.col(col) * F.col("weight")))
                / F.sum(F.when(F.col(col).isNotNull() & F.col("is_scored"), F.col("weight")))
            ).alias(f"o3_{col.lower()}")
        )

    daily = df.groupBy("date", "country").agg(*agg_exprs)

    # Coverage flag
    coverage_flag_expr = (
        F.when(F.col("emotion_coverage").isNull(),              "UNKNOWN")
        .when(F.col("emotion_coverage") >= coverage_ok,         "OK")
        .when(F.col("emotion_coverage") >= coverage_low,        "LOW_COVERAGE")
        .otherwise("VERY_LOW")
    )
    daily = daily.withColumn("coverage_flag", coverage_flag_expr)

    # Final column order
    o2_cols = [c for c in daily.columns if c.startswith("o2_")]
    o3_cols = [c for c in daily.columns if c.startswith("o3_")]
    final_order = [
        "date", "country",
        "total_streams", "track_count", "scored_track_count",
        "emotion_coverage", "coverage_flag",
    ] + o2_cols + o3_cols
    final_order = [c for c in final_order if c in daily.columns]

    return daily.select(*final_order).orderBy("country", "date").toPandas()

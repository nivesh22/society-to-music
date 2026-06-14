import logging

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from society_to_music.utils.logging import log_node

logger = logging.getLogger(__name__)


@log_node
def clean_spotify(
    raw_spotify_charts: DataFrame,
    target_regions: list[str],
    start_date: str,
    end_date: str,
    chart_type: str,
    trend_weights: dict,
) -> DataFrame:
    """
    Owner: Nisha

    Cleans raw Spotify charts data and computes per-row weights.

    Steps:
      1 — Extract track_id from the full Spotify URL
      1 — Parse date to yyyy-MM-dd
      2 — Filter: target chart type, target regions, project date range
      3 — Rename region → country
      4 — Compute trend_weight and weight = streams × trend_weight

    Output columns (song-level rows, not yet aggregated):
      track_id, date, country, streams, trend, trend_weight, weight
    """
    df = raw_spotify_charts

    # Extract track_id from full Spotify URL
    # e.g. 'https://open.spotify.com/track/6mICuAdrwEjh6Y6lroV2Kg' → last segment
    df = df.withColumn(
        "track_id",
        F.element_at(F.split(F.col("url"), "/"), -1),
    )

    # Normalise date → yyyy-MM-dd
    df = df.withColumn(
        "date",
        F.date_format(F.to_date(F.col("date")), "yyyy-MM-dd"),
    )

    # Scope filters: chart type, null keys, target regions, date range
    df = (
        df
        .filter(F.col("chart") == chart_type)
        .filter(F.col("date").isNotNull() & F.col("region").isNotNull())
        .filter(F.col("region").isin(target_regions))
        .filter((F.col("date") >= start_date) & (F.col("date") <= end_date))
    )

    df = df.withColumnRenamed("region", "country")

    # Trend weight — unrecognised trend values default to 1.0 (neutral)
    trend_expr = (
        F.when(F.col("trend") == "MOVE_UP",       float(trend_weights["MOVE_UP"]))
        .when(F.col("trend") == "SAME_POSITION",  float(trend_weights["SAME_POSITION"]))
        .when(F.col("trend") == "MOVE_DOWN",      float(trend_weights["MOVE_DOWN"]))
        .otherwise(1.0)
    )
    df = df.withColumn("trend_weight", trend_expr)
    df = df.withColumn("weight", F.col("streams") * F.col("trend_weight"))

    return df.select(
        "track_id",
        "date",
        "country",
        "streams",
        "trend",
        "trend_weight",
        "weight",
    )

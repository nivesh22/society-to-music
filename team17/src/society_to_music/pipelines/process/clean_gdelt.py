import logging

import pandas as pd
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from society_to_music.utils.logging import log_node

logger = logging.getLogger(__name__)


@log_node
def clean_gdelt(
    raw_gdelt: DataFrame,
    target_regions: list[str],
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """
    Owner: Shivathmika

    Cleans the BigQuery-exported daily GDELT dataset while preserving all
    columns from the CSV.

    Expected input columns include:
      - date
      - country_name
      - article_count
      - avg_tone_score
      - avg_tone_positive / avg_tone_negative
      - avg_emotion_* (anger, fear, sadness, joy, surprise, disgust,
                       trust, volatility, distribution, anxiety,
                       positive, negative)

    Output:
      Same columns, except:
      - country_name is renamed to country
      - date is standardized to yyyy-MM-dd
      - filtered to target_regions and project date range
      - duplicates on (date, country) removed
    """
    df = raw_gdelt

    if "country_name" in df.columns:
        df = df.withColumnRenamed("country_name", "country")

    df = df.withColumn("date", F.date_format(F.col("date"), "yyyy-MM-dd"))

    df = df.filter(F.col("date").isNotNull() & F.col("country").isNotNull())
    df = df.filter(F.col("country").isin(target_regions))
    df = df.filter((F.col("date") >= start_date) & (F.col("date") <= end_date))

    df = df.dropDuplicates(["date", "country"])

    return df.toPandas()

"""Tests for clean_gdelt node (Owner: Shivathmika).

These tests verify the node contract — correct input/output types and schema.
Shivathmika should add more tests here when implementing the cleaning logic.
"""

from pyspark.sql import DataFrame

from society_to_music.pipelines.process.clean_gdelt import clean_gdelt


def test_clean_gdelt_returns_spark_dataframe(spark):
    """Node must return a Spark DataFrame, not pandas."""
    raw = spark.createDataFrame(
        [
            {
                "date": "2020-01-01",
                "country": "US",
                "tone": 1.5,
                "tone_pos": 0.8,
                "tone_neg": 0.2,
            }
        ]
    )
    result = clean_gdelt(raw)
    assert isinstance(result, DataFrame)


def test_clean_gdelt_does_not_crash_on_empty_input(spark):
    """Node must handle an empty DataFrame without raising an error."""
    empty = spark.createDataFrame(
        [], "date STRING, country STRING, tone DOUBLE, tone_pos DOUBLE, tone_neg DOUBLE"
    )
    result = clean_gdelt(empty)
    assert isinstance(result, DataFrame)

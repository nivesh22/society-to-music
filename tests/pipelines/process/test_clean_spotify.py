"""Tests for clean_spotify node (Owner: Bhavika).

These tests verify the node contract — correct input/output types and schema.
Bhavika should add more tests here when implementing the join and aggregation logic.
"""

from pyspark.sql import DataFrame

from society_to_music.pipelines.process.clean_spotify import clean_spotify


def test_clean_spotify_returns_spark_dataframe(spark):
    """Node must return a Spark DataFrame, not pandas."""
    charts = spark.createDataFrame(
        [
            {
                "track_id": "abc123",
                "date": "2020-01-01",
                "country": "US",
                "streams": 100000,
            }
        ]
    )
    features = spark.createDataFrame(
        [
            {
                "track_id": "abc123",
                "valence": 0.7,
                "energy": 0.8,
                "danceability": 0.6,
                "tempo": 120.0,
            }
        ]
    )
    result = clean_spotify(charts, features)
    assert isinstance(result, DataFrame)


def test_clean_spotify_does_not_crash_on_empty_charts(spark):
    """Node must handle empty charts DataFrame without raising an error."""
    empty_charts = spark.createDataFrame(
        [], "track_id STRING, date STRING, country STRING, streams LONG"
    )
    features = spark.createDataFrame(
        [
            {
                "track_id": "abc123",
                "valence": 0.7,
                "energy": 0.8,
                "danceability": 0.6,
                "tempo": 120.0,
            }
        ]
    )
    result = clean_spotify(empty_charts, features)
    assert isinstance(result, DataFrame)

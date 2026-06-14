"""Shared pytest fixtures for all tests."""

import pytest
from pyspark.sql import SparkSession


@pytest.fixture(scope="session")
def spark():
    """Create a single SparkSession shared across all tests in the session.

    Using local[1] (single thread) keeps tests fast and deterministic.
    The session is stopped automatically after all tests finish.
    """
    session = (
        SparkSession.builder.appName("test-society-to-music")
        .master("local[1]")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "1")
        .getOrCreate()
    )
    yield session
    session.stop()

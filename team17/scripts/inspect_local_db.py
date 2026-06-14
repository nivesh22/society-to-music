"""Inspect the local DuckDB database after running the pipeline locally."""

import duckdb

conn = duckdb.connect("data/local.db")

print("\n=== Tables ===")
print(conn.execute("SHOW TABLES").fetchdf())

print("\n=== NEWS_SENTIMENT (first 5 rows) ===")
try:
    print(conn.execute("SELECT * FROM news_sentiment LIMIT 5").fetchdf())
except Exception:
    print("Table not yet populated — run `kedro run` first.")

print("\n=== MUSIC_FEATURES (first 5 rows) ===")
try:
    print(conn.execute("SELECT * FROM music_features LIMIT 5").fetchdf())
except Exception:
    print("Table not yet populated — run `kedro run` first.")

print("\n=== LYRICS_EMOTIONS (first 5 rows) ===")
try:
    print(conn.execute("SELECT * FROM lyrics_emotions LIMIT 5").fetchdf())
except Exception:
    print("Table not yet populated — run `kedro run` first.")

conn.close()

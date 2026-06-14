"""Upload music.csv and news.csv from dist/data/ to Snowflake."""
import pandas as pd
from pathlib import Path
from snowflake_connection import get_connection
from snowflake.connector.pandas_tools import write_pandas

DATA_DIR = Path(__file__).parent.parent / "dist" / "data"

def upload(conn, csv_file: Path, table_name: str):
    print(f"Loading {csv_file.name}...")
    df = pd.read_csv(csv_file)
    df.columns = [c.upper().replace(" ", "_") for c in df.columns]
    print(f"  {len(df)} rows, {len(df.columns)} columns → {table_name}")
    success, _, nrows, _ = write_pandas(
        conn=conn,
        df=df,
        table_name=table_name,
        auto_create_table=True,
        overwrite=True,
    )
    print(f"  {'✓' if success else '✗'} {nrows} rows written to {table_name}")

def main():
    conn = get_connection()
    try:
        upload(conn, DATA_DIR / "music.csv", "MUSIC_FEATURES")
        upload(conn, DATA_DIR / "news.csv",  "NEWS_SENTIMENT")
    finally:
        conn.close()

if __name__ == "__main__":
    main()

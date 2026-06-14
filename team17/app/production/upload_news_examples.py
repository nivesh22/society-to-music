import pandas as pd
from snowflake_connection import get_connection
from snowflake.connector.pandas_tools import write_pandas

from pathlib import Path

def main():
    # 1. Load the CSV
    csv_path = Path(__file__).parent / "News_examples.csv"
    print(f"Loading data from {csv_path}...")
    df = pd.read_csv(csv_path)

    # 3. Clean up column names for Snowflake
    # Snowflake prefers uppercase column names and underscores instead of spaces.
    df.columns = [col.upper().replace(' ', '_') for col in df.columns]
    
    table_name = "NEWS_EXAMPLES"

    print("Connecting to Snowflake...")
    conn = get_connection()
    try:
        print(f"Uploading {len(df)} rows to table {table_name}...")
        success, nchunks, nrows, _ = write_pandas(
            conn=conn,
            df=df,
            table_name=table_name,
            auto_create_table=True,
            overwrite=True # In case we run it multiple times
        )

        if success:
            print(f"Successfully uploaded {nrows} rows to {table_name}!")
        else:
            print(f"Failed to upload data to {table_name}.")

    finally:
        conn.close()

if __name__ == "__main__":
    main()

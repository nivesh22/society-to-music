import pandas as pd
from snowflake_connection import get_connection
from snowflake.connector.pandas_tools import write_pandas

from pathlib import Path

def main():
    # 1. Load the CSV
    csv_path = Path(__file__).parent / "top_10_songs_features.csv"
    print(f"Loading data from {csv_path}...")
    df = pd.read_csv(csv_path)

    # 2. Subset to only the requested columns
    df = df[['Feature', 'Rank', 'Title', 'Artist']]

    # 3. Clean up column names for Snowflake
    # Snowflake prefers uppercase column names without spaces.
    df.columns = [col.upper() for col in df.columns]
    
    table_name = "TOP_10_SONGS"

    print("Connecting to Snowflake...")
    conn = get_connection()
    try:
        # Create table first to ensure schema matches, but write_pandas has auto_create_table=True
        # Let's ensure the table exists or we auto-create it
        
        # It's better to explicitly create the table if we want a clean schema, but write_pandas with auto_create_table is easier.
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

import os
import snowflake.connector
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

def download_data():
    # Load environment variables from .env
    load_dotenv()
    
    # Ensure data directory exists
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    print("Connecting to Snowflake...")
    try:
        conn = snowflake.connector.connect(
            account=os.environ["SNOWFLAKE_ACCOUNT"],
            user=os.environ["SNOWFLAKE_USER"],
            password=os.environ["SNOWFLAKE_PASSWORD"],
            warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
            database=os.environ["SNOWFLAKE_DATABASE"],
            schema=os.environ["SNOWFLAKE_SCHEMA"],
            role=os.environ["SNOWFLAKE_ROLE"],
        )
        cur = conn.cursor()

        for table in ["NEWS_SENTIMENT", "MUSIC_FEATURES"]:
            print(f"Downloading {table}...")
            cur.execute(f"SELECT * FROM {table}")
            df = pd.DataFrame(cur.fetchall(), columns=[d[0] for d in cur.description])
            
            output_file = data_dir / f"{table.lower()}_export.csv"
            df.to_csv(output_file, index=False)
            print(f"Saved {table} to {output_file} ({len(df)} rows)")

        conn.close()
        print("Done!")
    except Exception as e:
        print(f"Error: {e}")
        exit(1)

if __name__ == "__main__":
    download_data()

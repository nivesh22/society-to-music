import pandas as pd
from snowflake_connection import get_connection
from snowflake.connector.pandas_tools import write_pandas

def fetch_table_to_df(conn, table_name: str) -> pd.DataFrame:
    """Fetch an entire table from Snowflake into a Pandas DataFrame."""
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {table_name}")
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    df = pd.DataFrame(rows, columns=columns)
    
    # Convert DATE to datetime for a cleaner join
    if 'DATE' in df.columns:
        df['DATE'] = pd.to_datetime(df['DATE'])
        
    cur.close()
    return df

def main():
    conn = get_connection()
    try:
        # Load both tables into DataFrames
        df_music = fetch_table_to_df(conn, "MUSIC_FEATURES")
        df_news = fetch_table_to_df(conn, "NEWS_SENTIMENT")
        
        
        # Normalize types for join keys
        df_music['COUNTRY'] = df_music['COUNTRY'].astype(str)
        df_news['COUNTRY'] = df_news['COUNTRY'].astype(str)
        
        # Join dataframes on COUNTRY and DATE
        joined_df = pd.merge(
            df_music, 
            df_news, 
            on=['COUNTRY', 'DATE'], 
            how='inner'
        )
        
        
        # Get numeric columns but exclude TOTAL_STREAMS and ARTICLE_COUNT
        exclude_cols = {'TOTAL_STREAMS', 'ARTICLE_COUNT', 'DATE', 'COUNTRY'}
        numeric_cols = joined_df.select_dtypes(include=['number']).columns
        cols_to_normalize = [c for c in numeric_cols if c not in exclude_cols]
        
        for col in cols_to_normalize:
            joined_df[f"{col}_ZSCORE"] = joined_df.groupby('COUNTRY')[col].transform(
                lambda x: (x - x.mean()) / x.std() if x.std() > 0 else 0.0
            )
                
        
        
        # Format Snowflake column names reliably (must be upper string)
        joined_df.columns = [str(c).upper() for c in joined_df.columns]
        
        success, nchunks, nrows, _ = write_pandas(
            conn, 
            joined_df, 
            table_name="MUSIC_NEWS_JOINED", 
            auto_create_table=True,
            overwrite=True
        )
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()

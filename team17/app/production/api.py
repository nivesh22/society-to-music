import os
import uvicorn
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import math
import numpy as np
from production.snowflake_connection import get_connection

app = FastAPI(title="Music & News API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mapping UI News Feature to DB Feature Name (ZSCORE)
NEWS_MAP = {
    'Positive Tone': 'AVG_TONE_POSITIVE_ZSCORE',
    'General Tone': 'AVG_TONE_SCORE_ZSCORE',
    'Negative Tone': 'AVG_TONE_NEGATIVE_ZSCORE',
    'Negative Emotion': 'AVG_EMOTION_NEGATIVE_ZSCORE',
    'Positive Emotion': 'AVG_EMOTION_POSITIVE_ZSCORE'
}

# Mapping UI Music Feature to DB Feature Name (ZSCORE)
MUSIC_MAP = {
    'Valence': 'O2_VALENCE_ZSCORE',
    'Energy': 'O2_ENERGY_ZSCORE',
    'Danceability': 'O2_DANCEABILITY_ZSCORE',
    'Acoustics': 'O2_ACOUSTICS_ZSCORE',
    'Tempo': 'O2_TEMPO_ZSCORE',
    'Liveliness': 'O2_LIVELINESS_ZSCORE',
    'Trust': 'O3_TRUST_ZSCORE',
    'Anger': 'O3_ANGER_ZSCORE',
    'Anticipation': 'O3_ANTICIPATION_ZSCORE',
    'Celebrate': 'O3_CELEBRATE_ZSCORE',
    'Fun': 'O3_FUN_ZSCORE',
    'Nostalgia': 'O3_NOSTALGIA_ZSCORE',
    'Explore': 'O3_EXPLORE_ZSCORE',
    'Desire': 'O3_DESIRE_ZSCORE',
    'Love': 'O3_LOVE_ZSCORE',
    'Sadness': 'O3_SADNESS_ZSCORE',
    'Thug': 'O3_THUG_ZSCORE',
    'Fear': 'O3_FEAR_ZSCORE',
    'Disgust': 'O3_DISGUST_ZSCORE',
    'Surprise': 'O3_SURPRISE_ZSCORE',
    'Hope': 'O3_HOPE_ZSCORE',
    'Joy': 'O3_JOY_ZSCORE'
}

# Mapping Lag/Rolling UI strings to OLAP lag_type values
# UI combinations: Lag Window: '0d (Live)', '1d', '2d', '3d', '7d'
# For the api we need to know what OLAP label to use if applicable
LAG_MAP = {
    '0d (Live)': 'Simultaneous',
    '1d': 'Speech_Lag_1', # wait, what did the correlation script call it? News_Lag_1 and Music_Lag_1
    '2d': 'News_Lag_2'
}

# Note: The rolling effect OLAP values:
# 'News_Roll_3d', 'News_Roll_1w', 'News_Roll_2w', 'News_Roll_1m'

def fetch_table(query: str) -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql(query, conn)
    finally:
        conn.close()

# Keep DataFrames in memory so API is fast
print("Loading data from Snowflake...")
try:
    # Fetch all ZSCORE columns to ensure we have everything mapped in NEWS_MAP and MUSIC_MAP
    df_joined = fetch_table("SELECT * FROM MUSIC_NEWS_JOINED")
    df_joined['DATE'] = pd.to_datetime(df_joined['DATE'])
    df_joined = df_joined.sort_values('DATE')
    
    df_olap = fetch_table("SELECT * FROM FEATURE_CORRELATIONS_OLAP")
    print("Data loaded successfully.")
except Exception as e:
    print(f"Error loading initial data: {e}")
    df_joined = pd.DataFrame()
    df_olap = pd.DataFrame()

@app.get("/api/time_series")
def get_time_series(
    country: str = 'All Regions',
    news_feature: str = 'Positive Emotion',
    music_feature: str = 'Valence',
    lag: str = '0d (Live)',
    rolling_window: str = 'None'
):
    filt_df = df_joined.copy()
    if country != 'All Regions':
        filt_df = filt_df[filt_df['COUNTRY'] == country]
    else:
        # Group by date and mean
        filt_df = filt_df.groupby('DATE').mean(numeric_only=True).reset_index()

    n_col = NEWS_MAP.get(news_feature, 'AVG_EMOTION_POSITIVE_ZSCORE')
    m_col = MUSIC_MAP.get(music_feature, 'O2_VALENCE_ZSCORE')

    # Apply rolling
    if rolling_window == '3d Rolling':
        filt_df[n_col] = filt_df[n_col].rolling(window=3, min_periods=1).mean()
    elif rolling_window == '1w Rolling':
        filt_df[n_col] = filt_df[n_col].rolling(window=7, min_periods=1).mean()
    elif rolling_window == '2w Rolling':
        filt_df[n_col] = filt_df[n_col].rolling(window=14, min_periods=1).mean()
    elif rolling_window == '1m Rolling':
        filt_df[n_col] = filt_df[n_col].rolling(window=30, min_periods=1).mean()

    # Apply lag
    if 'News Lag' in lag:
        shift_val = int(lag.split('d')[0])
        filt_df[n_col] = filt_df[n_col].shift(shift_val)
    elif 'Music Lag' in lag:
        shift_val = int(lag.split('d')[0])
        filt_df[m_col] = filt_df[m_col].shift(shift_val)
    
    filt_df = filt_df.dropna(subset=[n_col, m_col, 'DATE'])
    
    # Send ~30 evenly spaced points or downsample to keep it responsive/clean for the frontend
    # Since we have maybe 1000 days, let's take a 30-day moving average or just take 100 points
    
    # Actually, we can just return the raw array up to say 100 points
    # or let's downsample
    if len(filt_df) > 100:
        # Sample every Nth row to get exactly ~100 rows
        n = len(filt_df) // 100
        filt_df = filt_df.iloc[::n, :]

    result = []
    for _, row in filt_df.iterrows():
        result.append({
            "date": str(row['DATE'].date()),
            "newsSentiment": float(row[n_col]),
            "musicFeature": float(row[m_col])
        })
    return result

def clean_name(s: str) -> str:
    s = str(s)
    s = s.replace('_ZSCORE', '')
    if s.startswith('O2_'): s = s[3:]
    if s.startswith('O3_'): s = s[3:]
    if s.startswith('AVG_EMOTION_'): s = s[12:]
    if s.startswith('AVG_TONE_'): s = s[9:]
    return s.replace('_', ' ').title().strip()

@app.get("/api/correlations_top")
def get_correlations_top(
    country: str = 'All Regions',
    news_feature: str = 'Positive Emotion',
):
    db_n_feat = NEWS_MAP.get(news_feature, 'AVG_EMOTION_POSITIVE_ZSCORE').replace('_ZSCORE', '')
    
    if df_olap.empty: return {"pos": [], "neg": []}

    df = df_olap.copy()
    if country != 'All Regions':
        df = df[df['COUNTRY'] == country]
    df = df[df['NEWS_FEATURE'] == db_n_feat]
    
    if df.empty: return {"pos": [], "neg": []}
    
    # Group by music feature to average the correlations if 'All Regions'
    if country == 'All Regions':
         df = df.groupby(['MUSIC_FEATURE']).mean(numeric_only=True).reset_index()

    # Sort by positive
    pos_df = df.sort_values(by='SIMULTANEOUS_CORRELATION', ascending=False).head(5)
    neg_df = df.sort_values(by='SIMULTANEOUS_CORRELATION', ascending=True).head(5)

    def to_list(dff):
        res = []
        for _, r in dff.iterrows():
            c_val = r['SIMULTANEOUS_CORRELATION']
            c_val = c_val if pd.notna(c_val) else 0.0
            p_str = '< 0.001'
            if 'SIMULTANEOUS_P_VALUE_HAC' in r:
                p_val = r['SIMULTANEOUS_P_VALUE_HAC']
                if pd.notna(p_val) and p_val >= 0.001:
                    p_str = f"{p_val:.3f}"
            res.append({
                "name": clean_name(r['MUSIC_FEATURE']),
                "val": float(c_val),
                "pval": str(p_str)
            })
        return res

    return {
         "pos": to_list(pos_df),
         "neg": to_list(neg_df)
    }

@app.get("/api/lag_effect")
def get_lag_effect(
    country: str = 'All Regions',
    news_feature: str = 'Positive Emotion',
    music_feature: str = 'Valence'
):
    db_n_feat = NEWS_MAP.get(news_feature, 'AVG_EMOTION_POSITIVE_ZSCORE').replace('_ZSCORE', '')
    db_m_feat = MUSIC_MAP.get(music_feature, 'O2_VALENCE_ZSCORE').replace('_ZSCORE', '')
    
    if df_olap.empty: return []

    df = df_olap[(df_olap['NEWS_FEATURE'] == db_n_feat) & (df_olap['MUSIC_FEATURE'] == db_m_feat)]
    if country != 'All Regions':
        df = df[df['COUNTRY'] == country]

    if df.empty: return []
    if country == 'All Regions':
        df = df.mean(numeric_only=True).to_frame().T

    row = df.iloc[0]
    
    # Mapping the lag columns
    lags = [
        {"lag": "-2d", "col": "NEWS_LAG_2_CORRELATION"},
        {"lag": "-1d", "col": "NEWS_LAG_1_CORRELATION"},
        {"lag": "0d (Live)", "col": "SIMULTANEOUS_CORRELATION"},
        {"lag": "+1d", "col": "MUSIC_LAG_1_CORRELATION"},
        {"lag": "+2d", "col": "MUSIC_LAG_2_CORRELATION"}
    ]
    
    res = []
    for l in lags:
        val = row.get(l['col'], 0.0)
        res.append({"lag": l['lag'], "val": float(val) if pd.notna(val) else 0.0})
    return res

@app.get("/api/rolling_effect")
def get_rolling_effect(
    country: str = 'All Regions',
    news_feature: str = 'Positive Emotion',
    music_feature: str = 'Valence'
):
    db_n_feat = NEWS_MAP.get(news_feature, 'AVG_EMOTION_POSITIVE_ZSCORE').replace('_ZSCORE', '')
    db_m_feat = MUSIC_MAP.get(music_feature, 'O2_VALENCE_ZSCORE').replace('_ZSCORE', '')

    if df_olap.empty: return []

    df = df_olap[(df_olap['NEWS_FEATURE'] == db_n_feat) & (df_olap['MUSIC_FEATURE'] == db_m_feat)]
    if country != 'All Regions':
        df = df[df['COUNTRY'] == country]
        
    if df.empty: return []
    if country == 'All Regions':
        df = df.mean(numeric_only=True).to_frame().T
        
    row = df.iloc[0]
    
    periods = [
        {"period": "None", "col": "SIMULTANEOUS_CORRELATION"},
        {"period": "3d", "col": "NEWS_ROLL_3D_CORRELATION"},
        {"period": "1w", "col": "NEWS_ROLL_1W_CORRELATION"},
        {"period": "2w", "col": "NEWS_ROLL_2W_CORRELATION"},
        {"period": "1m", "col": "NEWS_ROLL_1M_CORRELATION"}
    ]
    
    res = []
    for p in periods:
        val = row.get(p['col'], 0.0)
        res.append({"period": p['period'], "corr": float(val) if pd.notna(val) else 0.0})
    return res

@app.get("/api/country_comparisons")
def get_country_comparisons(
    news_feature: str = 'Positive Emotion',
    music_feature: str = 'Valence'
):
    db_n_feat = NEWS_MAP.get(news_feature, 'AVG_EMOTION_POSITIVE_ZSCORE').replace('_ZSCORE', '')
    db_m_feat = MUSIC_MAP.get(music_feature, 'O2_VALENCE_ZSCORE').replace('_ZSCORE', '')
    
    if df_olap.empty: return []

    df = df_olap[(df_olap['NEWS_FEATURE'] == db_n_feat) & (df_olap['MUSIC_FEATURE'] == db_m_feat)]
    if df.empty: return []
    
    res = []
    for _, r in df.iterrows():
        chk = r['SIMULTANEOUS_CORRELATION']
        val = float(chk) if pd.notna(chk) else 0.0
        res.append({
            "name": r['COUNTRY'],
            "corr": val
        })
    res = sorted(res, key=lambda x: abs(x['corr']), reverse=True)
    return res

@app.get("/api/top_songs")
def get_top_songs(music_feature: str = 'Valence'):
    try:
        db_m_feat = MUSIC_MAP.get(music_feature, 'O2_VALENCE_ZSCORE')
        feature_name = clean_name(db_m_feat).lower()
        
        # Handle emotions that have _norm suffix in TOP_10_SONGS
        emotions = ['anger', 'anticipation', 'disgust', 'fear', 'joy', 'sadness', 'surprise', 'trust', 'positive', 'negative']
        if feature_name in emotions:
            feature_name = f"{feature_name}_norm"

        query = f"""
            SELECT RANK, TITLE, ARTIST 
            FROM TOP_10_SONGS 
            WHERE LOWER(FEATURE) = '{feature_name}'
            ORDER BY RANK ASC
        """
        df = fetch_table(query)
        if df.empty: return []
        res = []
        for _, row in df.iterrows():
            res.append({
                "rank": int(row['RANK']),
                "track": str(row['TITLE']),
                "artist": str(row['ARTIST'])
            })
        return res
    except Exception as e:
        print(f"Error fetching top songs: {e}")
        return []

@app.get("/api/news_examples")
def get_news_examples(news_feature: str = 'General Tone'):
    try:
        if news_feature == 'General Tone':
            condition = "TOP_5 = 'Yes'"
            score_col = "AVG_TONE"
        elif news_feature == 'Positive Emotion':
            condition = "HAPPY = 'Yes'"
            score_col = "EMOTION"
        elif news_feature == 'Positive Tone':
            condition = "HAPPY = 'Yes'"
            score_col = "TONE"
        elif news_feature == 'Negative Emotion':
            condition = "HAPPY = 'No'"
            score_col = "EMOTION"
        elif news_feature == 'Negative Tone':
            condition = "HAPPY = 'No'"
            score_col = "TONE"
        else:
            condition = "TOP_5 = 'Yes'"
            score_col = "AVG_TONE"

        query = f"""
            SELECT DATE, COUNTRY, EVENT, EVENT_TYPE, {score_col} AS SCORE 
            FROM NEWS_EXAMPLES 
            WHERE {condition}
        """
        query += " ORDER BY DATE DESC LIMIT 20"

        df = fetch_table(query)
        res = []
        for _, row in df.iterrows():
            res.append({
                "date": str(row['DATE']),
                "country": str(row['COUNTRY']),
                "event": str(row['EVENT']),
                "type": str(row['EVENT_TYPE']),
                "score": float(row['SCORE'])
            })
        return res
    except Exception as e:
        print(f"Error fetching news examples: {e}")
        return []

# ── Serve React frontend (production only — skipped if static/ doesn't exist) ─
_static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(_static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(_static_dir, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """Catch-all: serve index.html for any non-API route (SPA routing)."""
        return FileResponse(os.path.join(_static_dir, "index.html"))


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

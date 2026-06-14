import logging

import numpy as np
import pandas as pd
import statsmodels.api as sm

from society_to_music.utils.logging import log_node

logger = logging.getLogger(__name__)


@log_node
def join_and_normalize(
    music_features: pd.DataFrame,
    news_sentiment: pd.DataFrame,
) -> pd.DataFrame:
    """
    Owner: Sai

    Join MUSIC_FEATURES and NEWS_SENTIMENT on (COUNTRY, DATE), then
    compute per-country Z-score normalisation for all numeric feature columns.

    Steps:
      1 — Normalise column names to uppercase
      2 — Inner join on COUNTRY + DATE
      3 — Z-score each numeric feature column grouped by COUNTRY
            (excludes TOTAL_STREAMS, ARTICLE_COUNT, DATE, COUNTRY)

    Output:
      All original columns + one *_ZSCORE column per numeric feature column.
      Written to MUSIC_NEWS_JOINED in Snowflake (CURATED schema).
    """
    music_features.columns = [c.upper() for c in music_features.columns]
    news_sentiment.columns = [c.upper() for c in news_sentiment.columns]

    music_features["COUNTRY"] = music_features["COUNTRY"].astype(str)
    news_sentiment["COUNTRY"] = news_sentiment["COUNTRY"].astype(str)

    if "DATE" in music_features.columns:
        music_features["DATE"] = pd.to_datetime(music_features["DATE"])
    if "DATE" in news_sentiment.columns:
        news_sentiment["DATE"] = pd.to_datetime(news_sentiment["DATE"])

    joined = pd.merge(music_features, news_sentiment, on=["COUNTRY", "DATE"], how="inner")

    exclude = {"TOTAL_STREAMS", "ARTICLE_COUNT", "DATE", "COUNTRY"}
    numeric_cols = joined.select_dtypes(include=["number"]).columns
    to_zscore = [c for c in numeric_cols if c not in exclude]

    for col in to_zscore:
        joined[f"{col}_ZSCORE"] = joined.groupby("COUNTRY")[col].transform(
            lambda x: (x - x.mean()) / x.std() if x.std() > 0 else 0.0
        )

    joined.columns = [str(c).upper() for c in joined.columns]
    return joined


@log_node
def compute_correlations(
    music_news_joined: pd.DataFrame,
) -> pd.DataFrame:
    """
    Owner: Sai

    Compute Pearson correlations (with HAC-corrected p-values) between every
    news feature and every music feature across 9 lag/rolling transformations,
    per country.

    News features  : AVG_TONE_SCORE, AVG_TONE_POSITIVE, AVG_TONE_NEGATIVE,
                     AVG_EMOTION_POSITIVE, AVG_EMOTION_NEGATIVE (ZSCORE variants)
    Music features : all O2_* and O3_* columns (ZSCORE variants)
    Transformations: Simultaneous, News_Lag_1/2, Music_Lag_1/2,
                     News_Roll_3d/1w/2w/1m

    Output:
      One row per (country, music_feature, news_feature) with columns for
      each lag/rolling correlation and its HAC p-value.
      Written to FEATURE_CORRELATIONS_OLAP in Snowflake (CURATED schema).
    """
    df = music_news_joined.copy()
    df.columns = [c.upper() for c in df.columns]
    df = df.sort_values(["COUNTRY", "DATE"]).reset_index(drop=True)

    news_features = [
        "AVG_TONE_SCORE_ZSCORE",
        "AVG_TONE_POSITIVE_ZSCORE",
        "AVG_TONE_NEGATIVE_ZSCORE",
        "AVG_EMOTION_POSITIVE_ZSCORE",
        "AVG_EMOTION_NEGATIVE_ZSCORE",
    ]
    music_features = [
        c for c in df.columns
        if (c.startswith("O2_") or c.startswith("O3_")) and c.endswith("_ZSCORE")
    ]

    transformations = [
        ("Simultaneous",  "shift",     0,  0,  7),
        ("News_Lag_1",    "shift",     1,  0,  7),
        ("News_Lag_2",    "shift",     2,  0,  7),
        ("Music_Lag_1",   "shift",     0,  1,  7),
        ("Music_Lag_2",   "shift",     0,  2,  7),
        ("News_Roll_3d",  "roll_news", 3,  0, 10),
        ("News_Roll_1w",  "roll_news", 7,  0, 14),
        ("News_Roll_2w",  "roll_news", 14, 0, 21),
        ("News_Roll_1m",  "roll_news", 30, 0, 37),
    ]

    records = []
    for country in df["COUNTRY"].unique():
        cdf = df[df["COUNTRY"] == country].copy()
        for n_feat in news_features:
            for m_feat in music_features:
                if n_feat not in cdf.columns or m_feat not in cdf.columns:
                    continue
                base = cdf[[m_feat, n_feat]].copy()
                for name, kind, n_p, m_p, hac_lags in transformations:
                    if kind == "shift":
                        tmp = pd.DataFrame({
                            m_feat: base[m_feat].shift(m_p),
                            n_feat: base[n_feat].shift(n_p),
                        })
                    else:  # roll_news
                        tmp = pd.DataFrame({
                            m_feat: base[m_feat],
                            n_feat: base[n_feat].rolling(window=n_p, min_periods=n_p).mean(),
                        })

                    clean = tmp.dropna()
                    if len(clean) > max(10, hac_lags + 2):
                        corr = clean[m_feat].corr(clean[n_feat])
                        try:
                            model = sm.OLS(
                                clean[n_feat],
                                sm.add_constant(clean[m_feat]),
                            ).fit(cov_type="HAC", cov_kwds={"maxlags": hac_lags})
                            p_val = model.pvalues[m_feat]
                        except Exception:
                            p_val = np.nan
                    else:
                        corr, p_val = np.nan, np.nan

                    records.append({
                        "country":       country,
                        "lag_type":      name,
                        "music_feature": m_feat.replace("_ZSCORE", ""),
                        "news_feature":  n_feat.replace("_ZSCORE", ""),
                        "correlation":   corr,
                        "p_value_hac":   p_val,
                    })

    corr_df = pd.DataFrame(records)

    pivot = corr_df.pivot(
        index=["country", "music_feature", "news_feature"],
        columns="lag_type",
        values=["correlation", "p_value_hac"],
    )
    pivot.columns = [f"{lag}_{metric}" for metric, lag in pivot.columns]
    pivot = pivot.reset_index()

    if "Simultaneous_correlation" in pivot.columns:
        pivot["_abs"] = pivot["Simultaneous_correlation"].abs()
        pivot = pivot.sort_values("_abs", ascending=False).drop(columns=["_abs"])

    pivot.columns = [str(c).upper() for c in pivot.columns]
    return pivot.reset_index(drop=True)

import pandas as pd
from snowflake_connection import get_connection

def main():
    conn = get_connection()
    try:
        # Load the joined dataframe directly from Snowflake using pandas read_sql
        # which runs via the snowflake python connector
        query = "SELECT * FROM MUSIC_NEWS_JOINED"
        df = pd.read_sql(query, conn)
        
        # The prompt asked for: news tone, positive tone, negative tone, positive emotion, negative emotion
        # We will use the normalized ZSCORE versions since we just generated them
        news_features = [
            'AVG_TONE_SCORE_ZSCORE', 
            'AVG_TONE_POSITIVE_ZSCORE', 
            'AVG_TONE_NEGATIVE_ZSCORE', 
            'AVG_EMOTION_POSITIVE_ZSCORE', 
            'AVG_EMOTION_NEGATIVE_ZSCORE'
        ]
        
        # Identify the musical features by their prefix (O2_ / O3_)
        # Then filter to use their _ZSCORE equivalents
        music_features = [
            col for col in df.columns 
            if (col.startswith('O2_') or col.startswith('O3_')) and col.endswith('_ZSCORE')
        ]
        
        
        # Calculate Pearson correlations
        correlation_records = []
        
        import statsmodels.api as sm
        import numpy as np

        # Sort the dataframe by COUNTRY and DATE to maintain time-series structure
        # which is required for accurate HAC error calculations
        df = df.sort_values(by=['COUNTRY', 'DATE']).reset_index(drop=True)
        maxlags = 7  # 7 days lag is standard for daily autocorrelation
        
        # Iterate by country to prevent calculation leakage between countries
        countries = df['COUNTRY'].unique()
        for country in countries:
            country_df = df[df['COUNTRY'] == country].copy()
            
            for n_feat in news_features:
                for m_feat in music_features:
                    if n_feat in country_df.columns and m_feat in country_df.columns:
                        base_data = country_df[[m_feat, n_feat]].copy()
                        
                        transformations = [
                            ("Simultaneous", "shift", 0, 0, 7),
                            ("News_Lag_1", "shift", 1, 0, 7),
                            ("News_Lag_2", "shift", 2, 0, 7),
                            ("Music_Lag_1", "shift", 0, 1, 7),
                            ("Music_Lag_2", "shift", 0, 2, 7),
                            ("News_Roll_3d", "roll_news", 3, 0, 3 + 7),
                            ("News_Roll_1w", "roll_news", 7, 0, 7 + 7),
                            ("News_Roll_2w", "roll_news", 14, 0, 14 + 7),
                            ("News_Roll_1m", "roll_news", 30, 0, 30 + 7)
                        ]
                        
                        for transform_name, transform_type, n_param, m_param, hac_lags in transformations:
                            transformed_data = pd.DataFrame()
                            if transform_type == "shift":
                                transformed_data[m_feat] = base_data[m_feat].shift(m_param)
                                transformed_data[n_feat] = base_data[n_feat].shift(n_param)
                            elif transform_type == "roll_news":
                                transformed_data[m_feat] = base_data[m_feat]
                                transformed_data[n_feat] = base_data[n_feat].rolling(window=n_param, min_periods=n_param).mean()
                            
                            # Filter out NaN rows cleanly for OLS
                            clean_data = transformed_data.dropna()
                            
                            if len(clean_data) > max(10, hac_lags + 2):
                                # 1. Standard pearson correlation
                                corr = clean_data[m_feat].corr(clean_data[n_feat])
                                
                                # 2. Extract p-value corrected for HAC Autocorrelation errors (Newey-West)
                                X = sm.add_constant(clean_data[m_feat])
                                y = clean_data[n_feat]
                                try:
                                    # Adjust maxlags relative to the transformation to combat induced autocorrelation
                                    model = sm.OLS(y, X).fit(cov_type='HAC', cov_kwds={'maxlags': hac_lags})
                                    p_val = model.pvalues[m_feat]
                                except Exception:
                                    p_val = np.nan
                            else:
                                corr = np.nan
                                p_val = np.nan
                            
                            # Clean up names for the final dataframe
                            clean_n_feat = n_feat.replace('_ZSCORE', '')
                            clean_m_feat = m_feat.replace('_ZSCORE', '')
                            
                            correlation_records.append({
                                'country': country,
                                'lag_type': transform_name,
                                'music_feature': clean_m_feat,
                                'news_feature': clean_n_feat,
                                'correlation': corr,
                                'p_value_hac': p_val
                            })
        
        # Create dataframe with music feature, news feature, correlation
        corr_df = pd.DataFrame(correlation_records)
        
        # Pivot the dataframe so lag types become columns
        pivot_df = corr_df.pivot(
            index=['country', 'music_feature', 'news_feature'], 
            columns='lag_type', 
            values=['correlation', 'p_value_hac']
        )
        
        # Flatten the MultiIndex columns (e.g., 'correlation' + 'Simultaneous' -> 'Simultaneous_correlation')
        pivot_df.columns = [f'{lag}_{metric}' for metric, lag in pivot_df.columns]
        pivot_df = pivot_df.reset_index()
        
        # Sort values by the Simultaneous correlation strength (absolute value)
        if 'Simultaneous_correlation' in pivot_df.columns:
            pivot_df['abs_corr'] = pivot_df['Simultaneous_correlation'].abs()
            pivot_df = pivot_df.sort_values(by='abs_corr', ascending=False).drop(columns=['abs_corr']).reset_index(drop=True)
        
        
        
        # Format Snowflake column names reliably (must be upper string)
        pivot_df.columns = [str(c).upper() for c in pivot_df.columns]
        
        from snowflake.connector.pandas_tools import write_pandas
        
        success, nchunks, nrows, _ = write_pandas(
            conn, 
            pivot_df, 
            table_name="FEATURE_CORRELATIONS_OLAP", 
            auto_create_table=True,
            overwrite=True
        )
    finally:
        conn.close()

if __name__ == "__main__":
    main()

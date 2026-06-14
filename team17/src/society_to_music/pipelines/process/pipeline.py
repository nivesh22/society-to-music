from kedro.pipeline import Pipeline, node, pipeline

from .clean_audio_features import clean_audio_features
from .clean_gdelt import clean_gdelt
from .clean_spotify import clean_spotify


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=clean_gdelt,
                inputs=[
                    "raw_gdelt",
                    "params:target_regions",
                    "params:start_date",
                    "params:end_date",
                ],
                outputs="daily_news_sentiment",
                name="clean_gdelt_node",
            ),
            node(
                func=clean_spotify,
                inputs=[
                    "raw_spotify_charts",
                    "params:target_regions",
                    "params:start_date",
                    "params:end_date",
                    "params:chart_type",
                    "params:trend_weights",
                ],
                outputs="daily_music_features",
                name="clean_spotify_node",
            ),
            node(
                func=clean_audio_features,
                inputs=["raw_audio_features", "params:feature_columns"],
                outputs="audio_emotion_scores",
                name="clean_audio_features_node",
            ),
        ]
    )

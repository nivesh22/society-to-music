from kedro.pipeline import Pipeline, node, pipeline

from .join_and_aggregate_charts_music_features import join_and_aggregate


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=join_and_aggregate,
                inputs=[
                    "daily_music_features",
                    "audio_emotion_scores",
                    "params:coverage_ok",
                    "params:coverage_low",
                    "params:feature_columns",
                ],
                outputs="curated_music_features",
                name="join_and_aggregate_node",
            ),
        ]
    )

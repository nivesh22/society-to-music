from kedro.pipeline import Pipeline, node, pipeline

from .nodes import compute_correlations, join_and_normalize


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=join_and_normalize,
                inputs=["curated_music_features", "daily_news_sentiment"],
                outputs="music_news_joined",
                name="join_and_normalize_node",
            ),
            node(
                func=compute_correlations,
                inputs="music_news_joined",
                outputs="feature_correlations_olap",
                name="compute_correlations_node",
            ),
        ]
    )

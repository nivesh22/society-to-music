"""Project pipelines."""

from kedro.pipeline import Pipeline

from society_to_music.pipelines import analytics, curate, process


def register_pipelines() -> dict[str, Pipeline]:
    """Register the project's pipelines."""
    return {
        "process": process.create_pipeline(),
        "curate": curate.create_pipeline(),
        "analytics": analytics.create_pipeline(),
        "__default__": (
            process.create_pipeline()
            + curate.create_pipeline()
            + analytics.create_pipeline()
        ),
    }

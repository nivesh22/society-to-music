import logging
import time
from collections.abc import Callable
from functools import wraps

try:
    from pyspark.sql import DataFrame as SparkDataFrame  # noqa: F401

    SPARK_AVAILABLE = True
except ImportError:
    SPARK_AVAILABLE = False


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a node."""
    return logging.getLogger(f"society_to_music.{name}")


def log_node(func: Callable) -> Callable:
    """Decorator that automatically logs:
    - Node start with input row counts
    - Node end with output row counts
    - Execution time
    - Any errors

    Usage:
        @log_node
        def clean_spotify(df):
            ...
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__name__)

        # Log start + input sizes
        for i, arg in enumerate(args):
            if hasattr(arg, "count"):
                try:
                    count = arg.count()
                    logger.info(f"START | input_{i}_rows={count}")
                except Exception:
                    logger.info(f"START | input_{i}=DataFrame")
            elif hasattr(arg, "__len__"):
                logger.info(f"START | input_{i}_rows={len(arg)}")

        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            elapsed = round(time.time() - start_time, 2)

            # Log end + output size
            if hasattr(result, "count"):
                try:
                    out_count = result.count()
                    logger.info(
                        f"END | output_rows={out_count} | elapsed_seconds={elapsed}"
                    )
                except Exception:
                    logger.info(f"END | elapsed_seconds={elapsed}")
            else:
                logger.info(f"END | elapsed_seconds={elapsed}")

            return result

        except Exception as e:
            elapsed = round(time.time() - start_time, 2)
            logger.error(
                f"FAILED | error={str(e)} | elapsed_seconds={elapsed}", exc_info=True
            )
            raise

    return wrapper

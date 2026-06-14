"""
snowflake_connection.py
-----------------------
Provides a reusable Snowflake connection using credentials loaded
from a .env file in the same directory.

Usage
-----
    from snowflake_connection import get_connection, run_query

    # Get a raw connection
    conn = get_connection()

    # Run a query and get a pandas DataFrame
    df = run_query("SELECT * FROM my_table LIMIT 10")
    print(df.head())
"""

import os
import snowflake.connector
import pandas as pd
from pathlib import Path

_SNOWFLAKE_SECRETS = [
    "SNOWFLAKE_ACCOUNT",
    "SNOWFLAKE_USER",
    "SNOWFLAKE_PASSWORD",
    "SNOWFLAKE_WAREHOUSE",
    "SNOWFLAKE_ROLE",
    "SNOWFLAKE_DATABASE",
    "SNOWFLAKE_SCHEMA",
]

def _load_from_secret_manager() -> None:
    """Pull Snowflake secrets from GCP Secret Manager into os.environ."""
    from google.cloud import secretmanager  # noqa: PLC0415
    project_id = os.environ["GCP_PROJECT_ID"]
    client = secretmanager.SecretManagerServiceClient()
    for secret_name in _SNOWFLAKE_SECRETS:
        resource = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": resource})
        os.environ[secret_name] = response.payload.data.decode("UTF-8")

def _load_from_env_file() -> None:
    """Load credentials from .env file (local dev only)."""
    from dotenv import load_dotenv  # noqa: PLC0415
    _env_path = Path(__file__).parent / ".env"
    load_dotenv(dotenv_path=_env_path, override=True)

# On startup: use Secret Manager in GCP, .env file locally
if os.getenv("USE_SECRET_MANAGER", "false").lower() == "true":
    _load_from_secret_manager()
else:
    _load_from_env_file()


def get_connection() -> snowflake.connector.SnowflakeConnection:
    """
    Create and return a Snowflake connection using environment variables.

    Required .env keys:
        SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD

    Optional .env keys (applied via USE after connecting):
        SNOWFLAKE_ROLE, SNOWFLAKE_WAREHOUSE, SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA

    Returns
    -------
    snowflake.connector.SnowflakeConnection
    """
    required = ["SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {missing}\n"
            f"Copy .env.example → .env and fill in your credentials."
        )

    conn = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        login_timeout=30,
    )

    # Apply optional context settings after connecting
    cur = conn.cursor()
    if os.getenv("SNOWFLAKE_ROLE"):
        cur.execute(f"USE ROLE {os.environ['SNOWFLAKE_ROLE']}")
    if os.getenv("SNOWFLAKE_WAREHOUSE"):
        cur.execute(f"USE WAREHOUSE {os.environ['SNOWFLAKE_WAREHOUSE']}")
    if os.getenv("SNOWFLAKE_DATABASE"):
        cur.execute(f"USE DATABASE {os.environ['SNOWFLAKE_DATABASE']}")
    if os.getenv("SNOWFLAKE_SCHEMA"):
        cur.execute(f"USE SCHEMA {os.environ['SNOWFLAKE_SCHEMA']}")
    cur.close()

    return conn


def run_query(sql: str, params: tuple = None) -> pd.DataFrame:
    """
    Execute a SQL query and return the result as a pandas DataFrame.

    Parameters
    ----------
    sql : str
        The SQL query to execute.
    params : tuple, optional
        Bind parameters for the query.

    Returns
    -------
    pd.DataFrame
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        df = cur.fetch_pandas_all()
        return df
    finally:
        conn.close()


def test_connection() -> None:
    """Quick smoke-test: connects and prints current user, database, and Snowflake version."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT CURRENT_USER(), CURRENT_DATABASE(), CURRENT_SCHEMA(), CURRENT_WAREHOUSE(), CURRENT_VERSION()")
        user, db, schema, wh, version = cur.fetchone()
        print(f"✅  Connected to Snowflake!")
        print(f"    User      : {user}")
        print(f"    Warehouse : {wh}")
        print(f"    Database  : {db}")
        print(f"    Schema    : {schema}")
        print(f"    Version   : {version}")
    finally:
        conn.close()


if __name__ == "__main__":
    test_connection()

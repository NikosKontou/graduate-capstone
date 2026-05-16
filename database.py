import streamlit as st
import duckdb
from google.cloud import bigquery
from google.oauth2 import service_account


# ---------------------------------------------------------------------------
# DuckDB
# ---------------------------------------------------------------------------

@st.cache_resource
def get_local_connection(
    raw_path: str,
    agg_rounds_path: str,
    agg_sessions_path: str,
    agg_rtp_buckets_path: str,
    agg_spin_transitions_path: str,
):
    """
    Opens an in-memory DuckDB connection and registers all 5 parquet files
    as views so every query module can reference them by name.
    """
    con = duckdb.connect(database=":memory:")

    con.execute(f"CREATE OR REPLACE VIEW raw_rounds            AS SELECT * FROM read_parquet('{raw_path}')")
    con.execute(f"CREATE OR REPLACE VIEW agg_rounds            AS SELECT * FROM read_parquet('{agg_rounds_path}')")
    con.execute(f"CREATE OR REPLACE VIEW agg_sessions          AS SELECT * FROM read_parquet('{agg_sessions_path}')")
    con.execute(f"CREATE OR REPLACE VIEW agg_rtp_buckets       AS SELECT * FROM read_parquet('{agg_rtp_buckets_path}')")
    con.execute(f"CREATE OR REPLACE VIEW agg_spin_transitions  AS SELECT * FROM read_parquet('{agg_spin_transitions_path}')")

    return con


# ---------------------------------------------------------------------------
# BigQuery
# ---------------------------------------------------------------------------

@st.cache_resource
def get_bq_connection():
    info = st.secrets["gcp_service_account"]
    creds = service_account.Credentials.from_service_account_info(info)
    return bigquery.Client(credentials=creds, project=creds.project_id)


# ---------------------------------------------------------------------------
# Unified query executor — hides the BQ / DuckDB API difference
# ---------------------------------------------------------------------------

def run_query(client, query: str, env: str):
    """Execute *query* and always return a pandas DataFrame."""
    if env == "BigQuery":
        return client.query(query).to_dataframe()
    else:
        return client.execute(query).df()


# ---------------------------------------------------------------------------
# Table-ref helpers — backticks for BQ, plain names for DuckDB
# ---------------------------------------------------------------------------

def tbl(name: str, env: str, bq_dataset: str = "") -> str:
    """
    Return the correct table reference for the active environment.

    For BigQuery supply bq_dataset, e.g. 'graduate-capstone.igaming_test'.
    The agg tables are expected to live in the same dataset as the raw table.
    """
    if env == "BigQuery":
        return f"`{bq_dataset}.{name}`"
    return name  # DuckDB view registered above

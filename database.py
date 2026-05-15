import streamlit as st
import duckdb
from google.cloud import bigquery
from google.oauth2 import service_account

@st.cache_resource
def get_local_connection(db_path: str):
    con = duckdb.connect(database=':memory:')
    con.execute(f"CREATE OR REPLACE VIEW local_logs AS SELECT * FROM read_parquet('{db_path}')")
    return con

@st.cache_resource
def get_bq_connection():
    info = st.secrets["gcp_service_account"]
    creds = service_account.Credentials.from_service_account_info(info)
    return bigquery.Client(credentials=creds, project=creds.project_id)
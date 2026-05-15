import duckdb
import streamlit as st

@st.cache_resource
def get_connection(db_path: str):
    con = duckdb.connect(database=':memory:')
    con.execute(f"CREATE OR REPLACE VIEW local_logs AS SELECT * FROM read_parquet('{db_path}')")
    return con
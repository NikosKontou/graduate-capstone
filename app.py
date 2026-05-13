import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account

# Access secrets from the Streamlit Cloud dashboard
client_info = st.secrets["gcp_service_account"]
credentials = service_account.Credentials.from_service_account_info(client_info)
client = bigquery.Client(credentials=credentials, project=credentials.project_id)

# Your query logic here
st.title("iGaming Engagement Lab")

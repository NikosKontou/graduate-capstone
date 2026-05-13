import streamlit as st
import seaborn as sns
import matplotlib.pyplot as plt
from google.cloud import bigquery
from google.oauth2 import service_account

# Setup connection
@st.cache_resource
def get_bq_client():
    info = st.secrets["gcp_service_account"]
    creds = service_account.Credentials.from_service_account_info(info)
    return bigquery.Client(credentials=creds, project=creds.project_id)

client = get_bq_client()
table_name = 'graduate-capstone.igaming_test.second_50k_p1'

st.title("🎰 Player Engagement Demo")

# Sidebar for interactivity
st.sidebar.header("Filters")
min_bet = st.sidebar.slider("Minimum Bet Amount", 0.0, 5.0, 0.0)
provider = st.sidebar.multiselect("Game Provider ID", options=[2, 5, 10], default=[2])

# 1. Distribution of Wins vs Bets
st.subheader("Bet vs. Win Correlation")

query = f"""
    SELECT betbaseamount, wonbaseamount, game_provider_id
    FROM `{table_name}`
    WHERE betbaseamount >= {min_bet}
    AND game_provider_id IN UNNEST({provider})
    LIMIT 1000
"""

df = client.query(query).to_dataframe()

fig, ax = plt.subplots(figsize=(10, 5))
sns.scatterplot(data=df, x="betbaseamount", y="wonbaseamount", hue="game_provider_id", ax=ax)
sns.despine()
st.pyplot(fig)

# 2. Session Depth (Spins per Session)
st.subheader("Session Depth Analysis")

# Aggregate in SQL to keep the dataframe small
query_agg = f"""
    SELECT sessionid, COUNT(*) as spin_count
    FROM `{table_name}`
    GROUP BY sessionid
    HAVING spin_count > 1
    ORDER BY spin_count DESC
    LIMIT 20
"""

df_sessions = client.query(query_agg).to_dataframe()

fig2, ax2 = plt.subplots(figsize=(10, 5))
sns.barplot(data=df_sessions, x="sessionid", y="spin_count", palette="viridis", ax=ax2)
plt.xticks(rotation=45)
st.pyplot(fig2)

# 3. High-Level Metrics
col1, col2 = st.columns(2)
with col1:
    avg_win = df['wonbaseamount'].mean()
    st.metric("Avg Win (Selected)", f"{avg_win:.2f}")
with col2:
    total_spins = len(df)
    st.metric("Spins in View", total_spins)

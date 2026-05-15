import streamlit as st
import seaborn as sns
import matplotlib.pyplot as plt
from google.cloud import bigquery
from google.oauth2 import service_account

@st.cache_resource
def get_bq_client():
    info = st.secrets["gcp_service_account"]
    creds = service_account.Credentials.from_service_account_info(info)
    return bigquery.Client(credentials=creds, project=creds.project_id)

client = get_bq_client()
table_name = 'graduate-capstone.igaming_test.50k'

st.title("🎰 Player Engagement Demo")
st.warning("⚠️ Warning: The results displayed below are based on a limited 50k row test table.")

st.sidebar.header("Filters")
min_bet = st.sidebar.slider("Minimum Bet Amount", 0.0, 5.0, 0.0)
provider = st.sidebar.multiselect("Game Provider ID", options=[2, 5, 10], default=[2])

# --- Questions 1, 2 & 3: High-Level Session Metrics ---
st.subheader("Global Session Averages")

# Calculate all averages natively in BigQuery
kpi_query = f"""
    WITH session_data AS (
        SELECT 
            sessionid,
            COUNT(*) as spins,
            TIMESTAMP_DIFF(MAX(endtime), MIN(starttime), SECOND) as session_dur_sec
        FROM `{table_name}`
        GROUP BY sessionid
    )
    SELECT 
        (SELECT AVG(TIMESTAMP_DIFF(endtime, starttime, SECOND)) FROM `{table_name}`) as avg_round_sec,
        AVG(spins) as avg_spins,
        AVG(session_dur_sec) as avg_session_sec
    FROM session_data
"""
df_kpi = client.query(kpi_query).to_dataframe()

col1, col2, col3 = st.columns(3)
col1.metric("Avg Round Duration", f"{df_kpi['avg_round_sec'][0]:.2f} sec")
col2.metric("Avg Spins / Session", f"{df_kpi['avg_spins'][0]:.1f}")
col3.metric("Avg Session Duration", f"{df_kpi['avg_session_sec'][0]:.1f} sec")

st.divider()

# --- Question 4: Stake Variation by Game ---
st.subheader("Stake Variation (Up/Down) by Game")

# Identifies sessions where the max bet differs from the min bet
stake_query = f"""
    WITH stake_changes AS (
        SELECT 
            account,
            game_provider_id,
            IF(MAX(betbaseamount) > MIN(betbaseamount), 1, 0) as changed_stake
        FROM `{table_name}`
        GROUP BY sessionid, account, game_provider_id
    )
    SELECT 
        game_provider_id,
        SUM(changed_stake) as players_varying_stake,
        COUNT(DISTINCT account) as total_players,
        (SUM(changed_stake) / COUNT(DISTINCT account)) * 100 as pct_varying
    FROM stake_changes
    GROUP BY game_provider_id
    ORDER BY pct_varying DESC
"""
df_stake = client.query(stake_query).to_dataframe()

fig_stake, ax_stake = plt.subplots(figsize=(10, 4))
sns.barplot(data=df_stake, x="game_provider_id", y="pct_varying", palette="magma", ax=ax_stake)
ax_stake.set_ylabel("% of Players Changing Stake")
ax_stake.set_xlabel("Game Provider ID")
sns.despine()
st.pyplot(fig_stake)

st.divider()

# --- Original Charts ---
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

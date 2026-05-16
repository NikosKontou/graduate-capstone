import streamlit as st
import database
import queries
import charts

st.title("🎰 Player Engagement Demo")

# --- Environment Toggle ---
env = st.sidebar.radio("🌍 Environment Source", ["Local DuckDB", "BigQuery"])

if env == "Local DuckDB":
    db_path = '/Top/ACG/Year_2/trimester 3/capstone/data/full_merged_sorted_data.parquet'
    table_name = 'local_logs'
    client = database.get_local_connection(db_path)
    st.sidebar.success("🟢 Running locally via DuckDB")
else:
    table_name = 'graduate-capstone.igaming_test.50k'
    client = database.get_bq_connection()
    st.sidebar.info("☁️ Running via Google BigQuery")

st.sidebar.divider()

# --- Filters ---
st.sidebar.header("Filters")
min_bet = st.sidebar.slider("Minimum Bet Amount", 0.0, 5.0, 0.0)
providers = st.sidebar.multiselect("Game Provider ID", options=[2, 5, 10], default=[2])
game_ids_input = st.sidebar.text_input("Game IDs (comma-separated, optional)", "")

try:
    game_ids = [int(x.strip()) for x in game_ids_input.split(',')] if game_ids_input.strip() else []
except ValueError:
    st.sidebar.error("Please enter valid numeric Game IDs.")
    st.stop()

if not providers:
    st.warning("Select at least one provider.")
    st.stop()

# --- Data Execution ---
# We pass the selected 'env' variable down to the queries
target_env = "BigQuery" if env == "BigQuery" else "Local"

df_kpi = queries.get_kpi_metrics(client, table_name, min_bet, providers, game_ids, target_env)

c1, c2, c3 = st.columns(3)
c1.metric("Avg Round Duration", f"{df_kpi['avg_round'][0]:.2f}s")
c2.metric("Avg Spins", f"{df_kpi['avg_spins'][0]:.1f}")
c3.metric("Avg Session", f"{df_kpi['avg_session'][0]:.1f}s")

st.divider()

df_scatter = queries.get_scatter_data(client, table_name, min_bet, providers, game_ids, target_env)
fig_scatter = charts.plot_bet_vs_win(df_scatter)

st.subheader("Bet vs. Win Correlation")
st.caption("⚠️ Displaying a sample of 1,000 rows for performance.")
st.pyplot(fig_scatter)

# Fetch the data (Now passing min_bet, providers, and game_ids)
df_variance = queries.get_overall_stake_variance(client, table_name, min_bet, providers, game_ids, target_env)

# Extract the numbers from the dataframe
total_players = df_variance['total_players'][0]
varying_players = df_variance['varying_players'][0]
pct_varying = df_variance['pct_varying'][0]

# Display in the UI
st.subheader("Global Stake Behavior")
c1, c2 = st.columns(2)
c1.metric("Total Unique Players", f"{total_players:,}")
c2.metric("Players Changing Stake", f"{varying_players:,}", f"{pct_varying:.1f}%")
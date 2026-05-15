import streamlit as st
import database
import queries
import charts

# Setup
db_path = '/Top/ACG/Year_2/trimester 3/capstone/data/full_merged_sorted_data.parquet'
table_name = 'local_logs'
con = database.get_connection(db_path)

# UI Elements
st.title("🎰 Player Engagement Demo")

# Dynamic Sidebar Inputs
st.sidebar.header("Filters")
min_bet = st.sidebar.slider("Minimum Bet Amount", 0.0, 5.0, 0.0)
providers = st.sidebar.multiselect("Game Provider ID", options=[2, 5, 10], default=[2])

# New Game ID Filter (Comma-separated text input)
game_ids_input = st.sidebar.text_input("Game IDs (comma-separated, optional)", "")

# Convert the string input "101, 102" into a list of integers [101, 102]
try:
    game_ids = [int(x.strip()) for x in game_ids_input.split(',')] if game_ids_input.strip() else []
except ValueError:
    st.sidebar.error("Please enter valid numeric Game IDs.")
    st.stop()

if not providers:
    st.warning("Select at least one provider.")
    st.stop()

# KPIs (Passing the new game_ids list)
df_kpi = queries.get_kpi_metrics(con, table_name, min_bet, providers, game_ids)

c1, c2, c3 = st.columns(3)
c1.metric("Avg Round Duration", f"{df_kpi['avg_round'][0]:.2f}s")
c2.metric("Avg Spins", f"{df_kpi['avg_spins'][0]:.1f}")
c3.metric("Avg Session", f"{df_kpi['avg_session'][0]:.1f}s")

st.divider()

# Charts (Passing the new game_ids list)
df_scatter = queries.get_scatter_data(con, table_name, min_bet, providers, game_ids)
fig_scatter = charts.plot_bet_vs_win(df_scatter)

st.subheader("Bet vs. Win Correlation")
st.pyplot(fig_scatter)
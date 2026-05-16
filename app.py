"""
app.py
------
Player Engagement Dashboard — answers Q1 through Q8.

Layout:
  Sidebar   : environment toggle + filters
  Section 1 : KPI metrics         (Q1, Q2, Q3)
  Section 2 : Stake variance      (Q4 overall + by game)
  Section 3 : RTP distribution    (Q5)
  Section 4 : Spin transitions    (Q6)
  Section 5 : Win vs session len  (Q7)
  Section 6 : Post-win behaviour  (Q8)
"""

import streamlit as st
import database
import queries
import charts

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Player Engagement",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Player Engagement Dashboard")

# ---------------------------------------------------------------------------
# Sidebar — environment
# ---------------------------------------------------------------------------

st.sidebar.header("⚙️ Environment")
env_label = st.sidebar.radio("Data source", ["Local DuckDB", "BigQuery"])
env = "BigQuery" if env_label == "BigQuery" else "Local"

# ---- DuckDB paths (edit these to match your local filesystem) -------------
LOCAL_PATHS = {
    "raw" : "/Top/ACG/Year_2/trimester 3/capstone/data/full_merged_sorted_data.parquet",
    "agg_rounds":          "/Top/ACG/Year_2/trimester 3/capstone/data/agg_rounds.parquet",
    "agg_sessions":        "/Top/ACG/Year_2/trimester 3/capstone/data/agg_sessions.parquet",
    "agg_rtp_buckets":     "/Top/ACG/Year_2/trimester 3/capstone/data/agg_rtp_buckets.parquet",
    "agg_spin_transitions":"/Top/ACG/Year_2/trimester 3/capstone/data/agg_spin_transitions.parquet",
}

# ---- BigQuery table names (dataset.table, no backticks) -------------------
# BQ_DATASET = "graduate-capstone.igaming_test"
BQ_DATASET = "graduate-capstone.igaming_merged_full"
BQ_TABLES = {
    "raw":                  f"{BQ_DATASET}.raw_rounds",
    "agg_rounds":           f"{BQ_DATASET}.agg_rounds",
    "agg_sessions":         f"{BQ_DATASET}.agg_sessions",
    "agg_rtp_buckets":      f"{BQ_DATASET}.agg_rtp_buckets",
    "agg_spin_transitions": f"{BQ_DATASET}.agg_spin_transitions",
}

if env == "Local":
    client = database.get_local_connection(
        LOCAL_PATHS["raw"],
        LOCAL_PATHS["agg_rounds"],
        LOCAL_PATHS["agg_sessions"],
        LOCAL_PATHS["agg_rtp_buckets"],
        LOCAL_PATHS["agg_spin_transitions"],
    )
    tables = {k: v.split("/")[-1].replace(".parquet", "")   # view name = filename stem
              for k, v in LOCAL_PATHS.items()}
    # Overrides to match the view names registered in database.py
    tables = {
        "raw":                  "raw_rounds",
        "agg_rounds":           "agg_rounds",
        "agg_sessions":         "agg_sessions",
        "agg_rtp_buckets":      "agg_rtp_buckets",
        "agg_spin_transitions": "agg_spin_transitions",
    }
    st.sidebar.success("Local DuckDB")
else:
    client = database.get_bq_connection()
    tables = BQ_TABLES
    st.sidebar.info("☁BigQuery")

st.sidebar.divider()

# ---------------------------------------------------------------------------
# Sidebar — filters
# ---------------------------------------------------------------------------

st.sidebar.header("🔎 Filters")

min_bet = st.sidebar.slider("Minimum Bet Amount", 0.0, 5.0, 0.0, step=0.05)

providers = st.sidebar.multiselect(
    "Game Provider ID",
    options=[2, 5, 10],
    default=[2],
)

# New Game ID Multiselect
game_ids = st.sidebar.multiselect(
    "Game IDs (optional)",
    options=list(range(1, 12)), # Generates integers 1 through 11
    default=[]
)
if not providers:
    st.warning("⚠️ Select at least one Game Provider in the sidebar.")
    st.stop()

filters = {"min_bet": min_bet, "providers": providers, "game_ids": game_ids}

# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------
# @st.cache_data keys on every argument it can hash.
# - _client / _tables  : prefixed with _ so Streamlit skips hashing them
#   (DuckDB connections and dicts of view names aren't hashable).
# - The filter primitives (min_bet, providers_tuple, game_ids_tuple, env)
#   ARE passed as plain typed values so any sidebar change produces a new
#   cache key and triggers a fresh query automatically.
# ---------------------------------------------------------------------------

@st.cache_data(ttl=600, show_spinner=False)
def fetch_all(_client, _tables, min_bet: float, providers_tuple: tuple,
              game_ids_tuple: tuple, env: str):
    filters = {
        "min_bet":   min_bet,
        "providers": list(providers_tuple),
        "game_ids":  list(game_ids_tuple),
    }
    return {
        "kpi":           queries.get_kpi_metrics(_client, _tables, filters, env),
        "stake_overall": queries.get_stake_variance_overall(_client, _tables, filters, env),
        "stake_by_game": queries.get_stake_variance_by_game(_client, _tables, filters, env),
        "rtp":           queries.get_rtp_buckets(_client, _tables, filters, env),
        "transitions":   queries.get_spin_transitions(_client, _tables, filters, env),
        "scatter":       queries.get_win_vs_session_length(_client, _tables, filters, env),
        "post_win":      queries.get_post_win_continuation(_client, _tables, filters, env),
        "hesitation": queries.get_hesitation_distribution(_client, _tables, filters, env)
    }

with st.spinner("Fetching data…"):
    data = fetch_all(
        client, tables,
        min_bet,
        tuple(sorted(providers)),
        tuple(sorted(game_ids)),
        env,
    )

# ---------------------------------------------------------------------------
# Section 1 — KPI metrics (Q1, Q2, Q3)
# ---------------------------------------------------------------------------

st.header("Key Metrics", divider="gray")

kpi = data["kpi"].iloc[0]
c1, c2, c3 = st.columns(3)

avg_round = kpi.get("avg_round_duration_sec", 0) or 0
avg_spins = kpi.get("avg_spins_per_session", 0) or 0
avg_sess  = kpi.get("avg_session_duration_sec", 0) or 0

c1.metric(
    "Q1 — Avg Round Duration",
    f"{avg_round:.2f} s",
    help="Mean time from spin start to spin end across all filtered rounds.",
)
c2.metric(
    "Q2 — Avg Spins per Session",
    f"{avg_spins:.1f}",
    help="Average number of spins played within a single session.",
)
c3.metric(
    "Q3 — Avg Session Duration",
    f"{avg_sess:.1f} s",
    help="Average time from first spin to last spin end within a session.",
)

# ---------------------------------------------------------------------------
# Section 2 — Stake variance (Q4)
# ---------------------------------------------------------------------------

st.header("Stake Behaviour (Q4)", divider="gray")

sv = data["stake_overall"].iloc[0]
total_sess    = int(sv.get("total_sessions", 0) or 0)
with_change   = int(sv.get("sessions_with_stake_change", 0) or 0)
up_events     = int(sv.get("count_stake_up_events", 0) or 0)
down_events   = int(sv.get("count_stake_down_events", 0) or 0)
pct_changed   = float(sv.get("pct_sessions_changed", 0) or 0)

m1, m2, m3 = st.columns(3)
m1.metric("Total Sessions",          f"{total_sess:,}")
m2.metric("Sessions w/ Stake Change", f"{with_change:,}", f"{pct_changed:.1f}%")
m3.metric("Stake Up / Down Events",  f"{up_events:,} ↑  {down_events:,} ↓")

col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Overall")
    fig_sv_overall = charts.plot_stake_variance_overall(
        total_sess, with_change, up_events, down_events
    )
    st.pyplot(fig_sv_overall)

with col_b:
    st.subheader("By Game")
    sg = data["stake_by_game"]
    if sg.empty:
        st.info("No data for selected filters.")
    else:
        fig_sv_game = charts.plot_stake_variance_by_game(sg)
        st.pyplot(fig_sv_game)

# ---------------------------------------------------------------------------
# Section 3 — RTP bucket distribution (Q5)
# ---------------------------------------------------------------------------

st.header("Win / Bet Ratio Distribution (Q5)", divider="gray")
st.caption("Each round is classified by how much the win was relative to the stake.")

rtp_df = data["rtp"]
if rtp_df.empty:
    st.info("No data for selected filters.")
else:
    fig_rtp = charts.plot_rtp_buckets(rtp_df)
    st.pyplot(fig_rtp)

    with st.expander("Show raw data"):
        rtp_sorted = charts._sort_rtp(rtp_df)
        st.dataframe(
            rtp_sorted[["rtp_bucket", "round_count", "pct_of_all_rounds"]]
            .rename(columns={"rtp_bucket": "Bucket",
                             "round_count": "Rounds",
                             "pct_of_all_rounds": "% of rounds"}),
            hide_index=True,
            use_container_width=True,
        )

# ---------------------------------------------------------------------------
# Section 4 — Spin transitions / bet change direction (Q6)
# ---------------------------------------------------------------------------

st.header("Bet Change After Each Round (Q6)", divider="gray")
st.caption(
    "For every spin that follows another, did the player keep the same stake, "
    "increase it, or decrease it? Grouped by the previous round's outcome."
)

tr_df = data["transitions"]
if tr_df.empty:
    st.info("No data for selected filters.")
else:
    fig_tr = charts.plot_spin_transitions(tr_df)
    st.pyplot(fig_tr)

    with st.expander("Show raw data"):
        st.dataframe(tr_df, hide_index=True, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 5 — Win amount vs session length (Q7)
# ---------------------------------------------------------------------------

st.header("Win Amount vs Session Length (Q7)", divider="gray")
st.caption("Each dot = one session (up to 2 000 sampled). Dashed line = overall trend.")

sc_df = data["scatter"]
if sc_df.empty:
    st.info("No data for selected filters.")
else:
    fig_sc = charts.plot_win_vs_session_length(sc_df)
    st.pyplot(fig_sc)

# ---------------------------------------------------------------------------
# Section 6 — Post-win continuation (Q8)
# ---------------------------------------------------------------------------

st.header("How Long Players Continue After Each Win Type (Q8)", divider="gray")
st.caption(
    "After a round with a given win outcome, how many more spins did "
    "the player go on to play in that session?"
)

pw_df = data["post_win"]
if pw_df.empty:
    st.info("No data for selected filters.")
else:
    fig_pw = charts.plot_post_win_continuation(pw_df)
    st.pyplot(fig_pw)

    with st.expander("Show raw data"):
        display_cols = ["prev_rtp_bucket"] + [
            c for c in charts.SPINS_REMAINING_COLS if c in pw_df.columns
        ]
        st.dataframe(pw_df[display_cols], hide_index=True, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 7 — Session Hesitation
# ---------------------------------------------------------------------------

st.header("Session Hesitation", divider="gray")
st.caption(
    "Distribution of the average time taken between spins (Session Duration ÷ Total Spins). "
    "Values are rounded to the nearest second and capped at 60s to exclude abandoned sessions."
)

hes_df = data["hesitation"]
if hes_df.empty:
    st.info("No data for selected filters.")
else:
    fig_hes = charts.plot_hesitation_distribution(hes_df)
    st.pyplot(fig_hes)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.divider()
st.caption(
    f"Data source: **{env_label}** | "
    f"Filters: min_bet={min_bet}, providers={providers}"
    + (f", game_ids={game_ids}" if game_ids else "")
)
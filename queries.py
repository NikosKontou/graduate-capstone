"""
queries.py
----------
All analytical queries for the Player Engagement dashboard.

Every function accepts:
  client  – DuckDB connection or BigQuery client
  tables  – dict with keys: raw, agg_rounds, agg_sessions,
             agg_rtp_buckets, agg_spin_transitions
  filters – dict with keys: min_bet (float), providers (list), game_ids (list)
  env     – "BigQuery" | "Local"

Key design rule — each aggregated table only exposes the columns it was
built with, so we use three separate WHERE helpers instead of one:

  _where_rounds()      → agg_rounds   (has betbaseamount, game_provider_id, game_id)
  _where_sessions()    → agg_sessions (has total_bet, total_spins, game_provider_id, game_id)
  _where_transitions() → agg_spin_transitions (has game_id only)

SQL dialect differences:
  BQ                          DuckDB
  TIMESTAMP_DIFF(a,b,SECOND)  DATEDIFF('second', b, a)
  SAFE_DIVIDE(a, b)           a / NULLIF(b, 0)
  COUNTIF(cond)               COUNT(*) FILTER (WHERE cond)
  LOGICAL_OR(cond)            BOOL_OR(cond)
  `dataset.table`             plain view name
"""

from database import run_query


# ── helpers ──────────────────────────────────────────────────────────────────

def _ref(tables: dict, key: str, env: str) -> str:
    name = tables[key]
    return f"`{name}`" if env == "BigQuery" else name


def _where_rounds(filters: dict) -> str:
    """For agg_rounds / raw_rounds — has betbaseamount, game_provider_id, game_id."""
    parts = [
        f"betbaseamount >= {filters['min_bet']}",
        f"game_provider_id IN ({', '.join(map(str, filters['providers']))})",
    ]
    if filters["game_ids"]:
        parts.append(f"game_id IN ({', '.join(map(str, filters['game_ids']))})")
    return "WHERE " + " AND ".join(parts)


def _where_sessions(filters: dict) -> str:
    """
    For agg_sessions — has total_bet, total_spins, game_provider_id, game_id.
    min_bet is approximated as average bet per session (total_bet / total_spins).
    """
    parts = [
        f"game_provider_id IN ({', '.join(map(str, filters['providers']))})",
    ]
    if filters["min_bet"] > 0:
        parts.append(f"(total_bet / NULLIF(total_spins, 0)) >= {filters['min_bet']}")
    if filters["game_ids"]:
        parts.append(f"game_id IN ({', '.join(map(str, filters['game_ids']))})")
    return "WHERE " + " AND ".join(parts)


def _where_transitions(filters: dict) -> str:
    """For agg_spin_transitions — only game_id is available."""
    parts = []
    if filters["game_ids"]:
        parts.append(f"game_id IN ({', '.join(map(str, filters['game_ids']))})")
    return ("WHERE " + " AND ".join(parts)) if parts else ""


def _safe_div(num: str, den: str, env: str) -> str:
    if env == "BigQuery":
        return f"SAFE_DIVIDE({num}, {den})"
    return f"{num} / NULLIF({den}, 0)"


def _bool_or(condition: str, env: str) -> str:
    if env == "BigQuery":
        return f"LOGICAL_OR({condition})"
    return f"BOOL_OR({condition})"


# ── Q1 / Q2 / Q3 — KPI metrics ───────────────────────────────────────────────

def get_kpi_metrics(client, tables, filters, env):
    """
    One-row DataFrame:
      avg_round_duration_sec   (Q1)
      avg_spins_per_session    (Q2)
      avg_session_duration_sec (Q3)
    """
    ar  = _ref(tables, "agg_rounds",   env)
    as_ = _ref(tables, "agg_sessions", env)
    wr  = _where_rounds(filters)
    ws  = _where_sessions(filters)

    query = f"""
        SELECT
            (SELECT AVG(round_duration_sec)   FROM {ar}  {wr}) AS avg_round_duration_sec,
            (SELECT AVG(total_spins)          FROM {as_} {ws}) AS avg_spins_per_session,
            (SELECT AVG(session_duration_sec) FROM {as_} {ws}) AS avg_session_duration_sec
    """
    return run_query(client, query, env)


# ── Q4 — Stake variance ───────────────────────────────────────────────────────

def get_stake_variance_overall(client, tables, filters, env):
    as_ = _ref(tables, "agg_sessions", env)
    w = _where_sessions(filters)

    # Update this variable
    ftype = "FLOAT64" if env == "BigQuery" else "DOUBLE"
    pct = _safe_div(
        "SUM(CASE WHEN had_stake_change THEN 1 ELSE 0 END)",
        f"CAST(COUNT(*) AS {ftype})",
        env,
    )

    query = f"""
        SELECT
            COUNT(*)                                           AS total_sessions,
            SUM(CASE WHEN had_stake_change THEN 1 ELSE 0 END) AS sessions_with_stake_change,
            SUM(count_stake_up)                               AS count_stake_up_events,
            SUM(count_stake_down)                             AS count_stake_down_events,
            {pct} * 100                                       AS pct_sessions_changed
        FROM {as_} {w}
    """
    return run_query(client, query, env)


def get_stake_variance_by_game(client, tables, filters, env):
    as_ = _ref(tables, "agg_sessions", env)
    w = _where_sessions(filters)

    # Update this variable
    ftype = "FLOAT64" if env == "BigQuery" else "DOUBLE"
    pct = _safe_div(
        "SUM(CASE WHEN had_stake_change THEN 1 ELSE 0 END)",
        f"CAST(COUNT(*) AS {ftype})",
        env,
    )

    query = f"""
        SELECT
            game_id,
            COUNT(*)                                           AS total_sessions,
            SUM(CASE WHEN had_stake_change THEN 1 ELSE 0 END) AS sessions_with_stake_change,
            SUM(count_stake_up)                               AS count_stake_up_events,
            SUM(count_stake_down)                             AS count_stake_down_events,
            {pct} * 100                                       AS pct_sessions_changed
        FROM {as_} {w}
        GROUP BY game_id
        ORDER BY game_id
    """
    return run_query(client, query, env)

# ── Q5 — RTP bucket distribution ──────────────────────────────────────────────
def get_rtp_buckets(client, tables, filters, env):
    ar = _ref(tables, "agg_rounds", env)
    w = _where_rounds(filters)

    # Update this variable
    ftype = "FLOAT64" if env == "BigQuery" else "DOUBLE"
    total = _safe_div("COUNT(*)", f"CAST(SUM(COUNT(*)) OVER () AS {ftype})", env)

    query = f"""
        SELECT
            rtp_bucket,
            COUNT(*)       AS round_count,
            {total} * 100  AS pct_of_all_rounds
        FROM {ar}
        {w}
        GROUP BY rtp_bucket
    """
    return run_query(client, query, env)

# ── Q6 — Spin transitions ──────────────────────────────────────────────────────
def get_spin_transitions(client, tables, filters, env):
    ar = _ref(tables, "agg_rounds", env)
    w = _where_rounds(filters)
    w_ext = w + " AND prev_rtp_bucket IS NOT NULL AND bet_change_direction IS NOT NULL"

    # Update this variable
    ftype = "FLOAT64" if env == "BigQuery" else "DOUBLE"
    total = _safe_div("COUNT(*)", f"CAST(SUM(COUNT(*)) OVER () AS {ftype})", env)

    query = f"""
        SELECT
            prev_rtp_bucket,
            bet_change_direction,
            COUNT(*)       AS transition_count,
            {total} * 100  AS pct
        FROM {ar}
        {w_ext}
        GROUP BY prev_rtp_bucket, bet_change_direction
        ORDER BY prev_rtp_bucket, bet_change_direction
    """
    return run_query(client, query, env)


# ── Q7 — Win amount vs session length ─────────────────────────────────────────

def get_win_vs_session_length(client, tables, filters, env):
    """
    One row per session (up to 2 000 for scatter performance).
    Columns: sessionid, total_won, session_duration_sec, total_spins, game_id
    """
    as_ = _ref(tables, "agg_sessions", env)
    w   = _where_sessions(filters)

    query = f"""
        SELECT
            sessionid,
            total_won,
            session_duration_sec,
            total_spins,
            game_id
        FROM {as_}
        {w}
        LIMIT 2000
    """
    return run_query(client, query, env)


# ── Q8 — Post-win continuation ────────────────────────────────────────────────

def get_post_win_continuation(client, tables, filters, env):
    """
    One row per prev_rtp_bucket with spins-remaining bucket columns.
    Columns: prev_rtp_bucket, no_more_spins, spins_1_to_5, spins_6_to_10,
             spins_11_to_20, spins_21_to_50, spins_51_to_100, spins_100_plus
    """
    ast = _ref(tables, "agg_spin_transitions", env)
    w   = _where_transitions(filters)

    query = f"""
        SELECT
            prev_rtp_bucket,
            SUM(no_more_spins)   AS no_more_spins,
            SUM(spins_1_to_5)    AS spins_1_to_5,
            SUM(spins_6_to_10)   AS spins_6_to_10,
            SUM(spins_11_to_20)  AS spins_11_to_20,
            SUM(spins_21_to_50)  AS spins_21_to_50,
            SUM(spins_51_to_100) AS spins_51_to_100,
            SUM(spins_100_plus)  AS spins_100_plus
        FROM {ast}
        {w}
        GROUP BY prev_rtp_bucket
    """
    return run_query(client, query, env)


# ── Q9 — Hesitation (Seconds per spin) ────────────────────────────────────────

def get_hesitation_distribution(client, tables, filters, env):
    """
    Calculates seconds per spin (hesitation) rounded to the nearest second,
    and counts how many sessions fall into each bucket (capped at 60 seconds).
    """
    as_ = _ref(tables, "agg_sessions", env)
    w = _where_sessions(filters)

    sec_per_spin = _safe_div("session_duration_sec", "total_spins", env)

    query = f"""
        WITH calc AS (
            SELECT 
                ROUND({sec_per_spin}) AS hesitation_sec
            FROM {as_}
            {w}
        )
        SELECT 
            hesitation_sec,
            COUNT(*) as session_count
        FROM calc
        WHERE hesitation_sec IS NOT NULL AND hesitation_sec <= 60
        GROUP BY hesitation_sec
        ORDER BY hesitation_sec
    """
    return run_query(client, query, env)
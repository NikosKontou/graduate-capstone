"""
charts.py
---------
All Matplotlib / Seaborn chart functions for the Player Engagement dashboard.
Each function accepts a pandas DataFrame and returns a matplotlib Figure.
"""

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Shared style
# ---------------------------------------------------------------------------

RTP_BUCKET_ORDER = [
    "No Win", "< Stake Win", "1 to 5x Win", "5 to 10x Win",
    "10 to 20x Win", "20 to 30x Win", "30 to 40x Win", "40 to 50x Win",
    "50 to 60x Win", "60 to 70x Win", "70 to 100x Win", "100x+ Win",
]

SPINS_REMAINING_COLS = [
    "no_more_spins", "spins_1_to_5", "spins_6_to_10",
    "spins_11_to_20", "spins_21_to_50", "spins_51_to_100", "spins_100_plus",
]

SPINS_REMAINING_LABELS = [
    "No more spins", "1–5", "6–10", "11–20", "21–50", "51–100", "100+",
]

BET_CHANGE_COLORS = {
    "Same Stake": "#4C9BE8",
    "Stake Up":   "#2ECC71",
    "Stake Down": "#E74C3C",
}

PALETTE = sns.color_palette("muted")

def _sort_rtp(df: pd.DataFrame, col: str = "rtp_bucket") -> pd.DataFrame:
    """Sort a DataFrame by the canonical RTP bucket order."""
    order = {b: i for i, b in enumerate(RTP_BUCKET_ORDER)}
    df = df.copy()
    df["_sort"] = df[col].map(order).fillna(99)
    return df.sort_values("_sort").drop(columns="_sort")


def _fig(w=12, h=5):
    fig, ax = plt.subplots(figsize=(w, h))
    return fig, ax


# ---------------------------------------------------------------------------
# Q1 / Q2 / Q3  —  KPI cards are rendered directly in app.py (st.metric)
# No chart needed.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Q4  —  Stake variance
# ---------------------------------------------------------------------------

def plot_stake_variance_overall(total_sessions: int, with_change: int, up: int, down: int):
    """
    Donut chart: sessions that had a stake change vs those that didn't.
    Bar inset: up vs down event counts.
    """
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Donut
    ax1 = axes[0]
    unchanged = total_sessions - with_change
    sizes = [with_change, unchanged]
    labels = [f"Changed stake\n({with_change:,})", f"Consistent stake\n({unchanged:,})"]
    colors = ["#2ECC71", "#BDC3C7"]
    wedges, texts, autotexts = ax1.pie(
        sizes, labels=labels, colors=colors,
        autopct="%1.1f%%", startangle=90,
        wedgeprops=dict(width=0.5),
    )
    for at in autotexts:
        at.set_fontsize(11)
    ax1.set_title("Sessions with Stake Change", fontsize=13, fontweight="bold", pad=15)

    # Grouped bar: up vs down counts
    ax2 = axes[1]
    categories = ["Stake Up events", "Stake Down events"]
    values = [up, down]
    bars = ax2.bar(categories, values, color=["#2ECC71", "#E74C3C"], width=0.4)
    for bar, val in zip(bars, values):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(values) * 0.01,
                 f"{val:,}", ha="center", va="bottom", fontsize=11)
    ax2.set_title("Stake Change Events (all sessions)", fontsize=13, fontweight="bold")
    ax2.set_ylabel("Event count")
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    sns.despine(ax=ax2)

    fig.tight_layout()
    return fig


def plot_stake_variance_by_game(df: pd.DataFrame):
    """
    Grouped bar chart: per game_id — sessions with/without stake change,
    plus up/down event breakdown.
    """
    df = df.copy()
    df["game_id"] = df["game_id"].astype(str)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Left: % sessions with stake change
    ax1 = axes[0]
    bars = ax1.bar(df["game_id"], df["pct_sessions_changed"],
                   color=PALETTE[:len(df)], width=0.5)
    for bar, val in zip(bars, df["pct_sessions_changed"]):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                 f"{val:.1f}%", ha="center", va="bottom", fontsize=10)
    ax1.set_title("% Sessions with Stake Change by Game", fontsize=13, fontweight="bold")
    ax1.set_xlabel("Game ID")
    ax1.set_ylabel("% of sessions")
    ax1.set_ylim(0, min(100, df["pct_sessions_changed"].max() * 1.25 + 5))
    sns.despine(ax=ax1)

    # Right: stake up vs down events
    ax2 = axes[1]
    x = np.arange(len(df))
    width = 0.35
    ax2.bar(x - width / 2, df["count_stake_up_events"],   width, label="Stake Up",   color="#2ECC71")
    ax2.bar(x + width / 2, df["count_stake_down_events"], width, label="Stake Down", color="#E74C3C")
    ax2.set_xticks(x)
    ax2.set_xticklabels(df["game_id"])
    ax2.set_title("Stake Up vs Down Events by Game", fontsize=13, fontweight="bold")
    ax2.set_xlabel("Game ID")
    ax2.set_ylabel("Event count")
    ax2.legend()
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    sns.despine(ax=ax2)

    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Q5  —  RTP bucket distribution
# ---------------------------------------------------------------------------

def plot_rtp_buckets(df: pd.DataFrame):
    """Horizontal bar chart of round counts per RTP bucket."""
    df = _sort_rtp(df)

    fig, ax = _fig(12, 6)
    colors = sns.color_palette("RdYlGn", len(df))
    bars = ax.barh(df["rtp_bucket"], df["round_count"], color=colors)

    for bar, pct in zip(bars, df["pct_of_all_rounds"]):
        ax.text(bar.get_width() + max(df["round_count"]) * 0.005,
                bar.get_y() + bar.get_height() / 2,
                f"{pct:.1f}%", va="center", fontsize=9)

    ax.set_title("Round Distribution by RTP Bucket (Q5)", fontsize=14, fontweight="bold")
    ax.set_xlabel("Number of rounds")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.invert_yaxis()
    sns.despine(ax=ax)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Q6  —  Spin transitions (bet change after each round type)
# ---------------------------------------------------------------------------

def plot_spin_transitions(df: pd.DataFrame):
    """
    Stacked 100% bar chart:
    X = prev_rtp_bucket, stacks = Same Stake / Stake Up / Stake Down
    """
    df = _sort_rtp(df, col="prev_rtp_bucket")
    pivot = df.pivot_table(
        index="prev_rtp_bucket", columns="bet_change_direction",
        values="transition_count", aggfunc="sum", fill_value=0,
    )
    # Reorder columns
    col_order = [c for c in ["Same Stake", "Stake Up", "Stake Down"] if c in pivot.columns]
    pivot = pivot[col_order]
    totals = pivot.sum(axis=1)
    pct = pivot.div(totals, axis=0) * 100

    # Restore canonical row order
    present = [b for b in RTP_BUCKET_ORDER if b in pct.index]
    pct = pct.loc[present]

    fig, ax = _fig(13, 6)
    bottom = np.zeros(len(pct))
    for col in pct.columns:
        color = BET_CHANGE_COLORS.get(col, "#95A5A6")
        bars = ax.bar(pct.index, pct[col], bottom=bottom, label=col,
                      color=color, width=0.6)
        # Label segments > 5%
        for bar, val in zip(bars, pct[col]):
            if val > 5:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_y() + bar.get_height() / 2,
                    f"{val:.0f}%", ha="center", va="center",
                    fontsize=8, color="white", fontweight="bold",
                )
        bottom += pct[col].values

    ax.set_title("Bet Change Direction After Each Win Type (Q6)", fontsize=14, fontweight="bold")
    ax.set_xlabel("Previous Round Outcome")
    ax.set_ylabel("% of transitions")
    ax.set_ylim(0, 100)
    ax.legend(title="Next bet", bbox_to_anchor=(1.01, 1), loc="upper left")
    plt.xticks(rotation=35, ha="right")
    sns.despine(ax=ax)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Q7  —  Win amount vs session length (scatter)
# ---------------------------------------------------------------------------

def plot_win_vs_session_length(df: pd.DataFrame):
    """
    Scatter plot: total_won (x) vs session_duration_sec (y),
    coloured by game_id, with a regression line across all points.
    """
    fig, ax = _fig(11, 6)

    games = df["game_id"].unique()
    palette = dict(zip(games, sns.color_palette("tab10", len(games))))

    for game, grp in df.groupby("game_id"):
        ax.scatter(grp["total_won"], grp["session_duration_sec"],
                   alpha=0.4, s=18, label=f"Game {game}",
                   color=palette[game])

    # Overall trend line
    if len(df) > 2:
        m, b = np.polyfit(df["total_won"], df["session_duration_sec"], 1)
        x_line = np.linspace(df["total_won"].min(), df["total_won"].max(), 200)
        ax.plot(x_line, m * x_line + b, color="black", linewidth=1.5,
                linestyle="--", label="Trend (all games)")

    ax.set_title("Win Amount vs Session Length (Q7)", fontsize=14, fontweight="bold")
    ax.set_xlabel("Total won (session)")
    ax.set_ylabel("Session duration (seconds)")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.2f}"))
    ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left")
    sns.despine(ax=ax)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Q8  —  Post-win continuation (how long players continue after each win type)
# ---------------------------------------------------------------------------

def plot_post_win_continuation(df: pd.DataFrame):
    """
    Stacked 100% horizontal bar chart:
    Y = prev_rtp_bucket (win type), stacks = spins-remaining buckets.
    """
    df = _sort_rtp(df, col="prev_rtp_bucket")

    present = [b for b in RTP_BUCKET_ORDER if b in df["prev_rtp_bucket"].values]
    df = df.set_index("prev_rtp_bucket").loc[present]

    # Only keep columns that exist (table may lack some if data is thin)
    cols = [c for c in SPINS_REMAINING_COLS if c in df.columns]
    labels = [SPINS_REMAINING_LABELS[SPINS_REMAINING_COLS.index(c)] for c in cols]

    totals = df[cols].sum(axis=1)
    pct = df[cols].div(totals, axis=0) * 100

    colors = sns.color_palette("Blues_r", len(cols))
    # Override first bucket (quit) with red
    colors[0] = (0.85, 0.25, 0.25)

    fig, ax = plt.subplots(figsize=(13, 7))
    left = np.zeros(len(pct))

    for col, label, color in zip(cols, labels, colors):
        vals = pct[col].values
        bars = ax.barh(pct.index, vals, left=left, label=label,
                       color=color, height=0.6)
        for bar, val in zip(bars, vals):
            if val > 4:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_y() + bar.get_height() / 2,
                    f"{val:.0f}%", ha="center", va="center",
                    fontsize=8, color="white", fontweight="bold",
                )
        left += vals

    ax.set_title("Spins Played After Each Win Type (Q8)", fontsize=14, fontweight="bold")
    ax.set_xlabel("% of occurrences")
    ax.set_xlim(0, 100)
    ax.invert_yaxis()
    ax.legend(title="Spins remaining", bbox_to_anchor=(1.01, 1), loc="upper left")
    sns.despine(ax=ax)
    fig.tight_layout()
    return fig

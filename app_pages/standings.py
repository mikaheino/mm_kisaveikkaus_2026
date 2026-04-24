import base64
import os
import streamlit as st
import pandas as pd

session = st.session_state.snowpark_session

SCHEMA = "MM_KISAVEIKKAUS"
RESULTS_TABLE = f"{SCHEMA}.MM_KISAVEIKKAUS_RESULTS"

# ── Background image ──────────────────────────────────────────────────────────
_img_path = os.path.join(os.path.dirname(__file__), "..", "saku-koivu.jpg")
if os.path.exists(_img_path):
    _b64 = base64.b64encode(open(_img_path, "rb").read()).decode()
    st.markdown(
        f"""
        <style>
        [data-testid="stAppViewContainer"] {{
            background-image: url("data:image/jpeg;base64,{_b64}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        [data-testid="stAppViewContainer"]::before {{
            content: "";
            position: fixed;
            inset: 0;
            background: rgba(5, 10, 30, 0.72);
            pointer-events: none;
            z-index: 0;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

st.title("Standings")


def get_players() -> list:
    """Discover all player prediction tables by naming convention."""
    rows = session.sql(
        f"SHOW TABLES LIKE '%_MM_KISAVEIKKAUS' IN SCHEMA {SCHEMA}"
    ).collect()
    players = []
    for row in rows:
        name = row["name"]
        # Exclude system tables
        if name in ("MM_KISAVEIKKAUS_RESULTS", "MM_KISAVEIKKAUS_SCHEDULE"):
            continue
        # Extract player name: strip the _MM_KISAVEIKKAUS suffix
        player = name.replace("_MM_KISAVEIKKAUS", "")
        if player:
            players.append(player)
    return sorted(players)


def compute_player_points(player: str) -> pd.DataFrame:
    """Compute per-match and total points for a player."""
    table_name = f"{player}_MM_KISAVEIKKAUS"
    sql = f"""
    SELECT
        r.ID,
        r.MATCH,
        r.HOME_TEAM_GOALS AS RESULT_HOME,
        r.AWAY_TEAM_GOALS AS RESULT_AWAY,
        p.HOME_TEAM_GOALS AS PRED_HOME,
        p.AWAY_TEAM_GOALS AS PRED_AWAY,
        CASE
            WHEN r.HOME_TEAM_GOALS IS NULL THEN NULL
            WHEN p.HOME_TEAM_GOALS = r.HOME_TEAM_GOALS
                 AND p.AWAY_TEAM_GOALS = r.AWAY_TEAM_GOALS THEN 3
            WHEN (p.HOME_TEAM_GOALS > p.AWAY_TEAM_GOALS
                  AND r.HOME_TEAM_GOALS > r.AWAY_TEAM_GOALS)
              OR (p.HOME_TEAM_GOALS < p.AWAY_TEAM_GOALS
                  AND r.HOME_TEAM_GOALS < r.AWAY_TEAM_GOALS) THEN 1
            ELSE 0
        END AS POINTS
    FROM {SCHEMA}."{table_name}" p
    INNER JOIN {RESULTS_TABLE} r ON p.ID = r.ID
    WHERE r.MATCH IS NOT NULL
    ORDER BY r.ID
    """
    return session.sql(sql).to_pandas()


# -- Discover players --
players = get_players()

if not players:
    st.info("No predictions have been submitted yet.")
    st.stop()

# Games scored so far
scored_count = session.sql(
    f"SELECT COUNT(*) AS N FROM {RESULTS_TABLE} WHERE HOME_TEAM_GOALS IS NOT NULL"
).collect()[0]["N"]
total_games = session.sql(
    "SELECT COUNT(*) AS N FROM MM_KISAVEIKKAUS.MM_KISAVEIKKAUS_SCHEDULE"
).collect()[0]["N"]
st.caption(f":material/query_stats: Games with results: **{scored_count} / {total_games}**")

# -- Leaderboard --
st.subheader("Leaderboard")

MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}

leaderboard_rows = []
for player in players:
    try:
        df = compute_player_points(player)
        total = int(df["POINTS"].dropna().sum())
        leaderboard_rows.append({"Player": player.title(), "Points": total})
    except Exception:
        pass

if leaderboard_rows:
    leaderboard = pd.DataFrame(leaderboard_rows)
    leaderboard = leaderboard.sort_values("Points", ascending=False).reset_index(drop=True)
    leaderboard.index = leaderboard.index + 1
    leaderboard.index.name = "Rank"
    leaderboard.insert(0, "", leaderboard.index.map(lambda r: MEDALS.get(r, "")))
    st.dataframe(leaderboard, width="stretch")
else:
    st.info("No results available yet to compute standings.")

# -- Per-player detail --
st.divider()
st.subheader("Match Details")

selected_player = st.selectbox(
    "Select a player to see their predictions vs results:",
    options=[p.title() for p in players],
)

if selected_player:
    player_key = selected_player.upper()
    try:
        detail_df = compute_player_points(player_key)
        # Rename for display
        detail_df = detail_df.rename(columns={
            "ID": "#",
            "MATCH": "Match",
            "RESULT_HOME": "Result Home",
            "RESULT_AWAY": "Result Away",
            "PRED_HOME": "Pred Home",
            "PRED_AWAY": "Pred Away",
            "POINTS": "Points",
        })
        st.dataframe(detail_df, width="stretch", hide_index=True)
    except Exception as e:
        st.error(f"Could not load details for {selected_player}: {e}")

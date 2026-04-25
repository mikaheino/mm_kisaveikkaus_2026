import base64
import os
import streamlit as st
import pandas as pd

session = st.session_state.snowpark_session

SCHEMA = "MM_KISAVEIKKAUS"
PREDICTIONS_TABLE = f"{SCHEMA}.MM_KISAVEIKKAUS_PREDICTIONS"
RESULTS_TABLE = f"{SCHEMA}.MM_KISAVEIKKAUS_RESULTS"

_FLAGS = {
    "Austria": "🇦🇹", "Canada": "🇨🇦", "Czech Republic": "🇨🇿",
    "Denmark": "🇩🇰", "Finland": "🇫🇮", "Germany": "🇩🇪",
    "Great Britain": "🇬🇧", "Hungary": "🇭🇺", "Italy": "🇮🇹",
    "Latvia": "🇱🇻", "Norway": "🇳🇴", "Slovakia": "🇸🇰",
    "Slovenia": "🇸🇮", "Sweden": "🇸🇪", "Switzerland": "🇨🇭",
    "United States": "🇺🇸",
}

def flagged(match: str) -> str:
    parts = match.split(" vs ")
    if len(parts) == 2:
        h, a = parts[0].strip(), parts[1].strip()
        return f"{_FLAGS.get(h, '')} {h} vs {_FLAGS.get(a, '')} {a}"
    return match

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
        div[data-baseweb="select"] span {{
            color: #ffffff !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

st.title("Standings")


def email_to_display_name(email: str) -> str:
    """Convert 'first.last@domain' to 'First Last'."""
    local = email.split("@")[0]
    parts = local.replace(".", " ").split()
    return " ".join(p.capitalize() for p in parts)


def get_players() -> list[str]:
    """Get all players who have submitted predictions."""
    rows = session.sql(
        f"SELECT DISTINCT USER_EMAIL FROM {PREDICTIONS_TABLE} ORDER BY USER_EMAIL"
    ).collect()
    return [row["USER_EMAIL"] for row in rows]


def compute_player_points(player_email: str) -> pd.DataFrame:
    """Compute per-match and total points for a player."""
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
    FROM {PREDICTIONS_TABLE} p
    INNER JOIN {RESULTS_TABLE} r ON p.ID = r.ID
    WHERE p.USER_EMAIL = '{player_email}'
      AND r.MATCH IS NOT NULL
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
st.caption(f"Games with results: **{scored_count} / {total_games}**")

# -- Leaderboard --
st.subheader("Leaderboard")

MEDALS = {1: "\U0001f947", 2: "\U0001f948", 3: "\U0001f949"}

leaderboard_rows = []
for player_email in players:
    try:
        df = compute_player_points(player_email)
        total = int(df["POINTS"].dropna().sum())
        leaderboard_rows.append({
            "Player": email_to_display_name(player_email),
            "Points": total,
        })
    except Exception:
        pass

if leaderboard_rows:
    leaderboard = pd.DataFrame(leaderboard_rows)
    leaderboard = leaderboard.sort_values("Points", ascending=False).reset_index(drop=True)
    leaderboard.index = leaderboard.index + 1
    leaderboard.index.name = "Rank"
    leaderboard.insert(0, "", leaderboard.index.map(lambda r: MEDALS.get(r, "")))
    st.dataframe(leaderboard, use_container_width=True)
else:
    st.info("No results available yet to compute standings.")

# -- Per-player detail --
st.divider()
st.subheader("Match Details")

# Build display name → email mapping
player_display_names = [email_to_display_name(e) for e in players]
email_by_display = dict(zip(player_display_names, players))

selected_display = st.selectbox(
    "Select a player to see their predictions vs results:",
    options=player_display_names,
)

if selected_display:
    player_email = email_by_display[selected_display]
    try:
        detail_df = compute_player_points(player_email)
        detail_df = detail_df.rename(columns={
            "ID": "#",
            "MATCH": "Match",
            "RESULT_HOME": "Result Home",
            "RESULT_AWAY": "Result Away",
            "PRED_HOME": "Pred Home",
            "PRED_AWAY": "Pred Away",
            "POINTS": "Points",
        })
        detail_df["Match"] = detail_df["Match"].apply(flagged)
        detail_df = detail_df.set_index("#")
        st.dataframe(detail_df, use_container_width=True)
    except Exception as e:
        st.error(f"Could not load details for {selected_display}: {e}")

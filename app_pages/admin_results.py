import base64
import os
import streamlit as st
import pandas as pd

# ── Background image ──────────────────────────────────────────────────────────
_img_path = os.path.join(os.path.dirname(__file__), "..", "ioag9w7poe8ayrodgmlc.webp")
if os.path.exists(_img_path):
    _b64 = base64.b64encode(open(_img_path, "rb").read()).decode()
    st.markdown(
        f"""
        <style>
        [data-testid="stAppViewContainer"] {{
            background-image: url("data:image/webp;base64,{_b64}");
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

# ── Access control ────────────────────────────────────────────────────────────
# SiS apps run as the owner role, not the viewer's role, so we gate on email.
ADMIN_EMAILS = {
    "mika.heino@recordlydata.com",
    "mikko.sulonen@recordlydata.com",
    "marko.laitinen@recordlydata.com",
}

user_email = st.session_state.get("user_email", "")
if user_email not in ADMIN_EMAILS:
    st.error("You do not have permission to access this page.")
    st.stop()

session = st.session_state.snowpark_session
SCHEMA = "MM_KISAVEIKKAUS"
RESULTS_TABLE = f"{SCHEMA}.MM_KISAVEIKKAUS_RESULTS"
SCHEDULE_TABLE = f"{SCHEMA}.MM_KISAVEIKKAUS_SCHEDULE"

st.title("Admin — Enter Results")

# ── Load schedule + current results ──────────────────────────────────────────
data_df = session.sql(
    f"""
    SELECT s.ID, s.MATCH_DAY, s.MATCH,
           r.HOME_TEAM_GOALS, r.AWAY_TEAM_GOALS
    FROM {SCHEDULE_TABLE} s
    LEFT JOIN {RESULTS_TABLE} r ON s.ID = r.ID
    ORDER BY s.ID
    """
).to_pandas()

total = len(data_df)
filled = int(data_df["HOME_TEAM_GOALS"].notna().sum())

col1, col2 = st.columns([4, 1])
with col1:
    st.progress(filled / total if total > 0 else 0)
with col2:
    st.caption(f"{filled} / {total} results entered")

# ── Grouped editors by match day ──────────────────────────────────────────────
dates = sorted(data_df["MATCH_DAY"].unique())
game_inputs: dict[int, tuple] = {}  # gid -> (home, away)

with st.form("results_form"):
    for date in dates:
        day_df = data_df[data_df["MATCH_DAY"] == date].copy()
        day_ids = day_df["ID"].astype(int).tolist()

        day_complete = day_df["HOME_TEAM_GOALS"].notna().all()
        date_label = pd.to_datetime(str(date)).strftime("%A, %d %b")
        label = (
            f"{date_label} — {len(day_df)} games  \u2713"
            if day_complete
            else f"{date_label} — {len(day_df)} games"
        )

        with st.expander(label, expanded=not day_complete):
            hdr1, hdr2, hdr3 = st.columns([5, 1, 1])
            hdr2.caption("Home")
            hdr3.caption("Away")
            for _, row in day_df.iterrows():
                gid = int(row["ID"])
                h_def = int(row["HOME_TEAM_GOALS"]) if not pd.isna(row["HOME_TEAM_GOALS"]) else 0
                a_def = int(row["AWAY_TEAM_GOALS"]) if not pd.isna(row["AWAY_TEAM_GOALS"]) else 0
                c1, c2, c3 = st.columns([5, 1, 1])
                c1.write(row["MATCH"])
                home = c2.number_input("H", min_value=0, max_value=20, step=1,
                                       value=h_def, key=f"rh_{gid}",
                                       label_visibility="collapsed")
                away = c3.number_input("A", min_value=0, max_value=20, step=1,
                                       value=a_def, key=f"ra_{gid}",
                                       label_visibility="collapsed")
                game_inputs[gid] = (home, away)

    submit = st.form_submit_button("Save results", type="primary")

# ── Handle submission ─────────────────────────────────────────────────────────
if submit:
    try:
        for gid, (home, away) in game_inputs.items():
            session.sql(
                f"UPDATE {RESULTS_TABLE} "
                f"SET HOME_TEAM_GOALS = {home}, AWAY_TEAM_GOALS = {away} "
                f"WHERE ID = {gid}"
            ).collect()
        st.success(f"{len(game_inputs)} result(s) saved.")
        st.rerun()
    except Exception as e:
        st.error(f"Error saving results: {e}")

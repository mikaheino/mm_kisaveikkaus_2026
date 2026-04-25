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
day_editors: dict[str, dict] = {}

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
            edit_df = pd.DataFrame({
                "ID": day_ids,
                "MATCH": day_df["MATCH"].tolist(),
                "Home Goals": [
                    None if pd.isna(v) else int(v)
                    for v in day_df["HOME_TEAM_GOALS"].tolist()
                ],
                "Away Goals": [
                    None if pd.isna(v) else int(v)
                    for v in day_df["AWAY_TEAM_GOALS"].tolist()
                ],
            })

            edited = st.data_editor(
                edit_df,
                key=f"results_{str(date).replace('-', '_')}",
                num_rows="fixed",
                disabled=["ID", "MATCH"],
                column_config={
                    "ID": None,
                    "MATCH": st.column_config.TextColumn("Match"),
                    "Home Goals": st.column_config.NumberColumn(
                        "Home Goals", min_value=0, max_value=20, step=1
                    ),
                    "Away Goals": st.column_config.NumberColumn(
                        "Away Goals", min_value=0, max_value=20, step=1
                    ),
                },
                hide_index=True,
            )
            day_editors[str(date)] = {"edited": edited, "ids": day_ids}

    submit = st.form_submit_button("Save results", type="primary", icon=":material/save:")

# ── Handle submission ─────────────────────────────────────────────────────────
if submit:
    updates = []
    for date_str, entry in day_editors.items():
        edited_df = entry["edited"]
        ids = entry["ids"]
        for idx, gid in enumerate(ids):
            erow = edited_df.iloc[idx]
            home = erow["Home Goals"]
            away = erow["Away Goals"]
            # Only include rows where both values are filled
            if not pd.isna(home) and not pd.isna(away):
                updates.append((gid, int(home), int(away)))

    if not updates:
        st.warning("No complete results to save — fill in both home and away goals for each game.")
    else:
        try:
            for gid, home, away in updates:
                session.sql(
                    f"UPDATE {RESULTS_TABLE} "
                    f"SET HOME_TEAM_GOALS = {home}, AWAY_TEAM_GOALS = {away} "
                    f"WHERE ID = {gid}"
                ).collect()
            st.success(f":material/check_circle: {len(updates)} result(s) saved.")
            st.rerun()
        except Exception as e:
            st.error(f"Error saving results: {e}")

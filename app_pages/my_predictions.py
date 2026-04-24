import streamlit as st
import pandas as pd
from datetime import datetime


session = st.session_state.snowpark_session
SCHEMA = "MM_KISAVEIKKAUS"
PREDICTIONS_TABLE = f"{SCHEMA}.MM_KISAVEIKKAUS_PREDICTIONS"


def email_to_display_name(email: str) -> str:
    """Convert 'first.last@domain' to 'First Last'."""
    local = email.split("@")[0]
    parts = local.replace(".", " ").split()
    return " ".join(p.capitalize() for p in parts)


# ── Auto-identify user ──────────────────────────────────────────────────────

user_email = session.sql("SELECT CURRENT_USER()").collect()[0][0].lower()
display_name = email_to_display_name(user_email)

st.subheader(f"Welcome, {display_name}")


def get_schedule():
    return session.sql(
        f"SELECT ID, MATCH_DAY, MATCH FROM {SCHEMA}.MM_KISAVEIKKAUS_SCHEDULE ORDER BY ID"
    ).to_pandas()


schedule_df = get_schedule()

# ── Load existing predictions ────────────────────────────────────────────────

existing_preds: dict[int, tuple] = {}
pred_rows = session.sql(
    f"SELECT ID, HOME_TEAM_GOALS, AWAY_TEAM_GOALS FROM {PREDICTIONS_TABLE} "
    f"WHERE USER_EMAIL = '{user_email}' ORDER BY ID"
).to_pandas()

for _, row in pred_rows.iterrows():
    home = row["HOME_TEAM_GOALS"]
    away = row["AWAY_TEAM_GOALS"]
    existing_preds[int(row["ID"])] = (
        None if pd.isna(home) else home,
        None if pd.isna(away) else away,
    )

is_new = len(existing_preds) == 0

# ── Progress indicator ───────────────────────────────────────────────────────

total = len(schedule_df)
filled = sum(
    1 for gid in schedule_df["ID"].astype(int)
    if existing_preds.get(gid, (None, None))[0] is not None
)

col1, col2 = st.columns([4, 1])
with col1:
    st.progress(filled / total if total > 0 else 0)
with col2:
    st.caption(f"{filled} / {total} games")

# ── Games grouped by match day ───────────────────────────────────────────────

dates = sorted(schedule_df["MATCH_DAY"].unique())
upcoming_editors: dict[str, dict] = {}

with st.form("prediction_form"):
    for date in dates:
        day_df = schedule_df[schedule_df["MATCH_DAY"] == date].copy()
        day_ids = day_df["ID"].astype(int).tolist()

        # Collapse if user already has all predictions filled for this day
        day_complete = bool(existing_preds) and all(
            existing_preds.get(gid, (None, None))[0] is not None for gid in day_ids
        )

        date_label = pd.to_datetime(str(date)).strftime("%A, %d %b")
        date_key = str(date).replace("-", "_")

        label = (
            f"{date_label} — {len(day_df)} games  \u2713"
            if day_complete
            else f"{date_label} — {len(day_df)} games"
        )

        with st.expander(label, expanded=not day_complete):
            edit_df = pd.DataFrame({
                "ID": day_ids,
                "MATCH": day_df["MATCH"].tolist(),
                "Home Goals": [existing_preds.get(gid, (None, None))[0] for gid in day_ids],
                "Away Goals": [existing_preds.get(gid, (None, None))[1] for gid in day_ids],
            })

            edited = st.data_editor(
                edit_df,
                key=f"editor_{user_email}_{date_key}",
                width="stretch",
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
            upcoming_editors[date_key] = {"edited": edited, "ids": day_ids, "date": date}

    submit_label = "Save predictions" if is_new else "Update predictions"
    submit = st.form_submit_button(submit_label, type="primary", icon=":material/save:")

# ── Handle submission ────────────────────────────────────────────────────────

if submit:
    # Collect all edited rows
    rows_out = []
    for date_key, entry in upcoming_editors.items():
        edited_df = entry["edited"]
        ids = entry["ids"]
        day_schedule = schedule_df[schedule_df["MATCH_DAY"] == entry["date"]]
        for idx, gid in enumerate(ids):
            srow = day_schedule[day_schedule["ID"] == gid].iloc[0]
            erow = edited_df.iloc[idx]
            rows_out.append({
                "USER_EMAIL": user_email,
                "ID": gid,
                "MATCH_DAY": srow["MATCH_DAY"],
                "MATCH": srow["MATCH"],
                "HOME_TEAM_GOALS": erow["Home Goals"],
                "AWAY_TEAM_GOALS": erow["Away Goals"],
            })

    final_df = pd.DataFrame(rows_out).sort_values("ID").reset_index(drop=True)

    if final_df["HOME_TEAM_GOALS"].isna().any():
        st.error("Missing home goal predictions — please fill all games.")
    elif final_df["AWAY_TEAM_GOALS"].isna().any():
        st.error("Missing away goal predictions — please fill all games.")
    else:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            # Delete existing predictions for this user, then insert new ones
            session.sql(
                f"DELETE FROM {PREDICTIONS_TABLE} WHERE USER_EMAIL = '{user_email}'"
            ).collect()

            # Build MERGE-style insert using VALUES
            values_parts = []
            for _, r in final_df.iterrows():
                values_parts.append(
                    f"('{r['USER_EMAIL']}', {int(r['ID'])}, '{r['MATCH_DAY']}', "
                    f"'{r['MATCH']}', {int(r['HOME_TEAM_GOALS'])}, "
                    f"{int(r['AWAY_TEAM_GOALS'])}, '{now}')"
                )

            insert_sql = (
                f"INSERT INTO {PREDICTIONS_TABLE} "
                f"(USER_EMAIL, ID, MATCH_DAY, MATCH, HOME_TEAM_GOALS, AWAY_TEAM_GOALS, INSERTED) "
                f"VALUES {', '.join(values_parts)}"
            )
            session.sql(insert_sql).collect()

            st.success(f":material/check_circle: Predictions for **{display_name}** saved!")
            st.rerun()
        except Exception as e:
            st.error(f"Error saving predictions: {e}")

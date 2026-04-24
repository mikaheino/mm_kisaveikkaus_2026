import streamlit as st
import re
import pandas as pd
from datetime import datetime


def clean_name(s: str) -> str:
    return re.sub(r"\s+", "", s).upper()


def validate_name(name: str) -> bool:
    return bool(re.match(r"^[A-Z0-9_]+$", name)) and len(name) >= 2


session = st.session_state.snowpark_session
SCHEMA = "MM_KISAVEIKKAUS"


def get_players():
    rows = session.sql(
        f"SHOW TABLES LIKE '%_MM_KISAVEIKKAUS' IN SCHEMA {SCHEMA}"
    ).collect()
    players = []
    for row in rows:
        name = row["name"]
        if name not in ("MM_KISAVEIKKAUS_RESULTS", "MM_KISAVEIKKAUS_SCHEDULE"):
            player = name.replace("_MM_KISAVEIKKAUS", "")
            if player:
                players.append(player)
    return sorted(players)


def get_schedule():
    return session.sql(
        f"SELECT ID, MATCH_DAY, MATCH FROM {SCHEMA}.MM_KISAVEIKKAUS_SCHEDULE ORDER BY ID"
    ).to_pandas()


# ── Who are you? ──────────────────────────────────────────────────────────────

players = get_players()
schedule_df = get_schedule()

NEW_PARTICIPANT = "— New participant —"
options = [NEW_PARTICIPANT] + [p.title() for p in players]

selection = st.selectbox("Select your name:", options=options)

if selection == NEW_PARTICIPANT:
    contestant_raw = st.text_input(
        "Your name",
        max_chars=20,
        placeholder="Enter your name (letters and numbers only)",
    )
    contestant = clean_name(contestant_raw) if contestant_raw else ""
    is_new = True
else:
    contestant = clean_name(selection)
    is_new = False

if not contestant:
    st.info('Select your name from the list above, or choose "New participant" to register.')
    st.stop()

if is_new and not validate_name(contestant):
    st.error("Name must contain only letters, numbers, or underscores (min 2 chars).")
    st.stop()

table_name = f"{contestant}_MM_KISAVEIKKAUS"

# ── Load existing predictions ─────────────────────────────────────────────────

existing_preds: dict[int, tuple] = {}
if not is_new:
    existing = session.sql(
        f"SHOW TABLES LIKE '{table_name}' IN SCHEMA {SCHEMA}"
    ).collect()
    if len(existing) == 0:
        st.warning(
            f"No predictions found for **{contestant.title()}**. "
            'If you are new, select "New participant" from the dropdown.'
        )
        st.stop()
    pred_df = session.sql(
        f'SELECT ID, HOME_TEAM_GOALS, AWAY_TEAM_GOALS FROM {SCHEMA}."{table_name}" ORDER BY ID'
    ).to_pandas()
    for _, row in pred_df.iterrows():
        home = row["HOME_TEAM_GOALS"]
        away = row["AWAY_TEAM_GOALS"]
        existing_preds[int(row["ID"])] = (
            None if pd.isna(home) else home,
            None if pd.isna(away) else away,
        )

# ── Progress indicator ────────────────────────────────────────────────────────

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

# ── Games grouped by match day ────────────────────────────────────────────────

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
            f"{date_label} — {len(day_df)} games  ✓"
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
                key=f"editor_{contestant}_{date_key}",
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
            upcoming_editors[f"{contestant}_{date_key}"] = {"edited": edited, "ids": day_ids, "date": date}

    submit_label = "Save predictions" if is_new else "Update predictions"
    submit = st.form_submit_button(submit_label, type="primary", icon=":material/save:")

# ── Handle submission ─────────────────────────────────────────────────────────

if submit:
    if is_new:
        existing = session.sql(
            f"SHOW TABLES LIKE '{table_name}' IN SCHEMA {SCHEMA}"
        ).collect()
        if len(existing) > 0:
            st.error(
                f"**{contestant.title()}** already has predictions. "
                "Select your name from the dropdown to update them."
            )
            st.stop()

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
        final_df["INSERTED"] = now
        try:
            session.write_pandas(
                final_df,
                table_name,
                schema=SCHEMA,
                auto_create_table=True,
                overwrite=True,
            )
            st.success(f":material/check_circle: Predictions for **{contestant.title()}** saved!")
            st.rerun()
        except Exception as e:
            st.error(f"Error saving predictions: {e}")

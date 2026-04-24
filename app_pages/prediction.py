import streamlit as st
import re
from datetime import datetime


def clean_name(s: str) -> str:
    """Remove whitespace and uppercase the contestant name."""
    return re.sub(r"\s+", "", s).upper()


def validate_name(name: str) -> bool:
    """Ensure the name is alphanumeric only (no SQL injection risk)."""
    return bool(re.match(r"^[A-Z0-9_]+$", name)) and len(name) >= 2


session = st.session_state.snowpark_session

st.title("Submit Prediction")

# -- Load blank schedule --
schedule_df = session.sql(
    "SELECT ID, MATCH_DAY, MATCH, HOME_TEAM_GOALS, AWAY_TEAM_GOALS "
    "FROM MM_KISAVEIKKAUS.MM_KISAVEIKKAUS_SCHEDULE ORDER BY ID"
).to_pandas()

# -- Contestant name input --
contestant_raw = st.text_input(
    "Your name",
    max_chars=20,
    placeholder="Enter your contestant name",
)
contestant = clean_name(contestant_raw) if contestant_raw else ""

# -- Data editor for predictions --
with st.form("prediction_form"):
    st.caption("Fill in your predicted score for each match (home and away goals).")
    edited = st.data_editor(
        schedule_df,
        width="stretch",
        height=2000,
        num_rows="fixed",
        disabled=["ID", "MATCH_DAY", "MATCH"],
        column_config={
            "ID": st.column_config.NumberColumn("ID", width="small"),
            "MATCH_DAY": st.column_config.DateColumn("Date", width="small"),
            "MATCH": st.column_config.TextColumn("Match"),
            "HOME_TEAM_GOALS": st.column_config.NumberColumn(
                "Home Goals", min_value=0, max_value=20, step=1
            ),
            "AWAY_TEAM_GOALS": st.column_config.NumberColumn(
                "Away Goals", min_value=0, max_value=20, step=1
            ),
        },
    )
    submit = st.form_submit_button("Save prediction", type="primary")

if submit:
    if not contestant:
        st.error("Please enter your contestant name.")
    elif not validate_name(contestant):
        st.error("Name must contain only letters, numbers, or underscores (min 2 chars).")
    elif edited["HOME_TEAM_GOALS"].isna().any():
        st.error("Missing home goal predictions -- please fill all rows.")
    elif edited["AWAY_TEAM_GOALS"].isna().any():
        st.error("Missing away goal predictions -- please fill all rows.")
    else:
        table_name = f"{contestant}_MM_KISAVEIKKAUS"
        # Check if table already exists
        existing = session.sql(
            f"SHOW TABLES LIKE '{table_name}' IN SCHEMA MM_KISAVEIKKAUS"
        ).collect()
        if len(existing) > 0:
            st.error(
                f"A prediction for **{contestant}** already exists. "
                "Use the **Update Prediction** page to modify it."
            )
        else:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            edited["INSERTED"] = now
            try:
                session.write_pandas(
                    edited,
                    table_name,
                    schema="MM_KISAVEIKKAUS",
                    auto_create_table=True,
                    overwrite=True,
                )
                st.success(f"Predictions for **{contestant}** saved successfully!")
            except Exception as e:
                st.error(f"Error saving predictions: {e}")

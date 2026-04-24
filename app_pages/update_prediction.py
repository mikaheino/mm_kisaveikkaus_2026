import streamlit as st
import re
from datetime import datetime


def clean_name(s: str) -> str:
    """Remove whitespace and uppercase the contestant name."""
    return re.sub(r"\s+", "", s).upper()


def validate_name(name: str) -> bool:
    """Ensure the name is alphanumeric only."""
    return bool(re.match(r"^[A-Z0-9_]+$", name)) and len(name) >= 2


session = st.session_state.snowpark_session

st.title("Update Prediction")

# -- Contestant name input --
contestant_raw = st.text_input(
    "Your name",
    max_chars=20,
    placeholder="Enter your contestant name to load predictions",
)
contestant = clean_name(contestant_raw) if contestant_raw else ""

if not contestant:
    st.info("Enter your contestant name above to load your existing predictions.")
    st.stop()

if not validate_name(contestant):
    st.error("Name must contain only letters, numbers, or underscores (min 2 chars).")
    st.stop()

# -- Check if prediction table exists --
table_name = f"{contestant}_MM_KISAVEIKKAUS"
existing = session.sql(
    f"SHOW TABLES LIKE '{table_name}' IN SCHEMA MM_KISAVEIKKAUS"
).collect()

if len(existing) == 0:
    st.warning(
        f"No predictions found for **{contestant}**. "
        "Please submit your predictions on the **Submit Prediction** page first."
    )
    st.stop()

# -- Load existing predictions --
prediction_df = session.sql(
    f"SELECT ID, MATCH_DAY, MATCH, HOME_TEAM_GOALS, AWAY_TEAM_GOALS "
    f'FROM MM_KISAVEIKKAUS."{table_name}" ORDER BY ID'
).to_pandas()

with st.form("update_form"):
    st.caption("Edit your predictions below, then click save to overwrite.")
    edited = st.data_editor(
        prediction_df,
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
    submit = st.form_submit_button("Overwrite prediction", type="primary")

if submit:
    if edited["HOME_TEAM_GOALS"].isna().any():
        st.error("Missing home goal predictions -- please fill all rows.")
    elif edited["AWAY_TEAM_GOALS"].isna().any():
        st.error("Missing away goal predictions -- please fill all rows.")
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
            st.success(f"Predictions for **{contestant}** updated successfully!")
        except Exception as e:
            st.error(f"Error updating predictions: {e}")

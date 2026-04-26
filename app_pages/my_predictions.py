import base64
import os
import streamlit as st
import pandas as pd
from datetime import datetime
from trivia import MATCH_TRIVIA

# ── Background image ──────────────────────────────────────────────────────────
_img_path = os.path.join(os.path.dirname(__file__), "..", "assets", "ioag9w7poe8ayrodgmlc.webp")
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

session = st.session_state.snowpark_session
SCHEMA = "MM_KISAVEIKKAUS"
PREDICTIONS_TABLE = f"{SCHEMA}.MM_KISAVEIKKAUS_PREDICTIONS"

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


def email_to_display_name(email: str) -> str:
    """Convert 'first.last@domain' to 'First Last'."""
    local = email.split("@")[0]
    parts = local.replace(".", " ").split()
    return " ".join(p.capitalize() for p in parts)


# ── Auto-identify user ──────────────────────────────────────────────────────

user_email = st.session_state.get("user_email") or session.sql("SELECT CURRENT_USER()").collect()[0][0].lower()
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
all_inputs: dict[int, tuple] = {}  # gid -> (home_goals, away_goals)

with st.form("prediction_form"):
    for date in dates:
        day_df = schedule_df[schedule_df["MATCH_DAY"] == date].copy()
        day_ids = day_df["ID"].astype(int).tolist()

        # Collapse if user already has all predictions filled for this day
        day_complete = bool(existing_preds) and all(
            existing_preds.get(gid, (None, None))[0] is not None for gid in day_ids
        )

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
                h_def = str(int(existing_preds[gid][0])) if gid in existing_preds and existing_preds[gid][0] is not None else ""
                a_def = str(int(existing_preds[gid][1])) if gid in existing_preds and existing_preds[gid][1] is not None else ""
                c1, c2, c3 = st.columns([5, 1, 1])
                c1.write(flagged(row["MATCH"]))
                fact = MATCH_TRIVIA.get(row["MATCH"], "")
                if fact:
                    c1.caption(fact)
                home = c2.text_input("H", value=h_def, key=f"h_{gid}",
                                     label_visibility="collapsed")
                away = c3.text_input("A", value=a_def, key=f"a_{gid}",
                                     label_visibility="collapsed")
                all_inputs[gid] = (home, away)

    submit_label = "Save predictions" if is_new else "Update predictions"
    submit = st.form_submit_button(submit_label, type="primary")

# ── Handle submission ────────────────────────────────────────────────────────

if submit:
    # Validate all inputs are integers 0-20
    errors = []
    parsed: dict[int, tuple] = {}
    for gid, (h_str, a_str) in all_inputs.items():
        try:
            h, a = int(h_str.strip()), int(a_str.strip())
            if not (0 <= h <= 20 and 0 <= a <= 20):
                raise ValueError
            parsed[gid] = (h, a)
        except (ValueError, AttributeError):
            srow = schedule_df[schedule_df["ID"] == gid].iloc[0]
            errors.append(srow["MATCH"])
    if errors:
        st.error(f"Invalid or missing scores for: {', '.join(errors)}")
    else:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rows_out = []
        for gid, (home, away) in parsed.items():
            srow = schedule_df[schedule_df["ID"] == gid].iloc[0]
            rows_out.append({
                "USER_EMAIL": user_email,
                "ID": gid,
                "MATCH_DAY": srow["MATCH_DAY"],
                "MATCH": srow["MATCH"],
                "HOME_TEAM_GOALS": home,
                "AWAY_TEAM_GOALS": away,
            })
        final_df = pd.DataFrame(rows_out).sort_values("ID").reset_index(drop=True)
        try:
            session.sql(
                f"DELETE FROM {PREDICTIONS_TABLE} WHERE USER_EMAIL = '{user_email}'"
            ).collect()
            values_parts = [
                f"('{r['USER_EMAIL']}', {int(r['ID'])}, '{r['MATCH_DAY']}', "
                f"'{r['MATCH']}', {int(r['HOME_TEAM_GOALS'])}, "
                f"{int(r['AWAY_TEAM_GOALS'])}, '{now}')"
                for _, r in final_df.iterrows()
            ]
            session.sql(
                f"INSERT INTO {PREDICTIONS_TABLE} "
                f"(USER_EMAIL, ID, MATCH_DAY, MATCH, HOME_TEAM_GOALS, AWAY_TEAM_GOALS, INSERTED) "
                f"VALUES {', '.join(values_parts)}"
            ).collect()
            st.success(f"Predictions for **{display_name}** saved!")
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Error saving predictions: {e}")

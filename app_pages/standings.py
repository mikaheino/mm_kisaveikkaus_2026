import base64
import os
import streamlit as st
import pandas as pd

session = st.session_state.snowpark_session

SCHEMA = "MM_KISAVEIKKAUS"
PREDICTIONS_TABLE = f"{SCHEMA}.MM_KISAVEIKKAUS_PREDICTIONS"
RESULTS_TABLE = f"{SCHEMA}.MM_KISAVEIKKAUS_RESULTS"

_FLAGS = {
    "Itävalta": "🇦🇹", "Kanada": "🇨🇦", "Tšekki": "🇨🇿",
    "Tanska": "🇩🇰", "Suomi": "🇫🇮", "Saksa": "🇩🇪",
    "Iso-Britannia": "🇬🇧", "Unkari": "🇭🇺", "Italia": "🇮🇹",
    "Latvia": "🇱🇻", "Norja": "🇳🇴", "Slovakia": "🇸🇰",
    "Slovenia": "🇸🇮", "Ruotsi": "🇸🇪", "Sveitsi": "🇨🇭",
    "Yhdysvallat": "🇺🇸",
}

_FI_DAYS = ["Maanantai","Tiistai","Keskiviikko","Torstai","Perjantai","Lauantai","Sunnuntai"]
_FI_MONTHS = ["","tammikuuta","helmikuuta","maaliskuuta","huhtikuuta","toukokuuta","kesäkuuta",
               "heinäkuuta","elokuuta","syyskuuta","lokakuuta","marraskuuta","joulukuuta"]


def _fi_date(d) -> str:
    dt = pd.to_datetime(str(d))
    return f"{_FI_DAYS[dt.weekday()]} {dt.day}. {_FI_MONTHS[dt.month]}"


def flagged(match: str) -> str:
    parts = match.split(" vs ")
    if len(parts) == 2:
        h, a = parts[0].strip(), parts[1].strip()
        return f"{_FLAGS.get(h, '')} {h} vs {_FLAGS.get(a, '')} {a}"
    return match


def email_to_display_name(email: str) -> str:
    local = email.split("@")[0]
    parts = local.replace(".", " ").split()
    return " ".join(p.capitalize() for p in parts)


# ── Background image ──────────────────────────────────────────────────────────
_img_path = os.path.join(os.path.dirname(__file__), "..", "assets", "saku-koivu.jpg")
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

st.title("Tilanne")


def get_players() -> list[str]:
    rows = session.sql(
        f"SELECT DISTINCT USER_EMAIL FROM {PREDICTIONS_TABLE} ORDER BY USER_EMAIL"
    ).collect()
    return [row["USER_EMAIL"] for row in rows]


def compute_player_points(player_email: str) -> pd.DataFrame:
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


players = get_players()

if not players:
    st.info("Ei veikkauksia vielä.")
    st.stop()

scored_count = session.sql(
    f"SELECT COUNT(*) AS N FROM {RESULTS_TABLE} WHERE HOME_TEAM_GOALS IS NOT NULL"
).collect()[0]["N"]
total_games = session.sql(
    "SELECT COUNT(*) AS N FROM MM_KISAVEIKKAUS.MM_KISAVEIKKAUS_SCHEDULE"
).collect()[0]["N"]
st.caption(f"Otteluja tuloksilla: **{scored_count} / {total_games}**")

# ── Pistetaulukko ─────────────────────────────────────────────────────────────
st.subheader("Pistetaulukko")
st.caption("Sija lasketaan ottelukohtaisista pisteistä: 3 = täysosuma, 1 = oikea voittaja, 0 = väärä.")

current_user = st.session_state.get("user_email", "")

leaderboard_rows = []
for player_email in players:
    try:
        df = compute_player_points(player_email)
        total = int(df["POINTS"].dropna().sum())
        leaderboard_rows.append({
            "email": player_email,
            "name": email_to_display_name(player_email),
            "points": total,
        })
    except Exception:
        pass

if leaderboard_rows:
    leaderboard_rows.sort(key=lambda r: r["points"], reverse=True)
    rank_html_parts = []
    for i, row in enumerate(leaderboard_rows, start=1):
        is_me = row["email"] == current_user
        bg = "rgba(30, 70, 165, 0.92)" if is_me else "rgba(20, 50, 115, 0.75)"
        marker = " <span style='color:#7ec8ff;font-size:0.78rem;'>(sinä)</span>" if is_me else ""
        rank_html_parts.append(
            f"<div style=\"display:flex;align-items:center;justify-content:space-between;"
            f"padding:8px 14px;margin-bottom:4px;background:{bg};"
            f"box-shadow:inset -1px -1px rgba(0,0,0,0.85),inset 1px 1px rgba(170,200,255,0.55),"
            f"inset -2px -2px rgba(0,0,20,0.55),inset 2px 2px rgba(140,175,255,0.28);"
            f"color:#dce8f5;font-family:'Roboto',Arial,sans-serif;\">"
            f"<span><span style='display:inline-block;width:2.2rem;color:#7ec8ff;font-weight:700;'>"
            f"{i}.</span>{row['name']}{marker}</span>"
            f"<span style='font-weight:700;font-variant-numeric:tabular-nums;'>{row['points']} p</span>"
            f"</div>"
        )
    st.markdown("".join(rank_html_parts), unsafe_allow_html=True)
else:
    st.info("Tuloksia ei vielä saatavilla.")

# ── Ottelutiedot ──────────────────────────────────────────────────────────────
st.divider()
st.subheader("Ottelutiedot")
st.caption("Valitse pelaaja nähdäksesi hänen veikkauksensa ottelukohtaisesti.")

player_display_names = [email_to_display_name(e) for e in players]
email_by_display = dict(zip(player_display_names, players))

default_idx = 0
if current_user:
    me_display = email_to_display_name(current_user)
    if me_display in player_display_names:
        default_idx = player_display_names.index(me_display)

selected_display = st.selectbox(
    "Pelaaja",
    options=player_display_names,
    index=default_idx,
    label_visibility="collapsed",
)

if selected_display:
    player_email = email_by_display[selected_display]
    try:
        detail_df = compute_player_points(player_email)
    except Exception as e:
        st.error(f"Tietojen lataus epäonnistui ({selected_display}): {e}")
        detail_df = None

    if detail_df is not None and len(detail_df) > 0:
        # Need MATCH_DAY for grouping — fetch from schedule
        sched_df = session.sql(
            f"SELECT ID, MATCH_DAY FROM {SCHEMA}.MM_KISAVEIKKAUS_SCHEDULE ORDER BY ID"
        ).to_pandas()[["ID", "MATCH_DAY"]]
        merged = detail_df.merge(sched_df, on="ID", how="left")
        merged = merged.sort_values("ID")

        total_pts = int(merged["POINTS"].dropna().sum())
        st.caption(f"**{selected_display}** – yhteensä **{total_pts}** pistettä.")

        dates = sorted(merged["MATCH_DAY"].dropna().unique())
        for date in dates:
            day_rows = merged[merged["MATCH_DAY"] == date]
            day_pts = int(day_rows["POINTS"].dropna().sum())
            scored = int(day_rows["POINTS"].notna().sum())
            total = len(day_rows)
            date_label = _fi_date(date)
            label = f"{date_label} — {scored}/{total} ottelua tuloksella · {day_pts} p"
            with st.expander(label, expanded=False):
                hdr1, hdr2, hdr3, hdr4 = st.columns([5, 2, 2, 1])
                hdr2.caption("Veikkaus")
                hdr3.caption("Tulos")
                hdr4.caption("Pisteet")
                for _, row in day_rows.iterrows():
                    c1, c2, c3, c4 = st.columns([5, 2, 2, 1])
                    c1.write(flagged(row["MATCH"]))

                    ph, pa = row["PRED_HOME"], row["PRED_AWAY"]
                    pred_str = (
                        f"{int(ph)} – {int(pa)}"
                        if not pd.isna(ph) and not pd.isna(pa)
                        else "–"
                    )
                    c2.write(pred_str)

                    rh, ra = row["RESULT_HOME"], row["RESULT_AWAY"]
                    if not pd.isna(rh) and not pd.isna(ra):
                        c3.write(f"{int(rh)} – {int(ra)}")
                    else:
                        c3.write("—")

                    pts = row["POINTS"]
                    if pd.isna(pts):
                        badge = "<span style='color:#8899aa;'>—</span>"
                    elif int(pts) == 3:
                        badge = (
                            "<span style='background:rgba(40,160,80,0.85);color:#dce8f5;"
                            "padding:2px 8px;font-weight:700;'>3</span>"
                        )
                    elif int(pts) == 1:
                        badge = (
                            "<span style='background:rgba(200,160,40,0.85);color:#07111f;"
                            "padding:2px 8px;font-weight:700;'>1</span>"
                        )
                    else:
                        badge = (
                            "<span style='background:rgba(120,40,40,0.75);color:#dce8f5;"
                            "padding:2px 8px;font-weight:700;'>0</span>"
                        )
                    c4.markdown(badge, unsafe_allow_html=True)
    elif detail_df is not None:
        st.info("Pelaajalla ei ole vielä veikkauksia tuloksellisiin otteluihin.")

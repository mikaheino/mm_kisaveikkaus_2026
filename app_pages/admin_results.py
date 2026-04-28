import base64
import os
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

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

# ── Access control ────────────────────────────────────────────────────────────
# SiS apps run as the owner role, not the viewer's role, so we gate on email.
ADMIN_EMAILS = {
    "mika.heino@recordlydata.com",
    "mikko.sulonen@recordlydata.com",
    "marko.laitinen@recordlydata.com",
}

user_email = st.session_state.get("user_email", "")
if user_email not in ADMIN_EMAILS:
    st.error("Ei oikeuksia.")
    st.stop()

session = st.session_state.snowpark_session
SCHEMA = "MM_KISAVEIKKAUS"
SCHEDULE_TABLE = f"{SCHEMA}.MM_KISAVEIKKAUS_SCHEDULE"
RESULTS_TABLE = f"{SCHEMA}.MM_KISAVEIKKAUS_RESULTS"
PLAYOFF_RESULTS_TABLE = f"{SCHEMA}.MM_KISAVEIKKAUS_PLAYOFF_RESULTS"

_FLAGS = {
    "Itävalta": "🇦🇹", "Kanada": "🇨🇦", "Tšekki": "🇨🇿",
    "Tanska": "🇩🇰", "Suomi": "🇫🇮", "Saksa": "🇩🇪",
    "Iso-Britannia": "🇬🇧", "Unkari": "🇭🇺", "Italia": "🇮🇹",
    "Latvia": "🇱🇻", "Norja": "🇳🇴", "Slovakia": "🇸🇰",
    "Slovenia": "🇸🇮", "Ruotsi": "🇸🇪", "Sveitsi": "🇨🇭",
    "Yhdysvallat": "🇺🇸",
}

TEAMS = sorted(_FLAGS.keys())

_PLAYOFF_COLS = [
    "QF_TEAM_1", "QF_TEAM_2", "QF_TEAM_3", "QF_TEAM_4",
    "QF_TEAM_5", "QF_TEAM_6", "QF_TEAM_7", "QF_TEAM_8",
    "SF_TEAM_1", "SF_TEAM_2", "SF_TEAM_3", "SF_TEAM_4",
    "FINALIST_1", "FINALIST_2",
    "CHAMPION", "TOP_SCORER", "TOP_POINTS",
]

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


st.title("Syötä tulokset")

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
    st.caption(f"{filled} / {total} tulosta syötetty")

# ── Group-stage results editor ────────────────────────────────────────────────
st.subheader("Alkulohkon tulokset")
st.caption("Syötä jokaisen ottelun lopputulos (koti – vieras).")

dates = sorted(data_df["MATCH_DAY"].unique())
game_inputs: dict[int, tuple] = {}

with st.form("results_form"):
    for date in dates:
        day_df = data_df[data_df["MATCH_DAY"] == date].copy()
        day_ids = day_df["ID"].astype(int).tolist()

        day_complete = day_df["HOME_TEAM_GOALS"].notna().all()
        date_label = _fi_date(date)
        label = (
            f"{date_label} — {len(day_df)} ottelua  ✓"
            if day_complete
            else f"{date_label} — {len(day_df)} ottelua"
        )

        with st.expander(label, expanded=not day_complete):
            hdr1, hdr2, hdr3 = st.columns([5, 1, 1])
            hdr2.caption("Koti")
            hdr3.caption("Vieras")
            for _, row in day_df.iterrows():
                gid = int(row["ID"])
                try:
                    h_def = "" if pd.isna(row["HOME_TEAM_GOALS"]) else str(int(row["HOME_TEAM_GOALS"]))
                except (ValueError, TypeError):
                    h_def = ""
                try:
                    a_def = "" if pd.isna(row["AWAY_TEAM_GOALS"]) else str(int(row["AWAY_TEAM_GOALS"]))
                except (ValueError, TypeError):
                    a_def = ""
                c1, c2, c3 = st.columns([5, 1, 1])
                c1.write(flagged(row["MATCH"]))
                home = c2.text_input("H", value=h_def, key=f"rh_{gid}",
                                     label_visibility="collapsed")
                away = c3.text_input("A", value=a_def, key=f"ra_{gid}",
                                     label_visibility="collapsed")
                game_inputs[gid] = (home, away)

    submit = st.form_submit_button("Tallenna tulokset", type="primary")

# ── Handle group-stage submission ─────────────────────────────────────────────
if submit:
    parsed: dict[int, tuple] = {}
    for gid, (h_str, a_str) in game_inputs.items():
        try:
            h, a = int(h_str.strip()), int(a_str.strip())
            if not (0 <= h <= 20 and 0 <= a <= 20):
                raise ValueError
            parsed[gid] = (h, a)
        except (ValueError, AttributeError):
            pass
    if not parsed:
        st.warning("Ei tallennettavia tuloksia – syötä pisteet numeroina 0–20.")
    else:
        try:
            for gid, (home, away) in parsed.items():
                session.sql(
                    f"MERGE INTO {RESULTS_TABLE} t "
                    f"USING (SELECT {gid} AS ID, {home} AS HOME_TEAM_GOALS, {away} AS AWAY_TEAM_GOALS) s "
                    f"ON t.ID = s.ID "
                    f"WHEN MATCHED THEN UPDATE SET t.HOME_TEAM_GOALS = s.HOME_TEAM_GOALS, t.AWAY_TEAM_GOALS = s.AWAY_TEAM_GOALS "
                    f"WHEN NOT MATCHED THEN INSERT (ID, HOME_TEAM_GOALS, AWAY_TEAM_GOALS) VALUES (s.ID, s.HOME_TEAM_GOALS, s.AWAY_TEAM_GOALS)"
                ).collect()
            st.success(f"{len(parsed)} tulosta tallennettu.")
            st.rerun()
        except Exception as e:
            st.error(f"Virhe tallennuksessa: {e}")

# ── Playoff results section ───────────────────────────────────────────────────
st.divider()
st.subheader("Pudotuspelien tulokset")
st.caption(
    "Syötä pudotuspeleihin selvinneet joukkueet jokaiselle kierrokselle, "
    "turnauksen mestari sekä parhaat pelaajat. "
    "Kentät täytetään sitä mukaa kun otteluita pelataan."
)

playoff_existing: dict = {}
try:
    pp_df = session.sql(f"SELECT * FROM {PLAYOFF_RESULTS_TABLE}").to_pandas()
    if len(pp_df) > 0:
        for k in _PLAYOFF_COLS:
            if k not in pp_df.columns:
                continue
            v = pp_df.iloc[0][k]
            if v is not None and not (isinstance(v, float) and pd.isna(v)) and v != "":
                playoff_existing[k] = v
except Exception:
    pass


def _playoff_list(prefix: str, count: int) -> list[str]:
    result = []
    for i in range(1, count + 1):
        v = playoff_existing.get(f"{prefix}_{i}")
        if v and isinstance(v, str) and v in TEAMS:
            result.append(v)
    return result


def _str_default(key: str) -> str:
    v = playoff_existing.get(key, "")
    return v if isinstance(v, str) else ""


with st.form("playoff_results_form"):
    st.markdown("**Puolivälierät – valitse selvinneet 8 joukkuetta**")
    qf_teams = st.multiselect(
        "Puolivälieräjoukkueet",
        options=TEAMS,
        default=_playoff_list("QF_TEAM", 8),
        max_selections=8,
        key="ms_res_qf",
        label_visibility="collapsed",
    )

    st.markdown("**Välierät – valitse selvinneet 4 joukkuetta**")
    sf_teams = st.multiselect(
        "Välieräjoukkueet",
        options=TEAMS,
        default=_playoff_list("SF_TEAM", 4),
        max_selections=4,
        key="ms_res_sf",
        label_visibility="collapsed",
    )

    st.markdown("**Finalistit – valitse 2 joukkuetta**")
    f_teams = st.multiselect(
        "Finalistit",
        options=TEAMS,
        default=_playoff_list("FINALIST", 2),
        max_selections=2,
        key="ms_res_f",
        label_visibility="collapsed",
    )

    st.markdown("**Mestari**")
    _champ_options = ["—"] + TEAMS
    _champ_saved = playoff_existing.get("CHAMPION")
    _champ_idx = _champ_options.index(_champ_saved) if _champ_saved in TEAMS else 0
    champion = st.selectbox(
        "Mestari",
        options=_champ_options,
        index=_champ_idx,
        key="sel_res_champion",
        label_visibility="collapsed",
    )

    st.markdown("**Yksilöpalkinnot**")
    col_sc1, col_sc2 = st.columns(2)
    top_scorer = col_sc1.text_input(
        "Eniten maaleja (pelaajan nimi)",
        value=_str_default("TOP_SCORER"),
        key="ti_res_scorer",
    )
    top_points = col_sc2.text_input(
        "Pistepörssin voittaja (pelaajan nimi)",
        value=_str_default("TOP_POINTS"),
        key="ti_res_points",
    )

    playoff_submit = st.form_submit_button("Tallenna pudotuspelien tulokset", type="primary")

# ── Handle playoff results submission ─────────────────────────────────────────
if playoff_submit:
    from datetime import datetime
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _s(v) -> str:
        if not v or v == "—":
            return "NULL"
        return "'" + str(v).replace("'", "''") + "'"

    qf_v = (list(qf_teams) + [None] * 8)[:8]
    sf_v = (list(sf_teams) + [None] * 4)[:4]
    fi_v = (list(f_teams) + [None] * 2)[:2]

    col_list = (
        "QF_TEAM_1, QF_TEAM_2, QF_TEAM_3, QF_TEAM_4, "
        "QF_TEAM_5, QF_TEAM_6, QF_TEAM_7, QF_TEAM_8, "
        "SF_TEAM_1, SF_TEAM_2, SF_TEAM_3, SF_TEAM_4, "
        "FINALIST_1, FINALIST_2, CHAMPION, TOP_SCORER, TOP_POINTS, UPDATED"
    )
    val_list = (
        f"{_s(qf_v[0])}, {_s(qf_v[1])}, {_s(qf_v[2])}, {_s(qf_v[3])}, "
        f"{_s(qf_v[4])}, {_s(qf_v[5])}, {_s(qf_v[6])}, {_s(qf_v[7])}, "
        f"{_s(sf_v[0])}, {_s(sf_v[1])}, {_s(sf_v[2])}, {_s(sf_v[3])}, "
        f"{_s(fi_v[0])}, {_s(fi_v[1])}, {_s(champion)}, "
        f"{_s(top_scorer.strip())}, {_s(top_points.strip())}, '{now_str}'"
    )

    try:
        session.sql(f"DELETE FROM {PLAYOFF_RESULTS_TABLE}").collect()
        session.sql(
            f"INSERT INTO {PLAYOFF_RESULTS_TABLE} ({col_list}) VALUES ({val_list})"
        ).collect()
        st.success("Pudotuspelien tulokset tallennettu.")
        st.rerun()
    except Exception as e:
        st.error(f"Virhe pudotuspelien tulosten tallennuksessa: {e}")

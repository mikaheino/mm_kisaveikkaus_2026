import base64
import calendar
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

# ── Session + tables ──────────────────────────────────────────────────────────
session = st.session_state.snowpark_session
SCHEMA = "MM_KISAVEIKKAUS"
PREDICTIONS_TABLE = f"{SCHEMA}.MM_KISAVEIKKAUS_PREDICTIONS"
PLAYOFF_TABLE = f"{SCHEMA}.MM_KISAVEIKKAUS_PLAYOFF_PREDICTIONS"

# Lock at May 15 2026 17:20 Finnish EEST (= 14:20 UTC)
_LOCK_DATETIME = datetime(2026, 5, 15, 14, 20, 0)
_TARGET_MS = calendar.timegm(_LOCK_DATETIME.timetuple()) * 1000
is_locked = datetime.utcnow() >= _LOCK_DATETIME

_FLAGS = {
    "Austria": "🇦🇹", "Canada": "🇨🇦", "Czech Republic": "🇨🇿",
    "Denmark": "🇩🇰", "Finland": "🇫🇮", "Germany": "🇩🇪",
    "Great Britain": "🇬🇧", "Hungary": "🇭🇺", "Italy": "🇮🇹",
    "Latvia": "🇱🇻", "Norway": "🇳🇴", "Slovakia": "🇸🇰",
    "Slovenia": "🇸🇮", "Sweden": "🇸🇪", "Switzerland": "🇨🇭",
    "United States": "🇺🇸",
}

TEAMS = sorted(_FLAGS.keys())

_PLAYOFF_COLS = [
    "QF_TEAM_1", "QF_TEAM_2", "QF_TEAM_3", "QF_TEAM_4",
    "QF_TEAM_5", "QF_TEAM_6", "QF_TEAM_7", "QF_TEAM_8",
    "SF_TEAM_1", "SF_TEAM_2", "SF_TEAM_3", "SF_TEAM_4",
    "FINALIST_1", "FINALIST_2",
    "CHAMPION", "TOP_SCORER", "TOP_POINTS",
]


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


# ── Auto-identify user ────────────────────────────────────────────────────────
user_email = (
    st.session_state.get("user_email")
    or session.sql("SELECT CURRENT_USER()").collect()[0][0].lower()
)
display_name = email_to_display_name(user_email)

st.subheader(f"Welcome, {display_name}")

# ── Live countdown timer ──────────────────────────────────────────────────────
st.markdown(
    f"""
    <div style="background:rgba(0,0,0,0.55);border:1px solid rgba(255,255,255,0.15);
                border-radius:10px;padding:12px 20px;text-align:center;margin-bottom:1rem;">
      <div style="font-size:0.78rem;color:#aab4c8;letter-spacing:1px;
                  text-transform:uppercase;margin-bottom:4px;">
        ⏱ Veikkaukset lukittuvat
      </div>
      <div id="cd-timer"
           style="font-size:1.6rem;font-weight:700;color:#4da6ff;
                  font-variant-numeric:tabular-nums;letter-spacing:2px;">
        Lasketaan...
      </div>
      <div style="font-size:0.72rem;color:#8899aa;margin-top:2px;">
        15.5.2026 klo 17:20 (Helsinki)
      </div>
    </div>
    <script>
    (function() {{
      var target = {_TARGET_MS};
      function tick() {{
        var el = document.getElementById('cd-timer');
        if (!el) {{ setTimeout(tick, 200); return; }}
        var diff = target - Date.now();
        if (diff <= 0) {{
          el.style.color = '#ff6b6b';
          el.textContent = '🔒 Veikkaukset lukittu';
          return;
        }}
        var d = Math.floor(diff / 86400000);
        var h = Math.floor((diff % 86400000) / 3600000);
        var m = Math.floor((diff % 3600000) / 60000);
        var s = Math.floor((diff % 60000) / 1000);
        el.textContent = d + 'pv  '
          + String(h).padStart(2,'0') + 'h  '
          + String(m).padStart(2,'0') + 'm  '
          + String(s).padStart(2,'0') + 's';
        setTimeout(tick, 1000);
      }}
      tick();
    }})();
    </script>
    """,
    unsafe_allow_html=True,
)

if is_locked:
    st.warning("⛔ Veikkaukset on lukittu – turnaus on alkanut. Ennustuksia ei voi enää muokata.")
    st.stop()

# ── Load schedule ─────────────────────────────────────────────────────────────
schedule_df = session.sql(
    f"SELECT ID, MATCH_DAY, MATCH FROM {SCHEMA}.MM_KISAVEIKKAUS_SCHEDULE ORDER BY ID"
).to_pandas()

# ── Load existing group-stage predictions ─────────────────────────────────────
existing_preds: dict[int, tuple] = {}
for _, row in session.sql(
    f"SELECT ID, HOME_TEAM_GOALS, AWAY_TEAM_GOALS FROM {PREDICTIONS_TABLE} "
    f"WHERE USER_EMAIL = '{user_email}' ORDER BY ID"
).to_pandas().iterrows():
    h, a = row["HOME_TEAM_GOALS"], row["AWAY_TEAM_GOALS"]
    existing_preds[int(row["ID"])] = (
        None if pd.isna(h) else h,
        None if pd.isna(a) else a,
    )

is_new = len(existing_preds) == 0

# ── Load existing playoff predictions ────────────────────────────────────────
playoff_existing: dict = {}
try:
    pp_df = session.sql(
        f"SELECT * FROM {PLAYOFF_TABLE} WHERE USER_EMAIL = '{user_email}'"
    ).to_pandas()
    if len(pp_df) > 0:
        for k in _PLAYOFF_COLS:
            if k not in pp_df.columns:
                continue
            v = pp_df.iloc[0][k]
            if v is not None and not (isinstance(v, float) and pd.isna(v)) and v != "":
                playoff_existing[k] = v
except Exception:
    pass  # table may not exist yet on first deploy

playoff_new = len(playoff_existing) == 0

# ── Progress calculation (73 total: 56 group + 17 playoff) ───────────────────
group_filled = sum(
    1 for gid in schedule_df["ID"].astype(int)
    if existing_preds.get(gid, (None, None))[0] is not None
)
playoff_filled = sum(1 for k in _PLAYOFF_COLS if playoff_existing.get(k))
total_filled = group_filled + playoff_filled
TOTAL_PREDS = 73
pct = total_filled / TOTAL_PREDS

if pct >= 1.0:
    _bar_color, _ms_icon, _ms_text = "#ffd700", "🏆", "Täydelliset veikkaukset!"
elif pct >= 0.75:
    _bar_color, _ms_icon, _ms_text = "#adff2f", "🥇", "75 % täynnä – hyvää menoa!"
elif pct >= 0.5:
    _bar_color, _ms_icon, _ms_text = "#17a2b8", "🥈", "Puolet veikkauksia tehty!"
elif pct >= 0.25:
    _bar_color, _ms_icon, _ms_text = "#4da6ff", "🎯", "Hyvä alku – 25 % valmis!"
else:
    _bar_color, _ms_icon, _ms_text = "#6c757d", "", ""

st.markdown(
    f"<style>[data-testid='stProgressBar']>div>div"
    f"{{background:{_bar_color}!important;}}</style>",
    unsafe_allow_html=True,
)
col_pb, col_cnt = st.columns([4, 1])
with col_pb:
    st.progress(pct)
with col_cnt:
    st.caption(f"{total_filled} / {TOTAL_PREDS}")

if _ms_text:
    st.markdown(
        f"<div style='background:rgba(0,0,0,0.45);border-left:4px solid {_bar_color};"
        f"border-radius:6px;padding:8px 14px;margin-bottom:0.5rem;'>"
        f"<span style='color:{_bar_color};font-weight:700;font-size:1.1rem;'>{_ms_icon}</span>"
        f"&nbsp;<span style='color:white;'>{_ms_text}</span></div>",
        unsafe_allow_html=True,
    )

# ── Incomplete warning ────────────────────────────────────────────────────────
_unfilled_ids = [
    gid for gid in schedule_df["ID"].astype(int)
    if existing_preds.get(gid, (None, None))[0] is None
]
if existing_preds and _unfilled_ids:
    st.warning(f"⚠️ {len(_unfilled_ids)} ottelulla ei ole vielä ennustetta.")

# ── Group-stage section ───────────────────────────────────────────────────────
st.subheader("🏒 Alkulohkon ottelut")

if not is_new:
    st.markdown(
        "<style>[data-testid='stFormSubmitButton']>button{"
        "background-color:#c0392b!important;"
        "border-color:#922b21!important;color:white!important;}</style>",
        unsafe_allow_html=True,
    )

dates = sorted(schedule_df["MATCH_DAY"].unique())
all_inputs: dict[int, tuple] = {}

with st.form("prediction_form"):
    for date in dates:
        day_df = schedule_df[schedule_df["MATCH_DAY"] == date].copy()
        day_ids = day_df["ID"].astype(int).tolist()

        day_complete = bool(existing_preds) and all(
            existing_preds.get(gid, (None, None))[0] is not None for gid in day_ids
        )
        date_label = pd.to_datetime(str(date)).strftime("%A, %d %b")
        label = (
            f"{date_label} — {len(day_df)} games  ✓"
            if day_complete
            else f"{date_label} — {len(day_df)} games"
        )

        with st.expander(label, expanded=not day_complete):
            hdr1, hdr2, hdr3 = st.columns([5, 1, 1])
            hdr2.caption("Home")
            hdr3.caption("Away")
            for _, row in day_df.iterrows():
                gid = int(row["ID"])
                ep = existing_preds.get(gid, (None, None))
                h_def = str(int(ep[0])) if ep[0] is not None else ""
                a_def = str(int(ep[1])) if ep[1] is not None else ""
                c1, c2, c3 = st.columns([5, 1, 1])
                c1.write(flagged(row["MATCH"]))
                fact = MATCH_TRIVIA.get(row["MATCH"], "")
                if fact:
                    c1.caption(fact)
                home_in = c2.text_input("H", value=h_def, key=f"h_{gid}",
                                        label_visibility="collapsed")
                away_in = c3.text_input("A", value=a_def, key=f"a_{gid}",
                                        label_visibility="collapsed")
                all_inputs[gid] = (home_in, away_in)

    submit_label = "Save predictions" if is_new else "Update predictions"
    submit = st.form_submit_button(submit_label, type="primary")

# ── Handle group-stage submission ─────────────────────────────────────────────
if submit:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    parsed: dict[int, tuple] = {}
    skipped: list[str] = []

    for gid, (h_str, a_str) in all_inputs.items():
        h_s = h_str.strip() if h_str else ""
        a_s = a_str.strip() if a_str else ""
        if not h_s and not a_s:
            parsed[gid] = (None, None)
            skipped.append(schedule_df[schedule_df["ID"] == gid].iloc[0]["MATCH"])
        else:
            try:
                h, a = int(h_s), int(a_s)
                if not (0 <= h <= 20 and 0 <= a <= 20):
                    raise ValueError
                parsed[gid] = (h, a)
            except (ValueError, AttributeError):
                parsed[gid] = (None, None)
                skipped.append(schedule_df[schedule_df["ID"] == gid].iloc[0]["MATCH"])

    rows_out = []
    for gid, goals in parsed.items():
        srow = schedule_df[schedule_df["ID"] == gid].iloc[0]
        rows_out.append({
            "USER_EMAIL": user_email,
            "ID": gid,
            "MATCH_DAY": srow["MATCH_DAY"],
            "MATCH": srow["MATCH"],
            "HOME_TEAM_GOALS": goals[0],
            "AWAY_TEAM_GOALS": goals[1],
        })

    final_df = pd.DataFrame(rows_out).sort_values("ID").reset_index(drop=True)
    try:
        session.sql(
            f"DELETE FROM {PREDICTIONS_TABLE} WHERE USER_EMAIL = '{user_email}'"
        ).collect()
        values_parts = []
        for _, r in final_df.iterrows():
            h_sql = "NULL" if r["HOME_TEAM_GOALS"] is None else str(int(r["HOME_TEAM_GOALS"]))
            a_sql = "NULL" if r["AWAY_TEAM_GOALS"] is None else str(int(r["AWAY_TEAM_GOALS"]))
            values_parts.append(
                f"('{r['USER_EMAIL']}', {int(r['ID'])}, '{r['MATCH_DAY']}', "
                f"'{r['MATCH']}', {h_sql}, {a_sql}, '{now_str}')"
            )
        session.sql(
            f"INSERT INTO {PREDICTIONS_TABLE} "
            f"(USER_EMAIL, ID, MATCH_DAY, MATCH, HOME_TEAM_GOALS, AWAY_TEAM_GOALS, INSERTED) "
            f"VALUES {', '.join(values_parts)}"
        ).collect()
        if skipped:
            st.warning(
                f"⚠️ Tallennettu, mutta {len(skipped)} ottelulla ei ennustetta: "
                f"{', '.join(skipped[:5])}{'...' if len(skipped) > 5 else ''}"
            )
        else:
            st.success(f"Ennustukset tallennettu – **{display_name}**!")
        st.rerun()
    except Exception as e:
        st.error(f"Virhe tallennuksessa: {e}")

# ── Playoff predictions section ───────────────────────────────────────────────
st.divider()
st.subheader("💎 Veikkaukset: pudotuspelit")

st.markdown(
    """
    <div style="background:rgba(0,0,0,0.35);border-radius:8px;padding:10px 16px;
                margin-bottom:1rem;font-size:0.87rem;color:#ccd6e8;line-height:1.8;">
      🔹 <b>8 puolivälieräjoukkuetta</b> &nbsp;·&nbsp;
         <b>4 välieräjoukkuetta</b> &nbsp;·&nbsp;
         <b>2 finalistia</b> &nbsp;·&nbsp;
         🥇 <b>Mestari</b><br>
      🔹 <b>Maalientekijä</b> &amp; <b>Pistepörssin voittaja</b><br>
      <span style="color:#aab4c8;">
        Näin saat pudotuspelit mukaan heti, vaikka joukkueita ei vielä tiedetä.
      </span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Helpers for multiselect defaults ─────────────────────────────────────────


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


with st.form("playoff_form"):
    st.markdown("**Puolivälierät – valitse 8 joukkuetta** *(1 p / kpl, max 8)*")
    qf_teams = st.multiselect(
        "Puolivälieräjoukkueet",
        options=TEAMS,
        default=_playoff_list("QF_TEAM", 8),
        max_selections=8,
        key="ms_qf",
        label_visibility="collapsed",
    )

    st.markdown("**Välierät – valitse 4 joukkuetta** *(3 p / kpl, max 12)*")
    sf_teams = st.multiselect(
        "Välieräjoukkueet",
        options=TEAMS,
        default=_playoff_list("SF_TEAM", 4),
        max_selections=4,
        key="ms_sf",
        label_visibility="collapsed",
    )

    st.markdown("**Finalistit – valitse 2 joukkuetta** *(5 p / kpl, max 10)*")
    f_teams = st.multiselect(
        "Finalistit",
        options=TEAMS,
        default=_playoff_list("FINALIST", 2),
        max_selections=2,
        key="ms_f",
        label_visibility="collapsed",
    )

    st.markdown("**🥇 Mestari** *(10 p)*")
    _champ_idx = 0
    _champ_saved = playoff_existing.get("CHAMPION")
    if _champ_saved and _champ_saved in TEAMS:
        _champ_idx = TEAMS.index(_champ_saved)
    champion = st.selectbox(
        "Mestari",
        options=TEAMS,
        index=_champ_idx,
        key="sel_champion",
        label_visibility="collapsed",
    )

    st.markdown("**Yksilöpalkinnot**")
    col_sc1, col_sc2 = st.columns(2)
    top_scorer = col_sc1.text_input(
        "Eniten maaleja (pelaajan nimi)",
        value=_str_default("TOP_SCORER"),
        key="ti_scorer",
    )
    top_points = col_sc2.text_input(
        "Pistepörssin voittaja (pelaajan nimi)",
        value=_str_default("TOP_POINTS"),
        key="ti_points",
    )

    _po_label = "Save playoff predictions" if playoff_new else "Update playoff predictions"
    playoff_submit = st.form_submit_button(_po_label, type="primary")

# ── Handle playoff submission ─────────────────────────────────────────────────
if playoff_submit:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _s(v) -> str:
        return f"'{v}'" if v else "NULL"

    qf_v = (list(qf_teams) + [None] * 8)[:8]
    sf_v = (list(sf_teams) + [None] * 4)[:4]
    fi_v = (list(f_teams) + [None] * 2)[:2]

    col_list = (
        "USER_EMAIL, "
        "QF_TEAM_1, QF_TEAM_2, QF_TEAM_3, QF_TEAM_4, "
        "QF_TEAM_5, QF_TEAM_6, QF_TEAM_7, QF_TEAM_8, "
        "SF_TEAM_1, SF_TEAM_2, SF_TEAM_3, SF_TEAM_4, "
        "FINALIST_1, FINALIST_2, CHAMPION, TOP_SCORER, TOP_POINTS, INSERTED"
    )
    val_list = (
        f"'{user_email}', "
        f"{_s(qf_v[0])}, {_s(qf_v[1])}, {_s(qf_v[2])}, {_s(qf_v[3])}, "
        f"{_s(qf_v[4])}, {_s(qf_v[5])}, {_s(qf_v[6])}, {_s(qf_v[7])}, "
        f"{_s(sf_v[0])}, {_s(sf_v[1])}, {_s(sf_v[2])}, {_s(sf_v[3])}, "
        f"{_s(fi_v[0])}, {_s(fi_v[1])}, {_s(champion)}, "
        f"{_s(top_scorer.strip())}, {_s(top_points.strip())}, '{now_str}'"
    )

    try:
        session.sql(
            f"DELETE FROM {PLAYOFF_TABLE} WHERE USER_EMAIL = '{user_email}'"
        ).collect()
        session.sql(
            f"INSERT INTO {PLAYOFF_TABLE} ({col_list}) VALUES ({val_list})"
        ).collect()
        st.success(f"Pudotuspeliveikkaukset tallennettu – **{display_name}**!")
        st.rerun()
    except Exception as e:
        st.error(f"Virhe pudotuspeliveikkausten tallennuksessa: {e}")

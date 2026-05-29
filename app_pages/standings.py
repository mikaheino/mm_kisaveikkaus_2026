import base64
import os
import streamlit as st
import pandas as pd

session = st.session_state.snowpark_session

SCHEMA = "MM_KISAVEIKKAUS"
PREDICTIONS_TABLE = f"{SCHEMA}.MM_KISAVEIKKAUS_PREDICTIONS"
RESULTS_TABLE = f"{SCHEMA}.MM_KISAVEIKKAUS_RESULTS"
PLAYOFF_PREDICTIONS_TABLE = f"{SCHEMA}.MM_KISAVEIKKAUS_PLAYOFF_PREDICTIONS"
PLAYOFF_RESULTS_TABLE = f"{SCHEMA}.MM_KISAVEIKKAUS_PLAYOFF_RESULTS"

_QF_COLS = [f"QF_TEAM_{i}" for i in range(1, 9)]
_SF_COLS = [f"SF_TEAM_{i}" for i in range(1, 5)]
_F_COLS = ["FINALIST_1", "FINALIST_2"]

_QF_PTS_PER_HIT = 1
_SF_PTS_PER_HIT = 3
_F_PTS_PER_HIT = 5
_CHAMPION_PTS = 10

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


def _clean(v):
    if v is None:
        return None
    if isinstance(v, float) and pd.isna(v):
        return None
    if isinstance(v, str) and v == "":
        return None
    return v


def _team_set(row: dict, cols: list[str]) -> set:
    out = set()
    for c in cols:
        v = _clean(row.get(c))
        if v is not None:
            out.add(v)
    return out


def load_playoff_results() -> dict | None:
    try:
        df = session.sql(f"SELECT * FROM {PLAYOFF_RESULTS_TABLE}").to_pandas()
    except Exception:
        return None
    if len(df) == 0:
        return None
    return df.iloc[0].to_dict()


def load_playoff_predictions() -> dict:
    try:
        df = session.sql(f"SELECT * FROM {PLAYOFF_PREDICTIONS_TABLE}").to_pandas()
    except Exception:
        return {}
    out = {}
    for _, row in df.iterrows():
        out[row["USER_EMAIL"]] = row.to_dict()
    return out


def compute_playoff_points(prediction: dict | None, results: dict | None) -> dict:
    empty = {
        "qf_hits": 0, "qf_pts": 0,
        "sf_hits": 0, "sf_pts": 0,
        "f_hits": 0, "f_pts": 0,
        "champ_hit": False, "champ_pts": 0,
        "total": 0,
        "pred_qf": set(), "pred_sf": set(), "pred_f": set(), "pred_champ": None,
        "res_qf": set(), "res_sf": set(), "res_f": set(), "res_champ": None,
    }
    if not prediction or not results:
        return empty

    res_qf = _team_set(results, _QF_COLS)
    res_sf = _team_set(results, _SF_COLS)
    res_f = _team_set(results, _F_COLS)
    res_champ = _clean(results.get("CHAMPION"))

    pred_qf = _team_set(prediction, _QF_COLS)
    pred_sf = _team_set(prediction, _SF_COLS)
    pred_f = _team_set(prediction, _F_COLS)
    pred_champ = _clean(prediction.get("CHAMPION"))

    qf_hits = len(pred_qf & res_qf)
    sf_hits = len(pred_sf & res_sf)
    f_hits = len(pred_f & res_f)
    champ_hit = bool(res_champ and pred_champ and pred_champ == res_champ)

    qf_pts = qf_hits * _QF_PTS_PER_HIT
    sf_pts = sf_hits * _SF_PTS_PER_HIT
    f_pts = f_hits * _F_PTS_PER_HIT
    champ_pts = _CHAMPION_PTS if champ_hit else 0

    return {
        "qf_hits": qf_hits, "qf_pts": qf_pts,
        "sf_hits": sf_hits, "sf_pts": sf_pts,
        "f_hits": f_hits, "f_pts": f_pts,
        "champ_hit": champ_hit, "champ_pts": champ_pts,
        "total": qf_pts + sf_pts + f_pts + champ_pts,
        "pred_qf": pred_qf, "pred_sf": pred_sf, "pred_f": pred_f, "pred_champ": pred_champ,
        "res_qf": res_qf, "res_sf": res_sf, "res_f": res_f, "res_champ": res_champ,
    }


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

playoff_results = load_playoff_results()
playoff_predictions = load_playoff_predictions()

leaderboard_rows = []
for player_email in players:
    try:
        df = compute_player_points(player_email)
        group_pts = int(df["POINTS"].dropna().sum())
        po = compute_playoff_points(playoff_predictions.get(player_email), playoff_results)
        leaderboard_rows.append({
            "email": player_email,
            "name": email_to_display_name(player_email),
            "group_points": group_pts,
            "playoff_points": po["total"],
            "points": group_pts + po["total"],
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
        po_pts = row["playoff_points"]
        if po_pts > 0:
            breakdown = (
                f"<span style='color:#aab4c8;font-size:0.78rem;margin-right:8px;"
                f"font-variant-numeric:tabular-nums;'>"
                f"alku {row['group_points']} + po {po_pts}</span>"
            )
        else:
            breakdown = ""
        rank_html_parts.append(
            f"<div style=\"display:flex;align-items:center;justify-content:space-between;"
            f"padding:8px 14px;margin-bottom:4px;background:{bg};"
            f"box-shadow:inset -1px -1px rgba(0,0,0,0.85),inset 1px 1px rgba(170,200,255,0.55),"
            f"inset -2px -2px rgba(0,0,20,0.55),inset 2px 2px rgba(140,175,255,0.28);"
            f"color:#dce8f5;font-family:'Roboto',Arial,sans-serif;\">"
            f"<span><span style='display:inline-block;width:2.2rem;color:#7ec8ff;font-weight:700;'>"
            f"{i}.</span>{row['name']}{marker}</span>"
            f"<span>{breakdown}<span style='font-weight:700;font-variant-numeric:tabular-nums;'>"
            f"{row['points']} p</span></span>"
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

        group_pts = int(merged["POINTS"].dropna().sum())
        po = compute_playoff_points(playoff_predictions.get(player_email), playoff_results)
        total_pts = group_pts + po["total"]
        if po["total"] > 0 or playoff_results:
            st.caption(
                f"**{selected_display}** – yhteensä **{total_pts}** pistettä "
                f"(alkulohko {group_pts} + pudotuspelit {po['total']})."
            )
        else:
            st.caption(f"**{selected_display}** – yhteensä **{total_pts}** pistettä.")

        if playoff_results:
            with st.expander(
                f"Pudotuspelit · {po['total']} p", expanded=False
            ):
                def _fmt_set(s: set) -> str:
                    if not s:
                        return "—"
                    return ", ".join(f"{_FLAGS.get(t, '')} {t}".strip() for t in sorted(s))

                rows_html = []

                def _row(label: str, predicted: set, actual: set, hits: int,
                         pts_per: int, pts_total: int):
                    rows_html.append(
                        f"<tr>"
                        f"<td style='padding:6px 10px;color:#aab4c8;'>{label}</td>"
                        f"<td style='padding:6px 10px;'>{_fmt_set(predicted)}</td>"
                        f"<td style='padding:6px 10px;'>{_fmt_set(actual)}</td>"
                        f"<td style='padding:6px 10px;text-align:right;"
                        f"font-variant-numeric:tabular-nums;'>"
                        f"{hits} × {pts_per} = <b>{pts_total} p</b></td>"
                        f"</tr>"
                    )

                _row("Puolivälierät", po["pred_qf"], po["res_qf"],
                     po["qf_hits"], _QF_PTS_PER_HIT, po["qf_pts"])
                _row("Välierät", po["pred_sf"], po["res_sf"],
                     po["sf_hits"], _SF_PTS_PER_HIT, po["sf_pts"])
                _row("Finalistit", po["pred_f"], po["res_f"],
                     po["f_hits"], _F_PTS_PER_HIT, po["f_pts"])

                champ_pred = po["pred_champ"]
                champ_res = po["res_champ"]
                champ_pred_str = (
                    f"{_FLAGS.get(champ_pred, '')} {champ_pred}".strip()
                    if champ_pred else "—"
                )
                champ_res_str = (
                    f"{_FLAGS.get(champ_res, '')} {champ_res}".strip()
                    if champ_res else "—"
                )
                champ_hits_str = "1" if po["champ_hit"] else "0"
                rows_html.append(
                    f"<tr>"
                    f"<td style='padding:6px 10px;color:#aab4c8;'>Mestari</td>"
                    f"<td style='padding:6px 10px;'>{champ_pred_str}</td>"
                    f"<td style='padding:6px 10px;'>{champ_res_str}</td>"
                    f"<td style='padding:6px 10px;text-align:right;"
                    f"font-variant-numeric:tabular-nums;'>"
                    f"{champ_hits_str} × {_CHAMPION_PTS} = <b>{po['champ_pts']} p</b></td>"
                    f"</tr>"
                )

                st.markdown(
                    "<table style='width:100%;border-collapse:collapse;"
                    "background:rgba(20,50,115,0.5);color:#dce8f5;"
                    "font-family:Roboto,Arial,sans-serif;font-size:0.9rem;'>"
                    "<thead><tr>"
                    "<th style='padding:6px 10px;text-align:left;color:#7ec8ff;'>Kierros</th>"
                    "<th style='padding:6px 10px;text-align:left;color:#7ec8ff;'>Veikkaus</th>"
                    "<th style='padding:6px 10px;text-align:left;color:#7ec8ff;'>Tulos</th>"
                    "<th style='padding:6px 10px;text-align:right;color:#7ec8ff;'>Pisteet</th>"
                    "</tr></thead><tbody>"
                    + "".join(rows_html)
                    + "</tbody></table>",
                    unsafe_allow_html=True,
                )

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

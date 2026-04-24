"""
Mock Snowpark session for local development without a Snowflake connection.
Provides sample schedule data, fake results for the first two days, and
in-memory player prediction tables so all UI features can be tested.
"""
import pandas as pd
from datetime import date
from itertools import combinations

# ── Sample schedule ───────────────────────────────────────────────────────────

GROUP_A = ["Finland", "United States", "Switzerland", "Germany",
           "Latvia", "Austria", "Hungary", "Great Britain"]
GROUP_B = ["Canada", "Sweden", "Czech Republic", "Denmark",
           "Slovakia", "Norway", "Slovenia", "Italy"]

def _build_schedule() -> pd.DataFrame:
    """Round-robin matchups for both groups, spread across 12 days."""
    group_a_matches = list(combinations(GROUP_A, 2))   # 28 matches
    group_b_matches = list(combinations(GROUP_B, 2))   # 28 matches
    all_matches = group_a_matches + group_b_matches     # 56 total

    # Distribute across May 15–26 (12 days, ~4-5 games/day)
    start = date(2026, 5, 15)
    rows = []
    for i, (home, away) in enumerate(all_matches):
        day_offset = i * 12 // 56          # spread evenly over 12 days
        match_day = date(start.year, start.month, start.day + day_offset)
        rows.append({
            "ID": i + 1,
            "MATCH_DAY": match_day,
            "MATCH": f"{home} vs {away}",
            "HOME_TEAM_GOALS": None,
            "AWAY_TEAM_GOALS": None,
        })
    return pd.DataFrame(rows)

SCHEDULE_DF = _build_schedule()

# Results for the first 8 games (days 1–2)
_RESULTS = {
    1:  (3, 1), 2:  (2, 2), 3:  (1, 4), 4:  (5, 0),
    5:  (2, 3), 6:  (0, 1), 7:  (3, 3), 8:  (1, 2),
}

RESULTS_DF = SCHEDULE_DF[["ID"]].copy()
RESULTS_DF["HOME_TEAM_GOALS"] = RESULTS_DF["ID"].map(lambda i: _RESULTS.get(i, (None, None))[0])
RESULTS_DF["AWAY_TEAM_GOALS"] = RESULTS_DF["ID"].map(lambda i: _RESULTS.get(i, (None, None))[1])
RESULTS_DF["MATCH"] = SCHEDULE_DF["MATCH"]

# ── Sample player predictions ─────────────────────────────────────────────────

def _make_predictions(seed: int) -> pd.DataFrame:
    import random
    rng = random.Random(seed)
    rows = []
    for _, row in SCHEDULE_DF.iterrows():
        rows.append({
            "ID": row["ID"],
            "MATCH_DAY": row["MATCH_DAY"],
            "MATCH": row["MATCH"],
            "HOME_TEAM_GOALS": rng.randint(0, 5),
            "AWAY_TEAM_GOALS": rng.randint(0, 5),
            "INSERTED": "2026-04-20 10:00:00",
        })
    return pd.DataFrame(rows)

def _partial_predictions(seed: int, complete_days: int) -> pd.DataFrame:
    """Fill only the first N match days, leave the rest empty."""
    import random
    rng = random.Random(seed)
    dates = sorted(SCHEDULE_DF["MATCH_DAY"].unique())
    done_dates = set(dates[:complete_days])
    rows = []
    for _, row in SCHEDULE_DF.iterrows():
        filled = row["MATCH_DAY"] in done_dates
        rows.append({
            "ID": row["ID"],
            "MATCH_DAY": row["MATCH_DAY"],
            "MATCH": row["MATCH"],
            "HOME_TEAM_GOALS": rng.randint(0, 5) if filled else None,
            "AWAY_TEAM_GOALS": rng.randint(0, 5) if filled else None,
            "INSERTED": "2026-04-20 10:00:00",
        })
    return pd.DataFrame(rows)

# Pre-populated player tables
_PLAYER_TABLES: dict[str, pd.DataFrame] = {
    "MATTI_MM_KISAVEIKKAUS": _partial_predictions(42, complete_days=2),  # first 2 days filled
    "LIISA_MM_KISAVEIKKAUS": _make_predictions(7),                        # all days filled
}

# ── Mock row / result helpers ─────────────────────────────────────────────────

class _MockRow(dict):
    """Dict-like row so row["column"] access works like Snowpark Row."""
    pass

class _MockResult:
    def __init__(self, df: pd.DataFrame):
        self._df = df

    def to_pandas(self) -> pd.DataFrame:
        return self._df.copy()

    def collect(self) -> list[_MockRow]:
        return [_MockRow(r) for r in self._df.to_dict(orient="records")]


# ── Mock session ──────────────────────────────────────────────────────────────

class MockSession:
    """Mimics the subset of Snowpark Session API used by the app."""

    def sql(self, query: str) -> _MockResult:
        q = query.upper()

        # ── SHOW TABLES ──────────────────────────────────────────────────────
        if "SHOW TABLES" in q:
            table_names = list(_PLAYER_TABLES.keys()) + [
                "MM_KISAVEIKKAUS_RESULTS",
                "MM_KISAVEIKKAUS_SCHEDULE",
            ]
            # Respect LIKE filter if present (simple substring match)
            like_val = ""
            if "LIKE '" in query:
                like_val = query.split("LIKE '")[1].split("'")[0]
                like_val = like_val.replace("%", "").upper()
                table_names = [n for n in table_names if like_val in n.upper()]
            df = pd.DataFrame({"name": table_names})
            return _MockResult(df)

        # ── COUNT queries (must come before plain table matches) ─────────────
        if "COUNT" in q and "MM_KISAVEIKKAUS_RESULTS" in q:
            n = int(RESULTS_DF["HOME_TEAM_GOALS"].notna().sum())
            return _MockResult(pd.DataFrame({"N": [n]}))

        if "COUNT" in q and "MM_KISAVEIKKAUS_SCHEDULE" in q:
            return _MockResult(pd.DataFrame({"N": [len(SCHEDULE_DF)]}))

        # ── Schedule only ────────────────────────────────────────────────────
        if "MM_KISAVEIKKAUS_SCHEDULE" in q:
            return _MockResult(SCHEDULE_DF[["ID", "MATCH_DAY", "MATCH"]].copy())

        # ── Player points JOIN (standings) — must come before plain results ──
        for tname, tdf in _PLAYER_TABLES.items():
            if tname in q and "MM_KISAVEIKKAUS_RESULTS" in q:
                merged = tdf[["ID", "HOME_TEAM_GOALS", "AWAY_TEAM_GOALS"]].merge(
                    RESULTS_DF[["ID", "MATCH", "HOME_TEAM_GOALS", "AWAY_TEAM_GOALS"]],
                    on="ID", suffixes=("_PRED", "_RESULT"),
                )
                def _pts(row):
                    rh, ra = row["HOME_TEAM_GOALS_RESULT"], row["AWAY_TEAM_GOALS_RESULT"]
                    ph, pa = row["HOME_TEAM_GOALS_PRED"], row["AWAY_TEAM_GOALS_PRED"]
                    if pd.isna(rh):
                        return None
                    if ph == rh and pa == ra:
                        return 3
                    if (ph > pa and rh > ra) or (ph < pa and rh < ra):
                        return 1
                    return 0
                merged["POINTS"] = merged.apply(_pts, axis=1)
                result = merged.rename(columns={
                    "HOME_TEAM_GOALS_RESULT": "RESULT_HOME",
                    "AWAY_TEAM_GOALS_RESULT": "RESULT_AWAY",
                    "HOME_TEAM_GOALS_PRED": "PRED_HOME",
                    "AWAY_TEAM_GOALS_PRED": "PRED_AWAY",
                })[["ID", "MATCH", "RESULT_HOME", "RESULT_AWAY", "PRED_HOME", "PRED_AWAY", "POINTS"]]
                return _MockResult(result)

        # ── Results table ────────────────────────────────────────────────────
        if "MM_KISAVEIKKAUS_RESULTS" in q:
            return _MockResult(RESULTS_DF.copy())

        # ── Player prediction table ──────────────────────────────────────────
        for tname, tdf in _PLAYER_TABLES.items():
            if tname in q.upper():
                cols = ["ID", "MATCH_DAY", "MATCH", "HOME_TEAM_GOALS", "AWAY_TEAM_GOALS"]
                if "HOME_TEAM_GOALS" in q and "AWAY_TEAM_GOALS" in q and "MATCH_DAY" not in q:
                    cols = ["ID", "HOME_TEAM_GOALS", "AWAY_TEAM_GOALS"]
                return _MockResult(tdf[[c for c in cols if c in tdf.columns]].copy())

        # Fallback: empty result
        return _MockResult(pd.DataFrame())

    def write_pandas(self, df: pd.DataFrame, table_name: str, **kwargs):
        """Store written predictions in memory."""
        _PLAYER_TABLES[table_name.upper()] = df.copy()
        print(f"[mock] write_pandas → {table_name} ({len(df)} rows)")

"""
Mock Snowpark session for local development without a Snowflake connection.
Provides sample schedule data, fake results for the first two days, and
in-memory predictions in a single shared table so all UI features can be tested.
"""
import pandas as pd
from datetime import date, datetime
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

# ── Playoff predictions table ────────────────────────────────────────────────

_PLAYOFF_DF = pd.DataFrame(columns=[
    "USER_EMAIL",
    "QF_TEAM_1", "QF_TEAM_2", "QF_TEAM_3", "QF_TEAM_4",
    "QF_TEAM_5", "QF_TEAM_6", "QF_TEAM_7", "QF_TEAM_8",
    "SF_TEAM_1", "SF_TEAM_2", "SF_TEAM_3", "SF_TEAM_4",
    "FINALIST_1", "FINALIST_2",
    "CHAMPION", "TOP_SCORER", "TOP_POINTS", "INSERTED",
])

# ── Shared predictions table ─────────────────────────────────────────────────

MOCK_CURRENT_USER = "test.user@recordlydata.com"

def _make_predictions(email: str, seed: int, complete_days: int | None = None) -> pd.DataFrame:
    import random
    rng = random.Random(seed)
    dates = sorted(SCHEDULE_DF["MATCH_DAY"].unique())
    done_dates = set(dates[:complete_days]) if complete_days else set(dates)
    rows = []
    for _, row in SCHEDULE_DF.iterrows():
        filled = row["MATCH_DAY"] in done_dates
        rows.append({
            "USER_EMAIL": email,
            "ID": row["ID"],
            "MATCH_DAY": row["MATCH_DAY"],
            "MATCH": row["MATCH"],
            "HOME_TEAM_GOALS": rng.randint(0, 5) if filled else None,
            "AWAY_TEAM_GOALS": rng.randint(0, 5) if filled else None,
            "INSERTED": "2026-04-20 10:00:00",
        })
    return pd.DataFrame(rows)

# Pre-populated predictions
_PREDICTIONS_DF = pd.concat([
    _make_predictions("matti.test@recordlydata.com", 42, complete_days=2),
    _make_predictions("liisa.test@recordlydata.com", 7),
], ignore_index=True)

# ── Mock row / result helpers ─────────────────────────────────────────────────

class _MockRow(dict):
    """Dict-like row so row["column"] access works like Snowpark Row."""
    def __getitem__(self, key):
        # Support both string keys and integer index (positional)
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)

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
        global _PREDICTIONS_DF, _PLAYOFF_DF
        q = query.upper()

        # ── CURRENT_USER ────────────────────────────────────────────────
        if "CURRENT_USER" in q:
            return _MockResult(pd.DataFrame({"CURRENT_USER()": [MOCK_CURRENT_USER]}))

        # ── SHOW TABLES ─────────────────────────────────────────────────
        if "SHOW TABLES" in q:
            table_names = [
                "MM_KISAVEIKKAUS_RESULTS",
                "MM_KISAVEIKKAUS_SCHEDULE",
                "MM_KISAVEIKKAUS_PREDICTIONS",
                "MM_KISAVEIKKAUS_PLAYOFF_PREDICTIONS",
            ]
            if "LIKE '" in query:
                like_val = query.split("LIKE '")[1].split("'")[0]
                like_val = like_val.replace("%", "").upper()
                table_names = [n for n in table_names if like_val in n.upper()]
            df = pd.DataFrame({"name": table_names})
            return _MockResult(df)

        # ── DELETE playoff predictions ──────────────────────────────────
        if "DELETE" in q and "PLAYOFF_PREDICTIONS" in q:
            email = query.split("'")[1].lower()
            _PLAYOFF_DF = _PLAYOFF_DF[
                _PLAYOFF_DF["USER_EMAIL"] != email
            ].reset_index(drop=True)
            return _MockResult(pd.DataFrame({"rows_deleted": [0]}))

        # ── INSERT playoff predictions ──────────────────────────────────
        if "INSERT" in q and "PLAYOFF_PREDICTIONS" in q:
            import re
            cols_str = query.split("(")[1].split(")")[0]
            cols = [c.strip() for c in cols_str.split(",")]
            values_str = query.split("VALUES")[1]
            tuples = re.findall(r"\(([^)]+)\)", values_str)
            new_rows = []
            for t in tuples:
                parts = [p.strip().strip("'") for p in t.split(",")]
                row_dict = {}
                for idx, col in enumerate(cols):
                    row_dict[col] = None if parts[idx].upper() == "NULL" else parts[idx]
                new_rows.append(row_dict)
            _PLAYOFF_DF = pd.concat(
                [_PLAYOFF_DF, pd.DataFrame(new_rows)], ignore_index=True
            )
            return _MockResult(pd.DataFrame({"rows_inserted": [len(new_rows)]}))

        # ── SELECT playoff predictions ──────────────────────────────────
        if "PLAYOFF_PREDICTIONS" in q:
            email = query.split("'")[1].lower() if "'" in query else MOCK_CURRENT_USER
            filtered = _PLAYOFF_DF[_PLAYOFF_DF["USER_EMAIL"] == email]
            return _MockResult(filtered.copy())

        # ── DELETE predictions ──────────────────────────────────────────
        if "DELETE" in q and "MM_KISAVEIKKAUS_PREDICTIONS" in q:
            email = query.split("'")[1].lower()
            _PREDICTIONS_DF = _PREDICTIONS_DF[
                _PREDICTIONS_DF["USER_EMAIL"] != email
            ].reset_index(drop=True)
            return _MockResult(pd.DataFrame({"rows_deleted": [0]}))

        # ── INSERT predictions ──────────────────────────────────────────
        if "INSERT" in q and "MM_KISAVEIKKAUS_PREDICTIONS" in q:
            # Parse VALUES from the insert statement
            values_str = query.split("VALUES")[1]
            import re
            tuples = re.findall(r"\(([^)]+)\)", values_str)
            new_rows = []
            for t in tuples:
                parts = [p.strip().strip("'") for p in t.split(",")]
                new_rows.append({
                    "USER_EMAIL": parts[0],
                    "ID": int(parts[1]),
                    "MATCH_DAY": parts[2],
                    "MATCH": parts[3],
                    "HOME_TEAM_GOALS": None if parts[4].upper() == "NULL" else int(parts[4]),
                    "AWAY_TEAM_GOALS": None if parts[5].upper() == "NULL" else int(parts[5]),
                    "INSERTED": parts[6],
                })
            _PREDICTIONS_DF = pd.concat(
                [_PREDICTIONS_DF, pd.DataFrame(new_rows)], ignore_index=True
            )
            return _MockResult(pd.DataFrame({"rows_inserted": [len(new_rows)]}))

        # ── DISTINCT USER_EMAIL ─────────────────────────────────────────
        if "DISTINCT" in q and "USER_EMAIL" in q:
            emails = sorted(_PREDICTIONS_DF["USER_EMAIL"].unique())
            return _MockResult(pd.DataFrame({"USER_EMAIL": emails}))

        # ── COUNT queries ───────────────────────────────────────────────
        if "COUNT" in q and "MM_KISAVEIKKAUS_RESULTS" in q:
            n = int(RESULTS_DF["HOME_TEAM_GOALS"].notna().sum())
            return _MockResult(pd.DataFrame({"N": [n]}))

        if "COUNT" in q and "MM_KISAVEIKKAUS_SCHEDULE" in q:
            return _MockResult(pd.DataFrame({"N": [len(SCHEDULE_DF)]}))

        # ── Schedule ────────────────────────────────────────────────────
        if "MM_KISAVEIKKAUS_SCHEDULE" in q:
            return _MockResult(SCHEDULE_DF[["ID", "MATCH_DAY", "MATCH"]].copy())

        # ── Player points JOIN ──────────────────────────────────────────
        if "MM_KISAVEIKKAUS_PREDICTIONS" in q and "MM_KISAVEIKKAUS_RESULTS" in q:
            # Extract email from WHERE clause
            email = query.split("'")[1].lower() if "'" in query else MOCK_CURRENT_USER
            player_preds = _PREDICTIONS_DF[
                _PREDICTIONS_DF["USER_EMAIL"] == email
            ][["ID", "HOME_TEAM_GOALS", "AWAY_TEAM_GOALS"]]

            merged = player_preds.merge(
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

        # ── Select from predictions (user-filtered) ─────────────────────
        if "MM_KISAVEIKKAUS_PREDICTIONS" in q:
            email = query.split("'")[1].lower() if "'" in query else MOCK_CURRENT_USER
            filtered = _PREDICTIONS_DF[
                _PREDICTIONS_DF["USER_EMAIL"] == email
            ][["ID", "HOME_TEAM_GOALS", "AWAY_TEAM_GOALS"]]
            return _MockResult(filtered.copy())

        # ── Results table ───────────────────────────────────────────────
        if "MM_KISAVEIKKAUS_RESULTS" in q:
            return _MockResult(RESULTS_DF.copy())

        # Fallback: empty result
        return _MockResult(pd.DataFrame())

    def write_pandas(self, df: pd.DataFrame, table_name: str, **kwargs):
        """Legacy write_pandas — no longer used but kept for compatibility."""
        global _PREDICTIONS_DF
        print(f"[mock] write_pandas → {table_name} ({len(df)} rows)")

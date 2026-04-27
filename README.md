# MM-kisaveikkaus

IIHF World Championship ice hockey prediction game, running as a **Streamlit in Snowflake (SiS)** application using the **warehouse runtime**.

Players predict match outcomes (home and away goals) for all 56 group stage matches of the **2026 IIHF World Championship** (Zurich & Fribourg, Switzerland, May 15-26), plus playoff bracket predictions (8 QF → 4 SF → 2 finalists → champion) and individual award winners. Points are awarded based on prediction accuracy, and a live leaderboard tracks standings as results come in.

## Architecture

### Runtime

- **Warehouse runtime** (SiS) with Streamlit pinned via `environment.yml`
- **Warehouse**: `MM_KISAVEIKKAUS_WH` (XS, auto-suspend 60s)
- Packages from Snowflake Anaconda Channel only — no PyPI
- Local dev via `streamlit_app_local.py` with `MockSession` (no Snowflake needed)

### Snowflake Objects

| Object | Type | Description |
|--------|------|-------------|
| `STREAMLIT_APPS.MM_KISAVEIKKAUS` | Schema | All app objects live here |
| `MM_KISAVEIKKAUS_SCHEDULE` | Table | 56-row match schedule (2026 dates, Finnish team names) |
| `MM_KISAVEIKKAUS_RESULTS` | Table | Actual match results (goals filled in by admin as games finish) |
| `MM_KISAVEIKKAUS_RESULTS_V` | View | Results with computed winner column |
| `MM_KISAVEIKKAUS_PLAYOFF_PREDICTIONS` | Table | Per-user playoff bracket + award predictions |
| `MM_KISAVEIKKAUS_PLAYOFF_RESULTS` | Table | Actual playoff bracket + top scorer/points (admin-filled) |
| `MM_KISAVEIKKAUS_STAGE` | Stage | Streamlit app source files |
| `MM_KISAVEIKKAUS_APP` | Streamlit | The deployed application (warehouse runtime) |
| `MM_KISAVEIKKAUS_WH` | Warehouse | XS, auto-suspend 60s |

Player predictions are stored in `MM_KISAVEIKKAUS_PREDICTIONS` (one row per user × match). The standings page reads all predictions from this table.

### RBAC

```
ACCOUNTADMIN (owns Streamlit app)
SYSADMIN
  ├── MM_KISAVEIKKAUS_ADMIN_ROLE  → DB role: MM_KISAVEIKKAUS_ADMIN
  │                                    └── DB role: MM_KISAVEIKKAUS_USER
  └── MM_KISAVEIKKAUS_PLAYER_ROLE → DB role: MM_KISAVEIKKAUS_USER
```

- **Admin** — Full schema control, update match results, manage the Streamlit app
- **Player** — Read schedule, submit/update predictions, view standings, run the app

## App Pages

| Page | File | Description |
|------|------|-------------|
| My Predictions | `app_pages/my_predictions.py` | Group-stage scores + playoff bracket predictions |
| Standings | `app_pages/standings.py` | Live leaderboard and per-player match details |
| Rules | `app_pages/rules.py` | Scoring rules, playoff scoring, participation bet, prize distribution |
| Admin: Results | `app_pages/admin_results.py` | Admin: enter match results (restricted) |

## Scoring

### Group stage (per match)

- **3 points** — Exact score predicted correctly
- **1 point** — Correct winner predicted (wrong score)
- **0 points** — Wrong prediction
- Tiebreaker: earlier submission timestamp wins

### Playoff bracket (advance predictions)

| Prediction | Points | Max |
|---|---|---|
| Correct quarter-finalist | 1 p each | 8 p |
| Correct semi-finalist | 3 p each | 12 p |
| Correct finalist | 5 p each | 10 p |
| Correct champion | 10 p | 10 p |
| **Total playoff max** | | **40 p** |

## File Structure

```
streamlit_app.py               # Production entry point (Snowflake)
streamlit_app_local.py         # Local dev entry point (MockSession)
mock_session.py                # MockSession — mimics Snowpark Session API
trivia.py                      # Per-match trivia facts
environment.yml                # Snowflake warehouse runtime dependencies
pyproject.toml                 # Local dev dependencies (uv)
assets/
  logo_2026.png                # IIHF 2026 logo
  saku-koivu.jpg               # Background image — Standings page
  ioag9w7poe8ayrodgmlc.webp   # Background image — My Predictions + Rules
tests/
  test_trivia.py               # Smoke tests (pure Python)
app_pages/
  __init__.py
  my_predictions.py            # Submit + update predictions
  standings.py                 # Leaderboard and match details
  rules.py                     # Scoring rules and prize info
  admin_results.py             # Admin: enter match results
  prediction.py                # Legacy
  update_prediction.py         # Legacy
```

## Administration

### Add a new player

```sql
GRANT ROLE MM_KISAVEIKKAUS_PLAYER_ROLE TO USER <username>;
```

### Update match results

```sql
USE ROLE MM_KISAVEIKKAUS_ADMIN_ROLE;
USE WAREHOUSE MM_KISAVEIKKAUS_WH;

UPDATE STREAMLIT_APPS.MM_KISAVEIKKAUS.MM_KISAVEIKKAUS_RESULTS
SET HOME_TEAM_GOALS = 3, AWAY_TEAM_GOALS = 2
WHERE ID = 1;
```

### Redeploy app files after changes

```sql
USE ROLE ACCOUNTADMIN;
USE DATABASE STREAMLIT_APPS;
USE SCHEMA MM_KISAVEIKKAUS;
USE WAREHOUSE MM_KISAVEIKKAUS_WH;

PUT file:///path/to/streamlit_app.py
  @MM_KISAVEIKKAUS_STAGE/
  OVERWRITE=TRUE AUTO_COMPRESS=FALSE;

PUT file:///path/to/app_pages/standings.py
  @MM_KISAVEIKKAUS_STAGE/app_pages/
  OVERWRITE=TRUE AUTO_COMPRESS=FALSE;

-- ... repeat for each changed file ...

DROP STREAMLIT MM_KISAVEIKKAUS_APP;

CREATE STREAMLIT MM_KISAVEIKKAUS_APP
    ROOT_LOCATION = '@MM_KISAVEIKKAUS_STAGE'
    MAIN_FILE = 'streamlit_app.py'
    QUERY_WAREHOUSE = 'MM_KISAVEIKKAUS_WH';

GRANT USAGE ON STREAMLIT MM_KISAVEIKKAUS_APP TO DATABASE ROLE MM_KISAVEIKKAUS_USER;
GRANT USAGE ON STREAMLIT MM_KISAVEIKKAUS_APP TO DATABASE ROLE MM_KISAVEIKKAUS_ADMIN;
```

## Dependencies

Defined in `environment.yml` (warehouse runtime, Snowflake Anaconda Channel):

- `streamlit=1.35.0`
- `snowflake-snowpark-python`
- `pandas`

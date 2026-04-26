# MM-kisaveikkaus

IIHF World Championship ice hockey prediction game, running as a **Streamlit in Snowflake (SiS)** application using the **container runtime**.

Players predict match outcomes (home and away goals) for all 56 group stage matches of the **2026 IIHF World Championship** (Zurich & Fribourg, Switzerland, May 15-26). Points are awarded based on prediction accuracy, and a live leaderboard tracks standings as results come in.

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
| `MM_KISAVEIKKAUS_SCHEDULE` | Table | 56-row match schedule (2026 dates, English team names) |
| `MM_KISAVEIKKAUS_RESULTS` | Table | Actual match results (goals filled in by admin as games finish) |
| `MM_KISAVEIKKAUS_RESULTS_V` | View | Results with computed winner column |
| `MM_KISAVEIKKAUS_STAGE` | Stage | Streamlit app source files |
| `MM_KISAVEIKKAUS_APP` | Streamlit | The deployed application (container runtime) |
| `MM_KISAVEIKKAUS_WH` | Warehouse | XS, auto-suspend 60s |
| `MM_KISAVEIKKAUS_COMPUTE_POOL` | Compute Pool | CPU_X64_XS, auto-suspend 10min, auto-resume |

Player predictions are stored as individual tables named `{PLAYER}_MM_KISAVEIKKAUS` (e.g., `MIKA_MM_KISAVEIKKAUS`). The standings page dynamically discovers all prediction tables by pattern matching.

### RBAC

```
ACCOUNTADMIN (owns Streamlit app + compute pool)
SYSADMIN
  ├── MM_KISAVEIKKAUS_ADMIN_ROLE  → DB role: MM_KISAVEIKKAUS_ADMIN
  │                                    └── DB role: MM_KISAVEIKKAUS_PLAYER
  └── MM_KISAVEIKKAUS_PLAYER_ROLE → DB role: MM_KISAVEIKKAUS_PLAYER
```

- **Admin** — Full schema control, update match results, manage the Streamlit app
- **Player** — Read schedule, submit/update predictions, view standings, run the app

## App Pages

| Page | File | Description |
|------|------|-------------|
| Submit Prediction | `app_pages/prediction.py` | Enter name and predict all 56 match scores |
| Update Prediction | `app_pages/update_prediction.py` | Load and overwrite existing predictions |
| Standings | `app_pages/standings.py` | Live leaderboard and per-player match details |
| Rules | `app_pages/rules.py` | Scoring rules, participation bet, prize distribution |

## Scoring

- **3 points** — Exact score predicted correctly
- **1 point** — Correct winner predicted (wrong score)
- **0 points** — Wrong prediction
- Tiebreaker: earlier submission timestamp wins

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

PUT file:///path/to/streamlit_app.py
  @STREAMLIT_APPS.MM_KISAVEIKKAUS.MM_KISAVEIKKAUS_STAGE/
  OVERWRITE=TRUE AUTO_COMPRESS=FALSE;

PUT file:///path/to/app_pages/standings.py
  @STREAMLIT_APPS.MM_KISAVEIKKAUS.MM_KISAVEIKKAUS_STAGE/app_pages/
  OVERWRITE=TRUE AUTO_COMPRESS=FALSE;

ALTER STREAMLIT STREAMLIT_APPS.MM_KISAVEIKKAUS.MM_KISAVEIKKAUS_APP COMMIT;
ALTER STREAMLIT STREAMLIT_APPS.MM_KISAVEIKKAUS.MM_KISAVEIKKAUS_APP ADD LIVE VERSION FROM LAST;
```

### Manage compute pool

```sql
-- Suspend (stop credits)
ALTER COMPUTE POOL MM_KISAVEIKKAUS_COMPUTE_POOL SUSPEND;

-- Resume manually (also auto-resumes when app is opened)
ALTER COMPUTE POOL MM_KISAVEIKKAUS_COMPUTE_POOL RESUME;
```

## Dependencies

Defined in `pyproject.toml` (container runtime uses uv):

- `streamlit>=1.50`
- `snowflake-snowpark-python`
- `pandas`

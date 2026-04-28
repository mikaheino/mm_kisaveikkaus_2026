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
ACCOUNTADMIN (owns Streamlit app, stage, all objects)
  ├── DB role: MM_KISAVEIKKAUS_ADMIN  (full table control, results entry)
  │       └── DB role: MM_KISAVEIKKAUS_USER (inherits)
  └── Account role: MM_KISAVEIKKAUS_PLAYER → DB role: MM_KISAVEIKKAUS_USER
```

- **DB role `MM_KISAVEIKKAUS_ADMIN`** — Full schema control, update match results; inherits `MM_KISAVEIKKAUS_USER`
- **DB role `MM_KISAVEIKKAUS_USER`** — Read schedule, submit/update predictions, view standings, run the app
- **Account role `MM_KISAVEIKKAUS_PLAYER`** — Assigned to all players; maps to DB role `MM_KISAVEIKKAUS_USER`
- No admin account role exists — admin operations use `ACCOUNTADMIN` directly

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
USE ROLE ACCOUNTADMIN;
GRANT ROLE MM_KISAVEIKKAUS_PLAYER TO USER "user.name@recordlydata.com";
```

### Update match results

Use the admin page in the app, or SQL:

```sql
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE MM_KISAVEIKKAUS_WH;

UPDATE STREAMLIT_APPS.MM_KISAVEIKKAUS.MM_KISAVEIKKAUS_RESULTS
SET HOME_TEAM_GOALS = 3, AWAY_TEAM_GOALS = 2
WHERE ID = 1;
```

### Redeploy app files after changes

Always DROP and recreate the app — avoids stale file issues. The `ROOT_LOCATION` **must** be fully qualified (`@DB.SCHEMA.STAGE`) or the SiS runtime will fail with "no current database".

```sql
USE ROLE ACCOUNTADMIN;
USE DATABASE STREAMLIT_APPS;
USE SCHEMA MM_KISAVEIKKAUS;
USE WAREHOUSE MM_KISAVEIKKAUS_WH;

-- 1. Upload changed source files
PUT file:///path/to/streamlit_app.py @MM_KISAVEIKKAUS_STAGE/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file:///path/to/app_pages/my_predictions.py @MM_KISAVEIKKAUS_STAGE/app_pages/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file:///path/to/app_pages/standings.py @MM_KISAVEIKKAUS_STAGE/app_pages/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file:///path/to/app_pages/rules.py @MM_KISAVEIKKAUS_STAGE/app_pages/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file:///path/to/app_pages/admin_results.py @MM_KISAVEIKKAUS_STAGE/app_pages/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file:///path/to/trivia.py @MM_KISAVEIKKAUS_STAGE/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;

-- Assets (only when images change)
PUT file:///path/to/assets/logo_2026.png @MM_KISAVEIKKAUS_STAGE/assets/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file:///path/to/assets/saku-koivu.jpg @MM_KISAVEIKKAUS_STAGE/assets/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file:///path/to/assets/ioag9w7poe8ayrodgmlc.webp @MM_KISAVEIKKAUS_STAGE/assets/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;

-- Dependencies (only when environment.yml changes)
PUT file:///path/to/environment.yml @MM_KISAVEIKKAUS_STAGE/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;

-- 2. Drop and recreate with FULLY QUALIFIED ROOT_LOCATION
DROP STREAMLIT MM_KISAVEIKKAUS_APP;

CREATE STREAMLIT MM_KISAVEIKKAUS_APP
    ROOT_LOCATION = '@STREAMLIT_APPS.MM_KISAVEIKKAUS.MM_KISAVEIKKAUS_STAGE'
    MAIN_FILE = 'streamlit_app.py'
    QUERY_WAREHOUSE = 'MM_KISAVEIKKAUS_WH';

-- 3. Re-grant access (DROP removes all grants)
GRANT USAGE ON STREAMLIT MM_KISAVEIKKAUS_APP TO DATABASE ROLE MM_KISAVEIKKAUS_USER;
GRANT USAGE ON STREAMLIT MM_KISAVEIKKAUS_APP TO DATABASE ROLE MM_KISAVEIKKAUS_ADMIN;

-- 4. Ensure stage READ (needed for SiS runtime to load app files)
GRANT READ ON STAGE MM_KISAVEIKKAUS_STAGE TO DATABASE ROLE MM_KISAVEIKKAUS_USER;
GRANT READ ON STAGE MM_KISAVEIKKAUS_STAGE TO DATABASE ROLE MM_KISAVEIKKAUS_ADMIN;
GRANT READ ON STAGE MM_KISAVEIKKAUS_STAGE TO ROLE MM_KISAVEIKKAUS_PLAYER;
```

### Initial setup DDL (one-time)

Full DDL to recreate the environment from scratch:

```sql
USE ROLE ACCOUNTADMIN;

-- Infrastructure
CREATE DATABASE IF NOT EXISTS STREAMLIT_APPS;
CREATE SCHEMA IF NOT EXISTS STREAMLIT_APPS.MM_KISAVEIKKAUS;
CREATE WAREHOUSE IF NOT EXISTS MM_KISAVEIKKAUS_WH
    WAREHOUSE_SIZE = 'XSMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE;
CREATE STAGE IF NOT EXISTS STREAMLIT_APPS.MM_KISAVEIKKAUS.MM_KISAVEIKKAUS_STAGE
    COMMENT = 'Stage for MM Kisaveikkaus Streamlit app files'
    DIRECTORY = (ENABLE = TRUE);

-- Database roles
CREATE DATABASE ROLE IF NOT EXISTS STREAMLIT_APPS.MM_KISAVEIKKAUS_USER;
CREATE DATABASE ROLE IF NOT EXISTS STREAMLIT_APPS.MM_KISAVEIKKAUS_ADMIN;
GRANT DATABASE ROLE STREAMLIT_APPS.MM_KISAVEIKKAUS_USER
    TO DATABASE ROLE STREAMLIT_APPS.MM_KISAVEIKKAUS_ADMIN;

-- Account role for players
CREATE ROLE IF NOT EXISTS MM_KISAVEIKKAUS_PLAYER;
GRANT DATABASE ROLE STREAMLIT_APPS.MM_KISAVEIKKAUS_USER
    TO ROLE MM_KISAVEIKKAUS_PLAYER;
GRANT USAGE ON WAREHOUSE MM_KISAVEIKKAUS_WH TO ROLE MM_KISAVEIKKAUS_PLAYER;

-- DB role base grants
GRANT USAGE ON DATABASE STREAMLIT_APPS TO DATABASE ROLE MM_KISAVEIKKAUS_USER;
GRANT USAGE ON SCHEMA STREAMLIT_APPS.MM_KISAVEIKKAUS TO DATABASE ROLE MM_KISAVEIKKAUS_USER;

-- Tables
USE DATABASE STREAMLIT_APPS;
USE SCHEMA MM_KISAVEIKKAUS;

CREATE TABLE IF NOT EXISTS MM_KISAVEIKKAUS_SCHEDULE (
    ID          NUMBER AUTOINCREMENT,
    MATCH_DAY   DATE,
    MATCH       VARCHAR
);

CREATE TABLE IF NOT EXISTS MM_KISAVEIKKAUS_RESULTS (
    ID              NUMBER,
    HOME_TEAM_GOALS NUMBER,
    AWAY_TEAM_GOALS NUMBER
);

CREATE TABLE IF NOT EXISTS MM_KISAVEIKKAUS_PREDICTIONS (
    USER_EMAIL      VARCHAR(200) NOT NULL,
    MATCH           VARCHAR,
    HOME_TEAM_GOALS NUMBER,
    AWAY_TEAM_GOALS NUMBER,
    INSERTED        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS MM_KISAVEIKKAUS_PLAYOFF_PREDICTIONS (
    USER_EMAIL  VARCHAR(200) NOT NULL,
    QF_TEAM_1   VARCHAR(100), QF_TEAM_2   VARCHAR(100),
    QF_TEAM_3   VARCHAR(100), QF_TEAM_4   VARCHAR(100),
    QF_TEAM_5   VARCHAR(100), QF_TEAM_6   VARCHAR(100),
    QF_TEAM_7   VARCHAR(100), QF_TEAM_8   VARCHAR(100),
    SF_TEAM_1   VARCHAR(100), SF_TEAM_2   VARCHAR(100),
    SF_TEAM_3   VARCHAR(100), SF_TEAM_4   VARCHAR(100),
    FINALIST_1  VARCHAR(100), FINALIST_2  VARCHAR(100),
    CHAMPION    VARCHAR(100),
    TOP_SCORER  VARCHAR(200),
    TOP_POINTS  VARCHAR(200),
    INSERTED    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS MM_KISAVEIKKAUS_PLAYOFF_RESULTS (
    QF_TEAM_1   VARCHAR, QF_TEAM_2   VARCHAR, QF_TEAM_3   VARCHAR, QF_TEAM_4 VARCHAR,
    QF_TEAM_5   VARCHAR, QF_TEAM_6   VARCHAR, QF_TEAM_7   VARCHAR, QF_TEAM_8 VARCHAR,
    SF_TEAM_1   VARCHAR, SF_TEAM_2   VARCHAR, SF_TEAM_3   VARCHAR, SF_TEAM_4 VARCHAR,
    FINALIST_1  VARCHAR, FINALIST_2  VARCHAR,
    CHAMPION    VARCHAR,
    TOP_SCORER  VARCHAR,
    TOP_POINTS  VARCHAR,
    UPDATED     TIMESTAMP_NTZ
);

-- Table grants: MM_KISAVEIKKAUS_USER (player-facing)
GRANT SELECT ON TABLE MM_KISAVEIKKAUS_SCHEDULE TO DATABASE ROLE MM_KISAVEIKKAUS_USER;
GRANT SELECT ON TABLE MM_KISAVEIKKAUS_RESULTS TO DATABASE ROLE MM_KISAVEIKKAUS_USER;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE MM_KISAVEIKKAUS_PREDICTIONS TO DATABASE ROLE MM_KISAVEIKKAUS_USER;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE MM_KISAVEIKKAUS_PLAYOFF_PREDICTIONS TO DATABASE ROLE MM_KISAVEIKKAUS_USER;
GRANT SELECT ON TABLE MM_KISAVEIKKAUS_PLAYOFF_RESULTS TO DATABASE ROLE MM_KISAVEIKKAUS_USER;

-- Table grants: MM_KISAVEIKKAUS_ADMIN (all privileges via inheritance + explicit)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA MM_KISAVEIKKAUS TO DATABASE ROLE MM_KISAVEIKKAUS_ADMIN;

-- Stage READ grants
GRANT READ ON STAGE MM_KISAVEIKKAUS_STAGE TO DATABASE ROLE MM_KISAVEIKKAUS_USER;
GRANT READ ON STAGE MM_KISAVEIKKAUS_STAGE TO DATABASE ROLE MM_KISAVEIKKAUS_ADMIN;
GRANT READ ON STAGE MM_KISAVEIKKAUS_STAGE TO ROLE MM_KISAVEIKKAUS_PLAYER;
```

## Dependencies

Defined in `environment.yml` (warehouse runtime, Snowflake Anaconda Channel):

- `streamlit=1.35.0`
- `snowflake-snowpark-python`
- `pandas`

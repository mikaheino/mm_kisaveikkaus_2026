# Release Notes

## v1.3.0 — 2026-04-27

### Changes

- **Admin page** (`app_pages/admin_results.py`) renamed in nav from "Admin: Tulokset" wording stays the same in `streamlit_app.py` but the page title is now **"Syötä tulokset"** with proper Finnish characters throughout (`syötetty`, `syötä`, etc.).
- Admin page can now record **playoff results** in addition to group-stage scores: the 8 quarterfinal teams, 4 semifinal teams, 2 finalists, champion, and the tournament's top scorer + top points winner. These are stored in a new single-row table `MM_KISAVEIKKAUS_PLAYOFF_RESULTS` (see migration below).
- Fixed asset path bug in `admin_results.py` — background image was looked up at repo root instead of `assets/`.
- **Standings page** (`app_pages/standings.py`) restyled to match `my_predictions.py`: per-date expanders for the per-player match details, points badge (3 / 1 / 0) on each row, leaderboard rendered as styled rows with the current viewer highlighted.

### Database migration required

Run before deploying v1.3.0. Idempotent — the `CREATE TABLE IF NOT EXISTS` is a no-op on re-run.

```sql
USE DATABASE STREAMLIT_APPS;
USE SCHEMA MM_KISAVEIKKAUS;

BEGIN;

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

GRANT SELECT ON TABLE MM_KISAVEIKKAUS_PLAYOFF_RESULTS TO ROLE MM_KISAVEIKKAUS_PLAYER;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE MM_KISAVEIKKAUS_PLAYOFF_RESULTS TO ROLE MM_KISAVEIKKAUS_ADMIN;

COMMIT;

-- Sanity check: table exists and is empty until first admin save.
SELECT COUNT(*) AS playoff_results_rows FROM MM_KISAVEIKKAUS_PLAYOFF_RESULTS;  -- expect 0
```

## v1.2.0 — 2026-04-27

### Changes

- Full Finnish localization of team names. Previously the UI translated English DB values to Finnish on the fly; now team names are stored in Finnish in every column where they appear (`SCHEDULE.MATCH`, `PREDICTIONS.MATCH`, `RESULTS.MATCH`, all 15 team columns of `PLAYOFF_PREDICTIONS`). `flagged()` simplifies to flag-prefixing only.
- `trivia.py` keys rewritten to Finnish (`"Suomi vs Saksa"` etc.) to match the new schedule format.
- Removed dead `_EN_NAMES` reverse mapping and the read-path `_FI_NAMES` translation in `my_predictions.py`.
- Mock session (`mock_session.py`) updated so local dev runs against the same Finnish names.

### Database migration required

Before deploying v1.2.0, run the SQL below as `ACCOUNTADMIN` (or any role with write access to all four tables). The migration is idempotent — running it again on already-Finnish data is a no-op because none of the English source strings will match.

```sql
USE DATABASE STREAMLIT_APPS;
USE SCHEMA MM_KISAVEIKKAUS;

BEGIN;

-- 1. SCHEDULE.MATCH ("Finland vs Germany" → "Suomi vs Saksa")
UPDATE MM_KISAVEIKKAUS_SCHEDULE
SET MATCH = REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(MATCH,
    'Czech Republic', 'Tšekki'),
    'Great Britain',  'Iso-Britannia'),
    'United States',  'Yhdysvallat'),
    'Switzerland',    'Sveitsi'),
    'Austria',        'Itävalta'),
    'Hungary',        'Unkari'),
    'Germany',        'Saksa'),
    'Denmark',        'Tanska'),
    'Finland',        'Suomi'),
    'Norway',         'Norja'),
    'Sweden',         'Ruotsi'),
    'Canada',         'Kanada'),
    'Italy',          'Italia');

-- 2. PREDICTIONS.MATCH (denormalized copy)
UPDATE MM_KISAVEIKKAUS_PREDICTIONS
SET MATCH = REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(MATCH,
    'Czech Republic', 'Tšekki'),
    'Great Britain',  'Iso-Britannia'),
    'United States',  'Yhdysvallat'),
    'Switzerland',    'Sveitsi'),
    'Austria',        'Itävalta'),
    'Hungary',        'Unkari'),
    'Germany',        'Saksa'),
    'Denmark',        'Tanska'),
    'Finland',        'Suomi'),
    'Norway',         'Norja'),
    'Sweden',         'Ruotsi'),
    'Canada',         'Kanada'),
    'Italy',          'Italia');

-- 3. RESULTS.MATCH (denormalized copy)
UPDATE MM_KISAVEIKKAUS_RESULTS
SET MATCH = REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(MATCH,
    'Czech Republic', 'Tšekki'),
    'Great Britain',  'Iso-Britannia'),
    'United States',  'Yhdysvallat'),
    'Switzerland',    'Sveitsi'),
    'Austria',        'Itävalta'),
    'Hungary',        'Unkari'),
    'Germany',        'Saksa'),
    'Denmark',        'Tanska'),
    'Finland',        'Suomi'),
    'Norway',         'Norja'),
    'Sweden',         'Ruotsi'),
    'Canada',         'Kanada'),
    'Italy',          'Italia');

-- 4. PLAYOFF_PREDICTIONS: each team column. Use a temp mapping table.
CREATE OR REPLACE TEMP TABLE _team_xlate (en VARCHAR, fi VARCHAR);
INSERT INTO _team_xlate VALUES
    ('Austria','Itävalta'),('Canada','Kanada'),('Czech Republic','Tšekki'),
    ('Denmark','Tanska'),('Finland','Suomi'),('Germany','Saksa'),
    ('Great Britain','Iso-Britannia'),('Hungary','Unkari'),('Italy','Italia'),
    ('Norway','Norja'),('Sweden','Ruotsi'),('Switzerland','Sveitsi'),
    ('United States','Yhdysvallat');

UPDATE MM_KISAVEIKKAUS_PLAYOFF_PREDICTIONS p SET QF_TEAM_1 = x.fi FROM _team_xlate x WHERE p.QF_TEAM_1 = x.en;
UPDATE MM_KISAVEIKKAUS_PLAYOFF_PREDICTIONS p SET QF_TEAM_2 = x.fi FROM _team_xlate x WHERE p.QF_TEAM_2 = x.en;
UPDATE MM_KISAVEIKKAUS_PLAYOFF_PREDICTIONS p SET QF_TEAM_3 = x.fi FROM _team_xlate x WHERE p.QF_TEAM_3 = x.en;
UPDATE MM_KISAVEIKKAUS_PLAYOFF_PREDICTIONS p SET QF_TEAM_4 = x.fi FROM _team_xlate x WHERE p.QF_TEAM_4 = x.en;
UPDATE MM_KISAVEIKKAUS_PLAYOFF_PREDICTIONS p SET QF_TEAM_5 = x.fi FROM _team_xlate x WHERE p.QF_TEAM_5 = x.en;
UPDATE MM_KISAVEIKKAUS_PLAYOFF_PREDICTIONS p SET QF_TEAM_6 = x.fi FROM _team_xlate x WHERE p.QF_TEAM_6 = x.en;
UPDATE MM_KISAVEIKKAUS_PLAYOFF_PREDICTIONS p SET QF_TEAM_7 = x.fi FROM _team_xlate x WHERE p.QF_TEAM_7 = x.en;
UPDATE MM_KISAVEIKKAUS_PLAYOFF_PREDICTIONS p SET QF_TEAM_8 = x.fi FROM _team_xlate x WHERE p.QF_TEAM_8 = x.en;
UPDATE MM_KISAVEIKKAUS_PLAYOFF_PREDICTIONS p SET SF_TEAM_1 = x.fi FROM _team_xlate x WHERE p.SF_TEAM_1 = x.en;
UPDATE MM_KISAVEIKKAUS_PLAYOFF_PREDICTIONS p SET SF_TEAM_2 = x.fi FROM _team_xlate x WHERE p.SF_TEAM_2 = x.en;
UPDATE MM_KISAVEIKKAUS_PLAYOFF_PREDICTIONS p SET SF_TEAM_3 = x.fi FROM _team_xlate x WHERE p.SF_TEAM_3 = x.en;
UPDATE MM_KISAVEIKKAUS_PLAYOFF_PREDICTIONS p SET SF_TEAM_4 = x.fi FROM _team_xlate x WHERE p.SF_TEAM_4 = x.en;
UPDATE MM_KISAVEIKKAUS_PLAYOFF_PREDICTIONS p SET FINALIST_1 = x.fi FROM _team_xlate x WHERE p.FINALIST_1 = x.en;
UPDATE MM_KISAVEIKKAUS_PLAYOFF_PREDICTIONS p SET FINALIST_2 = x.fi FROM _team_xlate x WHERE p.FINALIST_2 = x.en;
UPDATE MM_KISAVEIKKAUS_PLAYOFF_PREDICTIONS p SET CHAMPION   = x.fi FROM _team_xlate x WHERE p.CHAMPION   = x.en;

DROP TABLE _team_xlate;

COMMIT;

-- Sanity checks (each should return 0)
SELECT COUNT(*) AS schedule_with_english FROM MM_KISAVEIKKAUS_SCHEDULE
  WHERE MATCH ILIKE '%Finland%' OR MATCH ILIKE '%United States%' OR MATCH ILIKE '%Germany%';

SELECT COUNT(*) AS playoff_with_english FROM MM_KISAVEIKKAUS_PLAYOFF_PREDICTIONS
  WHERE CHAMPION IN ('Finland','Germany','Sweden','Canada','United States','Switzerland',
                     'Czech Republic','Great Britain','Austria','Hungary','Italy',
                     'Norway','Denmark');
```

---

## v1.1.0 — 2026-04-27

### New features

- **Live countdown timer** — A ticking clock on the My Predictions page counts down to May 15, 2026 17:20 Helsinki time (tournament kick-off). When the first game starts, all predictions are locked and the form is replaced with a lock notice.

- **Incomplete predictions allowed** — Users can now save partial predictions (some games left empty). Empty games are stored as NULL. A warning banner shows how many games are still unfilled, both before the form and after saving.

- **Red "Update predictions" button** — After the first save, the submit button turns red and reads "Update predictions" to visually distinguish an update from a first-time save.

- **Playoff bracket predictions** — A new section below the group-stage form lets users predict:
  - 8 quarter-finalists (1 p each, max 8 p)
  - 4 semi-finalists (3 p each, max 12 p)
  - 2 finalists (5 p each, max 10 p)
  - Champion (10 p)
  - Top goal scorer and top points scorer (player names)
  - Max playoff score: **40 p**

- **Progress milestone visual cues** — The progress bar tracks all 73 predictions (56 group games + 17 playoff fields). At 25 / 50 / 75 / 100 % completion the bar changes color and a milestone banner is shown:
  - 🎯 25 % — "Hyvä alku – 25 % valmis!"
  - 🥈 50 % — "Puolet veikkauksia tehty!"
  - 🥇 75 % — "75 % täynnä – hyvää menoa!"
  - 🏆 100 % — "Täydelliset veikkaukset!"

### Fixes

- Replaced deprecated `st.experimental_rerun()` calls with `st.rerun()` in `my_predictions.py` and `admin_results.py`.

### Database migration required

Before deploying v1.1.0, run the following SQL as `ACCOUNTADMIN`:

```sql
CREATE TABLE STREAMLIT_APPS.MM_KISAVEIKKAUS.MM_KISAVEIKKAUS_PLAYOFF_PREDICTIONS (
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

GRANT SELECT, INSERT, UPDATE, DELETE
  ON TABLE STREAMLIT_APPS.MM_KISAVEIKKAUS.MM_KISAVEIKKAUS_PLAYOFF_PREDICTIONS
  TO DATABASE ROLE MM_KISAVEIKKAUS_PLAYER;
```

---

## v1.0.0 — 2026-04-20

Initial release.

- Group-stage score predictions for all 56 matches
- Live leaderboard with per-match point breakdown
- Scoring rules and prize info
- Per-match-day trivia facts
- Admin results entry page

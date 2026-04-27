# Release Notes

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

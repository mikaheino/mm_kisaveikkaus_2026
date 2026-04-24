# MM-kisaveikkaus 2026 — AI Coding Instructions

This is a Streamlit application for an internal company ice hockey prediction competition tied to the 2026 IIHF World Championship. Users predict scores for all 56 group stage games before the tournament starts; standings are computed as results come in.

## Tech stack

- **Streamlit ≥ 1.50** — UI framework
- **Snowflake Snowpark** — database and runtime (production)
- **Python 3.11** — required by the Snowflake container runtime
- **`st.connection("snowflake")`** — connection pattern used in production
- **`MockSession`** — local dev substitute (no Snowflake needed)

## Running locally (no Snowflake required)

```bash
python3 -m streamlit run streamlit_app_local.py
```

`streamlit_app_local.py` injects a `MockSession` into `st.session_state.snowpark_session` before the pages load. The mock provides:
- 56 generated games across 12 match days (May 15–26 2026)
- Two pre-populated players: **Matti** (first 2 days filled) and **Liisa** (all days filled)
- In-memory write via `write_pandas` — new submissions persist for the session

## File structure

```
streamlit_app.py          # Production entry point (Snowflake)
streamlit_app_local.py    # Local dev entry point (MockSession)
mock_session.py           # MockSession — mimics Snowpark Session API
pyproject.toml            # Dependencies (used by uv in container runtime)
logo_2026.png             # IIHF 2026 logo shown at top of every page
saku-koivu.jpg            # Background image for Standings page
ioag9w7poe8ayrodgmlc.webp # Background image for My Predictions / Rules pages
app_pages/
    my_predictions.py     # Combined submit + update predictions page
    standings.py          # Leaderboard + per-player match detail
    rules.py              # Scoring rules and prize info
    update_prediction.py  # Legacy — not in navigation, kept for reference
    prediction.py         # Legacy — not in navigation, kept for reference
```

## Snowflake schema

- **Database**: `STREAMLIT_APPS`
- **Schema**: `MM_KISAVEIKKAUS`
- **Warehouse**: `MM_KISAVEIKKAUS_WH`
- **Schedule table**: `MM_KISAVEIKKAUS_SCHEDULE` — 56 games, ID + MATCH_DAY + MATCH
- **Results table**: `MM_KISAVEIKKAUS_RESULTS` — same shape, filled by admin as games are played
- **Player tables**: `{NAME}_MM_KISAVEIKKAUS` — one table per player, auto-created on first submit

## Key patterns

### Session access
Every page gets the Snowpark session from `st.session_state`:
```python
session = st.session_state.snowpark_session
```
This is set once in `streamlit_app.py` (or replaced with `MockSession` in `streamlit_app_local.py`).

### Player name convention
Player names are uppercased and stripped of whitespace:
```python
def clean_name(s: str) -> str:
    return re.sub(r"\s+", "", s).upper()
```
Their prediction table is `{CLEANED_NAME}_MM_KISAVEIKKAUS`.

### Auto-collapse expanders
`my_predictions.py` groups games by match day. An expander collapses when all games in that day have predictions filled, giving the user a visual "done" cue. The key logic:
```python
day_complete = bool(existing_preds) and all(
    existing_preds.get(gid, (None, None))[0] is not None for gid in day_ids
)
```
**Important**: always convert pandas NaN to None when loading predictions, otherwise NaN is treated as filled:
```python
None if pd.isna(home) else home
```

### Widget key scoping
Data editor keys include the contestant name to force a fresh widget when the user switches between players:
```python
key=f"editor_{contestant}_{date_key}"
```

### Points scoring
- Exact score: **3 points**
- Correct winner only: **1 point**
- Wrong: **0 points**
- Game not yet played: **NULL** (not counted)

### Background images
Images are base64-encoded and injected as CSS `data:` URIs — required because Snowflake CSP blocks external URLs. The injection must use an f-string:
```python
_b64 = base64.b64encode(open("image.jpg", "rb").read()).decode()
st.markdown(f'<style>.stApp {{ background-image: url("data:image/jpeg;base64,{_b64}"); }}</style>', unsafe_allow_html=True)
```

## Deploying to Snowflake

```sql
USE ROLE ACCOUNTADMIN;
USE DATABASE STREAMLIT_APPS;
USE SCHEMA MM_KISAVEIKKAUS;
USE WAREHOUSE MM_KISAVEIKKAUS_WH;

PUT file:///path/to/streamlit_app.py @MM_KISAVEIKKAUS_STAGE/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file:///path/to/app_pages/my_predictions.py @MM_KISAVEIKKAUS_STAGE/app_pages/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
-- repeat for other changed files

ALTER STREAMLIT MM_KISAVEIKKAUS_APP COMMIT;
ALTER STREAMLIT MM_KISAVEIKKAUS_APP ADD LIVE VERSION FROM LAST;
```

If the container serves stale files after commit, do a full DROP + CREATE cycle.

## Common pitfalls

- **NaN vs None**: Snowpark returns NaN for NULL numerics in pandas. Always use `pd.isna()` checks, never `is None`, when handling goal values loaded from the DB.
- **Mock SQL ordering**: In `MockSession.sql()`, COUNT queries must be matched before plain table name queries — otherwise `SELECT COUNT(*) ... SCHEDULE` matches the schedule branch and returns wrong columns.
- **f-string braces**: CSS injected via f-strings must escape all CSS braces as `{{` / `}}`. Non-f-string markdown must use plain `{` / `}`.
- **Widget keys**: `st.data_editor` preserves state by key. Always scope keys to the current user (`contestant`) so switching players resets the editors.
- **AVIF support**: The original background image was `.avif`. Convert to JPEG/WebP for universal browser support (`saku-koivu.jpg`).
- **Container runtime**: Uses `SYSTEM$ST_CONTAINER_RUNTIME_PY3_11`. After file changes, always `COMMIT` + `ADD LIVE VERSION`. If stale, drop and recreate the Streamlit app.

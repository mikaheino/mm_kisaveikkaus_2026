# MM-kisaveikkaus 2026 — Complete Agent Reference

This is the single source of truth for working in this codebase. All agents (Claude Code, Ultraplan, remote agents) should read this file first.

---

## Project overview

Internal ice hockey prediction competition tied to the **2026 IIHF World Championship** (Zurich & Fribourg, May 15–26). Users predict scores for all 56 group stage games before the tournament starts; standings are computed as results come in.

**Tech stack:** Streamlit · Snowflake Snowpark · Python 3.11

---

## File structure

```
streamlit_app.py               # Production entry point (Snowflake)
streamlit_app_local.py         # Local dev entry point (MockSession)
mock_session.py                # MockSession — mimics Snowpark Session API
trivia.py                      # Per-match trivia facts (MATCH_TRIVIA dict)
environment.yml                # Snowflake warehouse runtime dependencies
pyproject.toml                 # Local dev dependencies (uv)
AGENTS.md                      # This file — comprehensive reference
CLAUDE.md                      # Claude Code instructions (brief, points here)
README.md                      # Project overview
assets/
  logo_2026.png                # IIHF 2026 logo shown at top of every page
  saku-koivu.jpg               # Background image — Standings page
  ioag9w7poe8ayrodgmlc.webp   # Background image — My Predictions + Rules pages
  logo.png                     # Original logo (legacy)
  saku-koivu-tuulettaa-maalia-naganossa-1998.avif  # Original AVIF source (legacy)
tests/
  __init__.py
  test_trivia.py               # Smoke tests for trivia.py
app_pages/
  __init__.py
  my_predictions.py            # Combined submit + update predictions page
  standings.py                 # Leaderboard + per-player match detail
  rules.py                     # Scoring rules and prize info
  admin_results.py             # Admin page: enter match results
  update_prediction.py         # Legacy — not in navigation
  prediction.py                # Legacy — not in navigation
```

---

## Runtime: Snowflake Warehouse (SiS)

This app runs on the **Snowflake Streamlit warehouse runtime**, not the container runtime.

- Python **3.9, 3.10, or 3.11** available — project uses **3.11**
- Packages must come from the **Snowflake Anaconda Channel only** — no PyPI
- Dependencies declared in `environment.yml` (not `pyproject.toml`, which is local-dev only)
- `pyproject.toml` is used by `uv` for local development; it is **not deployed to Snowflake**

### Supported Streamlit versions (warehouse runtime)

Only these versions are valid. Always use the newest available. **Verify against the live doc before upgrading:**
https://docs.snowflake.com/en/developer-guide/streamlit/app-development/dependency-management#supported-versions-of-the-streamlit-library-in-warehouse-runtimes

```
1.52.2, 1.52.1, 1.52.0, 1.51.0, 1.50.0, 1.49.1, 1.48.0, 1.47.0,
1.46.1, 1.45.1, 1.45.0, 1.44.1, 1.44.0, 1.42.0, 1.39.0, 1.35.0,
1.31.1, 1.29.0, 1.26.0, 1.22.0
```

Pin explicitly in `environment.yml`:
```yaml
  - streamlit==1.52.2
```

---

## Snowflake schema

- **Database**: `STREAMLIT_APPS`
- **Schema**: `MM_KISAVEIKKAUS`
- **Warehouse**: `MM_KISAVEIKKAUS_WH`
- **Schedule table**: `MM_KISAVEIKKAUS_SCHEDULE` — 56 games, ID + MATCH_DAY + MATCH
- **Results table**: `MM_KISAVEIKKAUS_RESULTS` — same shape, filled by admin
- **Player tables**: `{NAME}_MM_KISAVEIKKAUS` — one per player, auto-created on first submit

---

## Local development

```bash
python3 -m streamlit run streamlit_app_local.py
```

`streamlit_app_local.py` injects `MockSession` into `st.session_state.snowpark_session`. The mock provides:
- 56 generated games across 12 match days (May 15–26 2026)
- Two pre-populated players: **Matti** (first 2 days filled) and **Liisa** (all days filled)
- In-memory write via `write_pandas` — new submissions persist for the session

### Running tests

```bash
python3 -m pytest tests/
```

Tests in `tests/` are pure Python and require no Snowflake connection.

---

## Deploying to Snowflake

After code changes, upload changed files and commit:

```sql
USE ROLE ACCOUNTADMIN;
USE DATABASE STREAMLIT_APPS;
USE SCHEMA MM_KISAVEIKKAUS;
USE WAREHOUSE MM_KISAVEIKKAUS_WH;

-- Source files
PUT file:///path/to/streamlit_app.py @MM_KISAVEIKKAUS_STAGE/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file:///path/to/app_pages/my_predictions.py @MM_KISAVEIKKAUS_STAGE/app_pages/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
-- repeat for other changed .py files

-- Assets (when images change)
PUT file:///path/to/assets/logo_2026.png @MM_KISAVEIKKAUS_STAGE/assets/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file:///path/to/assets/saku-koivu.jpg @MM_KISAVEIKKAUS_STAGE/assets/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file:///path/to/assets/ioag9w7poe8ayrodgmlc.webp @MM_KISAVEIKKAUS_STAGE/assets/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;

-- Dependencies (when environment.yml changes)
PUT file:///path/to/environment.yml @MM_KISAVEIKKAUS_STAGE/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;

ALTER STREAMLIT MM_KISAVEIKKAUS_APP COMMIT;
ALTER STREAMLIT MM_KISAVEIKKAUS_APP ADD LIVE VERSION FROM LAST;
```

If the app serves stale files after commit, do a full DROP + CREATE cycle.

---

## Key patterns

### Session access
```python
session = st.session_state.snowpark_session
```
Set once in `streamlit_app.py` (or replaced with `MockSession` in `streamlit_app_local.py`).

### Player name convention
```python
def clean_name(s: str) -> str:
    return re.sub(r"\s+", "", s).upper()
```
Player prediction table: `{CLEANED_NAME}_MM_KISAVEIKKAUS`.

### Background images
Images are base64-encoded and injected as CSS `data:` URIs — required because Snowflake CSP blocks external URLs. Paths use `assets/` subfolder:
```python
_img_path = os.path.join(os.path.dirname(__file__), "..", "assets", "saku-koivu.jpg")
```
The injection must use an f-string with escaped CSS braces (`{{` / `}}`):
```python
_b64 = base64.b64encode(open(_img_path, "rb").read()).decode()
st.markdown(f'<style>.stApp {{ background-image: url("data:image/jpeg;base64,{_b64}"); }}</style>', unsafe_allow_html=True)
```
Always guard with `if os.path.exists(_img_path):` so missing files fail gracefully.

### Auto-collapse expanders
`my_predictions.py` groups games by match day. An expander collapses when all games in that day have predictions filled:
```python
day_complete = bool(existing_preds) and all(
    existing_preds.get(gid, (None, None))[0] is not None for gid in day_ids
)
```
Always convert pandas NaN to None when loading predictions:
```python
None if pd.isna(home) else home
```

### Widget key scoping
```python
key=f"editor_{contestant}_{date_key}"
```
Scoping keys to the current user forces a fresh widget when switching players.

### Points scoring
- Exact score: **3 points**
- Correct winner only: **1 point**
- Wrong: **0 points**
- Game not yet played: **NULL** (not counted)

---

## Compatibility rules

All code must be compatible with the pinned Snowflake warehouse Streamlit version:
- Never use `st.experimental_*` — use stable equivalents (`st.rerun()` not `st.experimental_rerun()`)
- Avoid `hide_index=` on dataframes — use `.style` or `use_container_width=True`
- Do not add packages to `environment.yml` unless they exist in the Snowflake Anaconda Channel
- Test every UI change locally with `streamlit_app_local.py` before deploying

---

## Common pitfalls

- **NaN vs None**: Snowpark returns NaN for NULL numerics. Always use `pd.isna()`, never `is None`.
- **Mock SQL ordering**: In `MockSession.sql()`, COUNT queries must be matched before plain table name queries.
- **f-string braces**: CSS in f-strings must escape `{` / `}` as `{{` / `}}`. Non-f-string markdown uses plain braces.
- **Widget keys**: Always scope `st.data_editor` keys to the current contestant.
- **AVIF support**: Original background was `.avif`. The `.jpg` and `.webp` conversions in `assets/` are what the code uses.
- **Container runtime**: After file changes, always `COMMIT` + `ADD LIVE VERSION`. If stale, drop and recreate.

---

## Git workflow

- **Always `git add` + `git commit` after major changes**
- Use `/plan` mode for changes that touch multiple pages, alter data flow, or change the schema
- Commit messages should describe what changed and why
- Keep commits focused — one logical change per commit

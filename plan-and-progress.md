# MM-kisaveikkaus: Plan & Progress

Last updated: 2026-04-23

## Current State: WORKING

The app is deployed and functional on Streamlit in Snowflake (container runtime). The compute pool is currently **suspended** (manually stopped to save credits). It auto-resumes when a user opens the app.

## Snowflake Connection

- **Connection name**: `CONTAINER_SERVICES`
- **Role**: `ACCOUNTADMIN` (required for Streamlit app + compute pool management)
- **Database**: `STREAMLIT_APPS`
- **Schema**: `MM_KISAVEIKKAUS`
- **Warehouse**: `MM_KISAVEIKKAUS_WH`

## Completed Work

### 1. Initial Setup (prior sessions)
- [x] Created database, schema, warehouse, stage
- [x] Created RBAC structure (database roles + account roles)
- [x] Created MM_KISAVEIKKAUS_SCHEDULE, MM_KISAVEIKKAUS_RESULTS tables
- [x] Created MM_KISAVEIKKAUS_RESULTS_V view
- [x] Built initial app with warehouse runtime

### 2. Container Runtime Migration
- [x] Created compute pool `MM_KISAVEIKKAUS_COMPUTE_POOL` (CPU_X64_XS, 1 node)
- [x] Set auto-suspend to 600s (10 min), auto-resume = true
- [x] Replaced `environment.yml` with `pyproject.toml` (uv package manager)
- [x] Added `version = "1.0.0"` to pyproject.toml (required by uv)
- [x] Migrated from `get_active_session()` to `st.connection("snowflake")`
- [x] Migrated from `st.sidebar.radio` to `st.navigation` + `st.Page`
- [x] Attached `ALLOW_ALL_INTEGRATION` EAI for PyPI access
- [x] Created Streamlit app with `SYSTEM$ST_CONTAINER_RUNTIME_PY3_11`
- [x] Full DROP + CREATE cycle to clear cached container state

### 3. Styling & Assets
- [x] Downloaded `logo.png` from original GitHub repo, uploaded to stage
- [x] CSS gradient background (dark hockey theme) replacing external image (blocked by CSP)
- [x] Button hover styles (black bg, yellow-green text)
- [x] Primary button styling
- [x] White text color for all elements (headings, paragraphs, labels, sidebar)

### 4. 2026 Schedule Update
- [x] Fetched 2026 IIHF World Championship schedule from Wikipedia
- [x] Loaded 56 group stage games (May 15-26, 2026) with English team names
- [x] Updated both MM_KISAVEIKKAUS_SCHEDULE and MM_KISAVEIKKAUS_RESULTS tables
- [x] Groups:
  - **Group A (Zurich)**: United States, Switzerland, Finland, Germany, Latvia, Austria, Hungary, Great Britain
  - **Group B (Fribourg)**: Canada, Sweden, Czech Republic, Denmark, Slovakia, Norway, Slovenia, Italy

### 5. Deprecation Fixes
- [x] Replaced `use_container_width=True` with `width="stretch"` in all files
  - streamlit_app.py (st.image)
  - prediction.py (st.data_editor)
  - update_prediction.py (st.data_editor)
  - standings.py (st.dataframe, 2 occurrences)

## Known Issues & Lessons Learned

1. **Container caching**: After updating files on stage, the container may serve stale versions. Fix: full `DROP STREAMLIT` + `CREATE STREAMLIT` cycle if `COMMIT` + `ADD LIVE VERSION` doesn't work.
2. **pyproject.toml requires `version`**: The uv package manager in container runtime fails without `version` in `[project]` table.
3. **CSP blocks external resources**: External URLs for images/fonts are blocked. Use local files on stage or CSS gradients.
4. **ACCOUNTADMIN required**: The `ALLOW_ALL_INTEGRATION` EAI and compute pool operations require ACCOUNTADMIN.
5. **`use_container_width` removed**: Streamlit versions in container runtime (post 2025-12-31) removed this parameter. Use `width="stretch"` instead.
6. **IIHF website returns 403**: Schedule data must be fetched from Wikipedia or other sources.
7. **App cannot be made public**: SiS apps cannot be exposed to the public internet; they require Snowflake authentication.

## Deployment Checklist

When making changes to the app:

```bash
# 1. Edit files locally in this directory
# 2. Upload changed files to stage:
```

```sql
USE ROLE ACCOUNTADMIN;
USE DATABASE STREAMLIT_APPS;
USE SCHEMA MM_KISAVEIKKAUS;
USE WAREHOUSE MM_KISAVEIKKAUS_WH;

-- Upload changed files (adjust paths)
PUT file:///Users/mika.heino/prod/porauslautta_snowflake_cortex_claude_non_devcontainer/streamlit_app.py
  @MM_KISAVEIKKAUS_STAGE/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;

PUT file:///Users/mika.heino/prod/porauslautta_snowflake_cortex_claude_non_devcontainer/app_pages/prediction.py
  @MM_KISAVEIKKAUS_STAGE/app_pages/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;

-- Commit and redeploy
ALTER STREAMLIT MM_KISAVEIKKAUS_APP COMMIT;
ALTER STREAMLIT MM_KISAVEIKKAUS_APP ADD LIVE VERSION FROM LAST;
```

## Stage Files (deployed)

```
mm_kisaveikkaus_stage/streamlit_app.py
mm_kisaveikkaus_stage/pyproject.toml
mm_kisaveikkaus_stage/logo.png
mm_kisaveikkaus_stage/app_pages/__init__.py
mm_kisaveikkaus_stage/app_pages/prediction.py
mm_kisaveikkaus_stage/app_pages/update_prediction.py
mm_kisaveikkaus_stage/app_pages/standings.py
mm_kisaveikkaus_stage/app_pages/rules.py
```

## Potential Future Work

- [ ] Add playoff/knockout round games to the schedule
- [ ] Admin page for entering match results directly in the app
- [ ] Email/notification when results are updated
- [ ] Historical season support (archive past tournaments)
- [ ] Mobile-optimized CSS tweaks

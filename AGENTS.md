# MM-kisaveikkaus — Agent Instructions

This document contains agent-specific instructions for working with this codebase. Read it alongside CLAUDE.md, which has the full project context.

## Runtime: Snowflake Warehouse (SiS)

This app runs on the **Snowflake Streamlit warehouse runtime**, not the container runtime. Key consequences:

- Python **3.9, 3.10, or 3.11** are available (project uses 3.11)
- Packages must come from the **Snowflake Anaconda Channel only** — no PyPI, no `pip install`
- Dependencies are declared in `environment.yml` (not `pyproject.toml`, which is local-dev only)
- `pyproject.toml` is used by `uv` for local development; it is **not deployed to Snowflake**

## Supported Streamlit versions (warehouse runtime)

Only these versions are valid in `environment.yml`. Use the **newest available**:

```
1.52.2, 1.52.1, 1.52.0, 1.51.0, 1.50.0, 1.49.1, 1.48.0, 1.47.0,
1.46.1, 1.45.1, 1.45.0, 1.44.1, 1.44.0, 1.42.0, 1.39.0, 1.35.0,
1.31.1, 1.29.0, 1.26.0, 1.22.0
```

**Reference**: https://docs.snowflake.com/en/developer-guide/streamlit/app-development/dependency-management#supported-versions-of-the-streamlit-library-in-warehouse-runtimes

Always verify the latest supported version against this doc before updating `environment.yml`. Pin explicitly:
```yaml
  - streamlit==1.52.2
```

## Compatibility rules for all code changes

- Never use APIs removed or changed between the pinned Streamlit version and current HEAD
- Avoid `st.experimental_*` functions — use stable equivalents (e.g. `st.rerun()` not `st.experimental_rerun()`)
- Avoid `hide_index=` on dataframes — use `.style` or pass `use_container_width=True` instead
- Test every UI change locally with `streamlit_app_local.py` before deploying
- Do not add packages to `environment.yml` unless they exist in the Snowflake Anaconda Channel: https://repo.anaconda.com/pkgs/snowflake/

## Deploying to Snowflake

After code changes:

```sql
USE ROLE ACCOUNTADMIN;
USE DATABASE STREAMLIT_APPS;
USE SCHEMA MM_KISAVEIKKAUS;
USE WAREHOUSE MM_KISAVEIKKAUS_WH;

PUT file:///path/to/streamlit_app.py @MM_KISAVEIKKAUS_STAGE/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file:///path/to/app_pages/my_predictions.py @MM_KISAVEIKKAUS_STAGE/app_pages/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
-- repeat for each changed file

ALTER STREAMLIT MM_KISAVEIKKAUS_APP COMMIT;
ALTER STREAMLIT MM_KISAVEIKKAUS_APP ADD LIVE VERSION FROM LAST;
```

Also upload `environment.yml` when dependencies change:
```sql
PUT file:///path/to/environment.yml @MM_KISAVEIKKAUS_STAGE/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
```

If the app serves stale files after commit, do a full DROP + CREATE cycle.

## Local development

```bash
python3 -m streamlit run streamlit_app_local.py
```

`streamlit_app_local.py` injects `MockSession` — no Snowflake connection needed. Changes to the mock data live in `mock_session.py`.

## Git workflow

- **Always `git add` + `git commit` after major changes**
- Use `/plan` mode for major changes before writing code
- Commit messages should describe what changed and why
- Keep commits focused — one logical change per commit

## Planning major changes

For any change that touches multiple pages, alters data flow, or changes the Snowflake schema:

1. Enter `/plan` mode first
2. Confirm the plan with the user before writing code
3. Implement incrementally, committing after each logical step

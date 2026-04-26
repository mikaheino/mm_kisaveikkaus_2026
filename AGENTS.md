# Project Overview

Internal ice hockey prediction competition tied to the **2026 IIHF World Championship** (Zurich & Fribourg, May 15–26). Users predict scores for all 56 group stage games before the tournament starts; standings are computed as results come in.

Runs as a **Streamlit in Snowflake (SiS) warehouse runtime** app. Each viewer gets a personal Streamlit server instance. The app uses Snowpark for all database access; there is no external backend.

---

# Directory Structure

```
streamlit_app.py               # Production entry point (Snowflake)
streamlit_app_local.py         # Local dev entry point (MockSession, no Snowflake needed)
mock_session.py                # MockSession — mimics Snowpark Session API for local dev
trivia.py                      # MATCH_TRIVIA dict: one fact per group-stage matchup
environment.yml                # Snowflake warehouse runtime dependencies (Anaconda channel)
pyproject.toml                 # Local dev dependencies (uv) — NOT deployed to Snowflake
AGENTS.md                      # This file
CLAUDE.md                      # Claude Code essentials (brief, points here)
README.md                      # Project overview and administration guide
assets/
  logo_2026.png                # IIHF 2026 logo — shown at top of every page
  saku-koivu.jpg               # Background image — Standings page
  ioag9w7poe8ayrodgmlc.webp   # Background image — My Predictions + Rules pages
  logo.png                     # Original logo (legacy)
  saku-koivu-tuulettaa-maalia-naganossa-1998.avif  # Original AVIF source (legacy)
tests/
  __init__.py
  test_trivia.py               # Smoke tests for trivia.py (pure Python, no Snowflake)
app_pages/
  __init__.py
  my_predictions.py            # Combined submit + update predictions page
  standings.py                 # Leaderboard + per-player match detail
  rules.py                     # Scoring rules and prize info
  admin_results.py             # Admin page: enter match results (restricted by email)
  update_prediction.py         # Legacy — not in navigation
  prediction.py                # Legacy — not in navigation
```

---

# Tech Stack

| Layer | Technology |
|---|---|
| UI framework | Streamlit (warehouse runtime, see supported versions below) |
| Runtime | Snowflake SiS warehouse runtime, Python 3.11 |
| Database | Snowflake Snowpark (`snowflake-snowpark-python`) |
| Data manipulation | pandas |
| Local dev | `MockSession` (no Snowflake required), `uv` for deps |
| Tests | pytest |
| Formatter | Ruff |

### Supported Streamlit versions (warehouse runtime)

Pin explicitly in `environment.yml`. Always verify against the live doc before upgrading:
https://docs.snowflake.com/en/developer-guide/streamlit/app-development/dependency-management#supported-versions-of-the-streamlit-library-in-warehouse-runtimes

```
1.52.2, 1.52.1, 1.52.0, 1.51.0, 1.50.0, 1.49.1, 1.48.0, 1.47.0,
1.46.1, 1.45.1, 1.45.0, 1.44.1, 1.44.0, 1.42.0, 1.39.0, 1.35.0,
1.31.1, 1.29.0, 1.26.0, 1.22.0
```

---

# Coding Standards (Do)

- **Formatter**: Ruff. Run `ruff format .` before committing.
- **Linter**: Ruff. Run `ruff check .` and fix all issues before committing.
- **Naming**: player names uppercased and whitespace-stripped via `clean_name()` in `mock_session.py`; table names follow `{CLEANED_NAME}_MM_KISAVEIKKAUS`.
- **NaN handling**: Snowpark returns `NaN` for NULL numerics. Always use `pd.isna()` — never `is None` or `== None`.
- **Widget keys**: scope `st.data_editor` and other stateful widgets to the current contestant: `key=f"editor_{contestant}_{date_key}"`.
- **Background images**: base64-encode and inject as CSS `data:` URIs (Snowflake CSP blocks external URLs). Use `os.path.join(os.path.dirname(__file__), "..", "assets", "filename")` from `app_pages/`. Always guard with `if os.path.exists(_img_path):`.
- **CSS in f-strings**: escape all CSS braces as `{{` / `}}`. In non-f-string markdown use plain `{` / `}`.
- **No experimental APIs**: use `st.rerun()` not `st.experimental_rerun()`, etc.
- **No comments** unless the WHY is non-obvious. Never write what the code does — only hidden constraints or surprising invariants.
- **Major changes**: use `/plan` mode before writing code. Commit after each logical step.

---

# Don'ts

- **Never bypass Snowflake RBAC.** All database actions must go through the assigned role (`MM_KISAVEIKKAUS_PLAYER` or `MM_KISAVEIKKAUS_ADMIN`). Never use `ACCOUNTADMIN` for app queries.
- **Never commit credentials or `.env` files.** The Snowflake connection is handled by `get_active_session()` in production and `MockSession` locally — no hardcoded connection strings.
- **Never run destructive SQL (`DROP`, `TRUNCATE`, `DELETE`) in production** without explicit user instruction and confirmation.
- **Never add packages to `environment.yml`** unless they exist in the Snowflake Anaconda Channel (https://repo.anaconda.com/pkgs/snowflake/). No PyPI packages in production.
- **Never use `st.experimental_*` APIs** — they are removed in current Streamlit versions and will break on deployment.
- **Never skip `--no-verify`** on git commits unless the user explicitly requests it.
- **Never push to `main`** without user confirmation.

---

# Snowflake-Specific Settings

| Setting | Value |
|---|---|
| Database | `STREAMLIT_APPS` |
| Schema | `MM_KISAVEIKKAUS` |
| Warehouse | `MM_KISAVEIKKAUS_WH` (XS, auto-suspend 60s) |
| Stage | `MM_KISAVEIKKAUS_STAGE` |
| App object | `MM_KISAVEIKKAUS_APP` |
| Player role | `MM_KISAVEIKKAUS_PLAYER_ROLE` → DB role `MM_KISAVEIKKAUS_PLAYER` |
| Admin role | `MM_KISAVEIKKAUS_ADMIN_ROLE` → DB role `MM_KISAVEIKKAUS_ADMIN` |

### Key tables

| Table | Purpose |
|---|---|
| `MM_KISAVEIKKAUS_SCHEDULE` | 56 games: ID, MATCH_DAY, MATCH |
| `MM_KISAVEIKKAUS_RESULTS` | Actual results (admin-filled) |
| `MM_KISAVEIKKAUS_RESULTS_V` | Results view with computed winner column |
| `{NAME}_MM_KISAVEIKKAUS` | Per-player predictions, auto-created on first submit |

### Deploying files after changes

```sql
USE ROLE ACCOUNTADMIN;
USE DATABASE STREAMLIT_APPS;
USE SCHEMA MM_KISAVEIKKAUS;
USE WAREHOUSE MM_KISAVEIKKAUS_WH;

-- Source files
PUT file:///path/to/streamlit_app.py @MM_KISAVEIKKAUS_STAGE/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file:///path/to/app_pages/my_predictions.py @MM_KISAVEIKKAUS_STAGE/app_pages/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
-- repeat for other changed .py files

-- Assets (only when images change)
PUT file:///path/to/assets/logo_2026.png @MM_KISAVEIKKAUS_STAGE/assets/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file:///path/to/assets/saku-koivu.jpg @MM_KISAVEIKKAUS_STAGE/assets/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file:///path/to/assets/ioag9w7poe8ayrodgmlc.webp @MM_KISAVEIKKAUS_STAGE/assets/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;

-- Dependencies (only when environment.yml changes)
PUT file:///path/to/environment.yml @MM_KISAVEIKKAUS_STAGE/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;

ALTER STREAMLIT MM_KISAVEIKKAUS_APP COMMIT;
ALTER STREAMLIT MM_KISAVEIKKAUS_APP ADD LIVE VERSION FROM LAST;
```

If the app serves stale files after commit, do a full DROP + CREATE cycle.

---

# Testing & Quality

```bash
# Run tests (pure Python, no Snowflake needed)
python3 -m pytest tests/ -v

# Format
ruff format .

# Lint
ruff check .

# Run app locally
python3 -m streamlit run streamlit_app_local.py
```

Tests live in `tests/`. Keep them pure Python — no Streamlit imports, no Snowflake connection. `MockSession` exists for local logic testing if needed.

There is no CI/CD pipeline. Deploys are manual SQL PUT commands (see Snowflake-Specific Settings above).

---

# Custom Skills & SubAgents Guide

### `developing-with-streamlit`

**Load with:** `/developing-with-streamlit` (or the Skill tool with `skill: "developing-with-streamlit"`)

**Use for:** any Streamlit task — creating, editing, debugging, styling, theming, optimizing, or deploying pages. Also covers layout, widget selection, session state, data display, and Snowflake connection patterns.

**Sub-skills available inside it:**

| Sub-skill | When to use |
|---|---|
| `organizing-streamlit-code` | restructuring pages or modules |
| `improving-streamlit-design` | visual polish, icons, badges |
| `using-streamlit-layouts` | columns, tabs, sidebar, expanders |
| `displaying-streamlit-data` | dataframes, column config, charts |
| `optimizing-streamlit-performance` | caching, fragments, slow reruns |
| `connecting-streamlit-to-snowflake` | `st.connection`, query caching |
| `creating-streamlit-themes` | CSS, colors, dark mode |
| `using-streamlit-session-state` | widget keys, callbacks, state bugs |
| `building-streamlit-multipage-apps` | navigation, shared state across pages |

**Do not** use this skill for pure Snowflake SQL or schema changes — those are handled directly.

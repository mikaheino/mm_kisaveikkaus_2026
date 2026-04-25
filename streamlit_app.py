import streamlit as st

# -- Page config (must be first Streamlit call) --
st.set_page_config(
    page_title="MM-kisaveikkaus",
    page_icon="\U0001f3d2",
    layout="centered",
)

# -- Custom CSS: hockey-themed dark gradient background + button styles --
st.markdown(
    """
    <style>
    /* ── Background ── */
    .stApp {
        background: linear-gradient(
            135deg,
            #0a0a2e 0%,
            #1a1a4e 25%,
            #0d2137 50%,
            #162a3e 75%,
            #0a0a2e 100%
        );
        color: white;
    }

    /* ── Global white text ── */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4,
    .stApp p, .stApp span, .stApp label, .stApp div,
    .stApp .stMarkdown, .stApp .stText {
        color: white !important;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] { color: white !important; }
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label { color: white !important; }

    /* ── Form ── */
    [data-testid="stForm"] { border: 0px; }

    /* ── Text + number inputs ── */
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input {
        background-color: rgba(255, 255, 255, 0.92) !important;
        color: #0d1b2a !important;
        border: 1px solid rgba(255, 255, 255, 0.6) !important;
        border-radius: 6px !important;
    }
    [data-testid="stTextInput"] input:focus,
    [data-testid="stNumberInput"] input:focus {
        border-color: #4da6ff !important;
        box-shadow: 0 0 0 2px rgba(77, 166, 255, 0.4) !important;
    }
    [data-testid="stTextInput"] input::placeholder {
        color: #5a7a9a !important;
    }

    /* ── Selectbox ── */
    [data-testid="stSelectbox"] [data-baseweb="select"] > div {
        background-color: rgba(255, 255, 255, 0.92) !important;
        border: 1px solid rgba(255, 255, 255, 0.6) !important;
        border-radius: 6px !important;
    }
    [data-testid="stSelectbox"] [data-baseweb="select"] *,
    [data-testid="stSelectbox"] [data-baseweb="select"] input {
        color: #0d1b2a !important;
    }
    [data-testid="stSelectbox"] [data-baseweb="select"] svg { fill: #0d1b2a !important; }

    /* Selectbox dropdown menu */
    [data-baseweb="popover"] > div { background-color: #1a2a4a !important; }
    [data-baseweb="menu"] li {
        background-color: #1a2a4a !important;
        color: white !important;
    }
    [data-baseweb="menu"] li:hover,
    [data-baseweb="menu"] [aria-selected="true"] {
        background-color: #2a4070 !important;
    }

    /* ── Expander ── */
    [data-testid="stExpander"] {
        border: 1px solid rgba(255, 255, 255, 0.18) !important;
        border-radius: 8px !important;
        background-color: rgba(255, 255, 255, 0.05) !important;
    }
    [data-testid="stExpander"] summary {
        background-color: rgba(255, 255, 255, 0.07) !important;
        border-radius: 6px !important;
        padding: 4px 8px !important;
    }
    [data-testid="stExpander"] summary *,
    [data-testid="stExpander"] summary p,
    [data-testid="stExpander"] summary span {
        color: white !important;
    }

    /* ── Top navigation bar ── */
    header[data-testid="stHeader"] {
        background-color: rgba(10, 10, 46, 0.97) !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.15) !important;
    }
    header[data-testid="stHeader"] a,
    header[data-testid="stHeader"] span,
    header[data-testid="stHeader"] p,
    header[data-testid="stHeader"] button,
    header[data-testid="stHeader"] div {
        color: white !important;
    }
    /* Active / selected nav link */
    header[data-testid="stHeader"] [aria-selected="true"],
    header[data-testid="stHeader"] [data-active="true"] {
        border-bottom: 2px solid #ADFF2F !important;
        color: #ADFF2F !important;
    }

    /* ── Buttons ── */
    .stButton > button:hover {
        background-color: #000000 !important;
        color: #ADFF2F !important;
        border-color: #ADFF2F !important;
    }
    .stButton > button[kind="primary"] {
        background-color: #1a73e8;
        color: white;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #000000 !important;
        color: #ADFF2F !important;
        border-color: #ADFF2F !important;
    }

    /* ── Logo image full-width ── */
    [data-testid="stImage"] img { width: 100% !important; max-width: 100%; }

    /* ── Horizontal nav radio ── */
    div[role="radiogroup"] { gap: 0.5rem; }
    div[role="radiogroup"] label {
        padding: 6px 16px !important;
        border: 1px solid rgba(255,255,255,0.25) !important;
        border-radius: 6px !important;
        cursor: pointer;
    }
    div[role="radiogroup"] label:has(input:checked) {
        border-color: #ADFF2F !important;
        color: #ADFF2F !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -- Snowflake session (get_active_session works in both classic SiS and vNext) --
from snowflake.snowpark.context import get_active_session
st.session_state.snowpark_session = get_active_session()

# -- Resolve the viewer's identity --
# In vNext SiS get_active_session() is scoped to the viewer, so CURRENT_USER()
# returns their Snowflake username, which equals their email address at Recordly.
st.session_state.user_email = st.session_state.snowpark_session.sql(
    "SELECT CURRENT_USER()"
).collect()[0][0].lower()

# -- Display logo --
st.image("logo_2026.png")

# -- Multi-page navigation (sidebar, compatible with all SiS Streamlit versions) --
import importlib
import sys

_ADMIN_EMAILS = {
    "mika.heino@recordlydata.com",
    "mikko.sulonen@recordlydata.com",
    "marko.laitinen@recordlydata.com",
}

_page_titles = ["My Predictions", "Standings", "Rules"]
if st.session_state.get("user_email") in _ADMIN_EMAILS:
    _page_titles.append("Admin: Results")

_page_modules = {
    "My Predictions": "app_pages.my_predictions",
    "Standings":      "app_pages.standings",
    "Rules":          "app_pages.rules",
    "Admin: Results": "app_pages.admin_results",
}

selected = st.radio("", _page_titles, horizontal=True, label_visibility="collapsed")

_mod = _page_modules[selected]
if _mod in sys.modules:
    importlib.reload(sys.modules[_mod])
else:
    importlib.import_module(_mod)

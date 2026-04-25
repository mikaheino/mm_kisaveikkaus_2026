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
    </style>
    """,
    unsafe_allow_html=True,
)

# -- Snowflake session (get_active_session works in both classic SiS and vNext) --
from snowflake.snowpark.context import get_active_session
st.session_state.snowpark_session = get_active_session()

# -- Resolve the actual logged-in viewer's identity --
# Container runtime runs as a platform service account, so CURRENT_USER() returns
# a system name. Try st.context.user attributes in order of preference.
_SERVICE_ACCOUNT = "stplatstreamlit15690104"

def _resolve_user_email(session) -> str:
    _ctx_user = getattr(st.context, "user", None)
    if _ctx_user is not None:
        # Try email first, then login_name (set to email on user creation), then name
        for _attr in ("email", "login_name", "name"):
            _val = getattr(_ctx_user, _attr, None)
            if _val and _val.lower() != _SERVICE_ACCOUNT:
                return _val.lower()
    # Final fallback: correct in native SiS and local dev
    return session.sql("SELECT CURRENT_USER()").collect()[0][0].lower()

st.session_state.user_email = _resolve_user_email(st.session_state.snowpark_session)

# Temporary debug — only shown when identity resolution fails (service account detected)
if st.session_state.user_email == _SERVICE_ACCOUNT:
    with st.expander("⚠️ Debug: user context (admin only)", expanded=True):
        _ctx_user = getattr(st.context, "user", None)
        st.write("st.context.user:", _ctx_user)
        if _ctx_user is not None:
            st.write("Attributes:", {
                a: getattr(_ctx_user, a, None)
                for a in ("email", "login_name", "name", "id")
            })
        _headers = getattr(st.context, "headers", None)
        st.write("st.context.headers:", dict(_headers) if _headers else None)

# -- Display logo --
st.image("logo_2026.png", width="stretch")

# -- Multi-page navigation using st.navigation + st.Page --
_ADMIN_EMAILS = {
    "mika.heino@recordlydata.com",
    "mikko.sulonen@recordlydata.com",
    "marko.laitinen@recordlydata.com",
}

_pages = [
    st.Page("app_pages/my_predictions.py", title="My Predictions", icon=":material/sports_hockey:"),
    st.Page("app_pages/standings.py", title="Standings", icon=":material/emoji_events:"),
    st.Page("app_pages/rules.py", title="Rules", icon=":material/menu_book:"),
]
if st.session_state.get("user_email") in _ADMIN_EMAILS:
    _pages.append(
        st.Page("app_pages/admin_results.py", title="Admin: Results", icon=":material/admin_panel_settings:")
    )

pages = st.navigation(_pages, position="top")

pages.run()

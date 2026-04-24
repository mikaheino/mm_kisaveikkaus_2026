"""Local development entry point — uses MockSession instead of Snowflake."""
import base64
import os
import streamlit as st
from mock_session import MockSession

def _img_b64(filename: str) -> str:
    path = os.path.join(os.path.dirname(__file__), filename)
    return base64.b64encode(open(path, "rb").read()).decode()

st.set_page_config(
    page_title="MM-kisaveikkaus (local)",
    page_icon="🏒",
    layout="centered",
)

_ioag_b64 = _img_b64("ioag9w7poe8ayrodgmlc.webp")
st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: url("data:image/webp;base64,{_ioag_b64}");
        background-size: cover;
        background-position: center top;
        background-attachment: fixed;
    }}
    .stApp::before {{
        content: "";
        position: fixed;
        inset: 0;
        background: rgba(5, 10, 30, 0.68);
        pointer-events: none;
        z-index: 0;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
    /* ── Global text ── */
    .stApp {
        color: white;
    }

    /* ── Global white text ── */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4,
    .stApp p, .stApp span, .stApp label, .stApp div,
    .stApp .stMarkdown, .stApp .stText { color: white !important; }

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

if "snowpark_session" not in st.session_state:
    st.session_state.snowpark_session = MockSession()

st.image("logo_2026.png", width="stretch")

pages = st.navigation(
    [
        st.Page("app_pages/my_predictions.py", title="My Predictions", icon=":material/sports_hockey:"),
        st.Page("app_pages/standings.py", title="Standings", icon=":material/emoji_events:"),
        st.Page("app_pages/rules.py", title="Rules", icon=":material/menu_book:"),
    ],
    position="top",
)

pages.run()

import base64
import os
import streamlit as st

# ── Background image ──────────────────────────────────────────────────────────
_img_path = os.path.join(os.path.dirname(__file__), "..", "assets", "ioag9w7poe8ayrodgmlc.webp")
if os.path.exists(_img_path):
    _b64 = base64.b64encode(open(_img_path, "rb").read()).decode()
    st.markdown(
        f"""
        <style>
        [data-testid="stAppViewContainer"] {{
            background-image: url("data:image/webp;base64,{_b64}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        [data-testid="stAppViewContainer"]::before {{
            content: "";
            position: fixed;
            inset: 0;
            background: rgba(5, 10, 30, 0.72);
            pointer-events: none;
            z-index: 0;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

st.title("Rules")

st.header("How to input your prediction")
st.write(
    "Input your predictions by using the **Submit Prediction** page. "
    "You can modify your existing prediction using the **Update Prediction** page."
)
st.write(
    "Updating your prediction will overwrite the existing one. "
    "The system does not keep backups of previous predictions."
)

st.divider()

st.header("Scoring")
st.write("Let's consider a match between **France** and **Slovakia**.")
st.write("You predict that France will win **3\u20132**.")
st.markdown(
    """
- If the game ends **3\u20132** \u2192 you get **3 points** (correct exact score)
- If the game ends **4\u20132** \u2192 you get **1 point** (correct winner only)
- If two or more players are tied on points, the player who submitted their prediction first has the upper hand.
"""
)

st.divider()

st.header("Participation Bet")
st.write("20 euros for each participant. The bet must be paid before the first game.")

st.divider()

st.header("Prize Distribution")
st.write("1st place: **60%**")
st.write("2nd place: **30%**")
st.write("3rd place: **10%**")

st.divider()

st.header("Playoff Predictions")
st.write(
    "In addition to group-stage scores, predict the knockout-round teams, "
    "the champion, and individual award winners."
)
st.markdown(
    """
| Prediction | Points | Max |
|---|---|---|
| Correct quarter-finalist | 1 p each | 8 p |
| Correct semi-finalist | 3 p each | 12 p |
| Correct finalist | 5 p each | 10 p |
| Correct champion | 10 p | 10 p |
| **Total playoff max** | | **40 p** |
"""
)
st.write("Top scorer and top points winner scoring will be announced separately.")

import streamlit as st

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

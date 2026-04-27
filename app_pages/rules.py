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

st.title("S\u00e4\u00e4nn\u00f6t")

st.header("N\u00e4in veikkaat")
st.write(
    "Sy\u00f6t\u00e4 veikkaukset **Omat veikkaukset** -sivulla. "
    "Voit p\u00e4ivitt\u00e4\u00e4 veikkauksiasi milloin tahansa ennen lukkiutumisaikaa."
)
st.write(
    "P\u00e4ivitys korvaa aiemman veikkauksen. "
    "J\u00e4rjestelm\u00e4 ei s\u00e4ilyt\u00e4 vanhoja versioita."
)

st.divider()

st.header("Pisteytys")
st.write("Esimerkki: ottelu **Ranska vs Slovakia**.")
st.write("Veikkauksesi: Ranska voittaa **3\u20132**.")
st.markdown(
    """
- Ottelu p\u00e4\u00e4ttyy **3\u20132** \u2192 saat **3 pistett\u00e4** (oikea tulos)
- Ottelu p\u00e4\u00e4ttyy **4\u20132** \u2192 saat **1 pisteen** (oikea voittaja)
- Ottelu p\u00e4\u00e4ttyy **2\u20133** \u2192 saat **0 pistett\u00e4**
- Tasatilanteessa aiemmin l\u00e4hetetty veikkaus voittaa.
"""
)

st.divider()

st.header("Osallistumismaksu")
st.write("20 euroa per osallistuja. Maksu tulee suorittaa ennen ensimm\u00e4ist\u00e4 ottelua.")

st.divider()

st.header("Palkinnonjako")
st.write("1. sija: **60 %**")
st.write("2. sija: **30 %**")
st.write("3. sija: **10 %**")

st.divider()

st.header("Pudotuspeliveikkaukset")
st.write(
    "Alkulohkon tulosten lis\u00e4ksi veikataan pudotuspelikierrosten joukkueet, "
    "mestari sek\u00e4 yksil\u00f6palkinnot."
)
st.markdown(
    """
| Veikkaus | Pisteet | Maksimi |
|---|---|---|
| Oikea puoliv\u00e4lier\u00e4 | 1 p / kpl | 8 p |
| Oikea v\u00e4lier\u00e4 | 3 p / kpl | 12 p |
| Oikea finalisti | 5 p / kpl | 10 p |
| Oikea mestari | 10 p | 10 p |
| **Pudotuspelimaksimi yhteensa** | | **40 p** |
"""
)
st.write("Maalientekija- ja pisteporssipisteytys ilmoitetaan erikseen.")

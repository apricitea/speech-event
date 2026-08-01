import streamlit as st

st.markdown("# Event Study: Abnormal Returns vs. News Days")
st.write("""
Flags trading days where BBRI's return deviates from what a market-model
regression (BBRI return ~ IHSG return) would predict by more than 2 standard
deviations, then checks which of those abnormal-return days coincide with a
CEO-speech-related news article.
""")

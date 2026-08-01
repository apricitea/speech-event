import streamlit as st

st.markdown("# News Sentiment")
st.write("""
Sentiment, topic, and summary for each scraped article, scored by a local
LLM (Ollama, llama3) on a 7-point scale from Very Negative to Very Positive,
with a Not Relevant class for articles that surfaced from the keyword search
but aren't actually about the CEO.
""")

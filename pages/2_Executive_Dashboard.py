import streamlit as st

st.set_page_config(page_title="Executive Dashboard", layout="wide")

st.title("2. Executive Dashboard")
st.caption("CFO-level risk overview")

col1, col2, col3 = st.columns(3)

col1.metric("Overall Risk", "Moderate", "Watch")
col2.metric("Dividend Sustainability", "Weakening", "-")
col3.metric("Refinancing Risk", "High", "+100bp stress")

st.info("This page will summarize the top risk signals that require CFO attention.")
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Client Pain Points", layout="wide")

st.title("1. Client Pain Points")
st.caption("From fragmented real estate data to CFO-level decision intelligence")

pain_points = pd.DataFrame(
    {
        "Client Pain Point": [
            "Data is scattered across DART, IR decks, Excel files, and internal systems",
            "Debt maturity and interest rate exposure are monitored separately",
            "Dividend sustainability requires manual scenario analysis",
            "Tax impact is not always integrated into capital allocation decisions",
            "Investor Q&A responses are repetitive and time-consuming",
            "Disclosure data quality is reviewed manually",
        ],
        "Business Risk": [
            "Delayed risk recognition",
            "Refinancing risk",
            "Dividend credibility risk",
            "Distorted hold/sell decisions",
            "Inconsistent investor communication",
            "Disclosure and governance risk",
        ],
        "Copilot Solution": [
            "Integrated CFO risk cockpit",
            "Debt maturity and rate stress monitor",
            "Dividend sustainability score",
            "Tax-adjusted scenario engine",
            "AI investor Q&A generator",
            "Disclosure quality flags",
        ],
    }
)

st.dataframe(pain_points, use_container_width=True)
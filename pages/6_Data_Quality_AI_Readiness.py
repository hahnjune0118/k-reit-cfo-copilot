import streamlit as st
import pandas as pd

st.set_page_config(page_title="Data Quality & AI Readiness", layout="wide")

st.title("6. Data Quality & AI Readiness")
st.caption("Diagnose whether the client has the data foundation required for AX transformation")

readiness = pd.DataFrame(
    {
        "Dimension": [
            "Data Availability",
            "Data Consistency",
            "KPI Standardization",
            "Scenario Capability",
            "Tax-Finance Integration",
            "AI Use Case Readiness",
        ],
        "Score": [4, 3, 3, 2, 2, 3],
        "Interpretation": [
            "Core data exists",
            "Some inconsistencies need review",
            "KPI definitions require standardization",
            "Scenario logic is partially manual",
            "Tax impact is not fully embedded",
            "Initial AI use cases are identifiable",
        ],
    }
)

st.dataframe(readiness, use_container_width=True)

avg_score = readiness["Score"].mean()
st.metric("AI Readiness Score", f"{avg_score:.1f} / 5")
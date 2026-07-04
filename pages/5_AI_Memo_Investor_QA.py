import streamlit as st

st.set_page_config(page_title="AI Memo & Investor Q&A", layout="wide")

st.title("5. AI Memo & Investor Q&A")
st.caption("Convert quantitative analysis into CFO briefing and investor communication")

company = st.selectbox("Select REIT", ["SK REIT", "Lotte REIT", "ESR Kendall Square REIT"])
focus = st.selectbox("Memo Focus", ["Dividend sustainability", "Refinancing risk", "Asset value decline", "Investor communication"])

if st.button("Generate Draft Memo"):
    st.markdown(
        f"""
        ### CFO Briefing Memo - {company}

        Under the selected scenario, the key issue is **{focus}**.
        The CFO should monitor the combined impact of interest expense, asset-level cash flow,
        debt maturity concentration, and dividend capacity.

        Recommended actions:
        1. Review near-term refinancing exposure.
        2. Assess dividend buffer under downside scenarios.
        3. Prepare investor-facing explanation for key risk drivers.
        """
    )
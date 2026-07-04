import streamlit as st

st.set_page_config(
    page_title="K-REIT CFO Copilot",
    page_icon="🏢",
    layout="wide",
)

st.title("K-REIT CFO Copilot")
st.subheader("AI-powered decision intelligence for listed REIT CFOs, AMCs, and IR teams")

st.markdown(
    """
    This project is a client-facing AX prototype designed to help listed REIT CFOs,
    AMCs, and IR teams integrate fragmented signals across interest rates, debt maturity,
    asset-level risk, tax impact, dividend sustainability, and disclosure quality.

    The goal is not only to automate analysis, but to redesign the CFO decision workflow:
    from scattered data to scenario-based insight, management briefing, and investor communication.
    """
)

st.info(
    "Use the sidebar to navigate across the six AX consulting modules."
)

st.markdown(
    """
    ### Six Core Modules

    1. **Client Pain Points**  
       Define the customer problem before showing the solution.

    2. **Executive Dashboard**  
       Summarize the REIT's key risk signals for CFO-level attention allocation.

    3. **Scenario Engine**  
       Simulate the impact of interest rates, rent changes, asset value changes, and tax effects.

    4. **Asset & Debt Risk**  
       Identify which assets, tenants, and debt maturities drive portfolio risk.

    5. **AI Memo & Investor Q&A**  
       Convert numbers into CFO briefing memos and investor-facing explanations.

    6. **Data Quality & AI Readiness**  
       Diagnose whether the client has the data foundation required for AX transformation.
    """
)
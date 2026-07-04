import pandas as pd
import plotly.express as px
import streamlit as st

from modules.ui_components import hero, setup_page, signal_card


setup_page(
    "1. Client Pain Points",
    "From fragmented real estate data to CFO-level decision intelligence",
)

hero(
    "Customer problem first",
    "Listed REIT finance teams need a decision platform, not another accounting automation screen",
    "The prototype is framed around CFO, AMC, and IR pain points: capital-market pressure, dividend "
    "credibility, asset-level evidence, tax leakage, disclosure consistency, and AX readiness.",
)

pain_points = pd.DataFrame(
    [
        {
            "Client pain point": "Data is scattered across DART, IR decks, Excel files, and internal systems",
            "CFO decision cost": "Delayed risk recognition",
            "Copilot response": "Integrated CFO risk cockpit",
            "Business impact": "Faster leadership attention allocation",
        },
        {
            "Client pain point": "Debt maturity and interest rate exposure are monitored separately",
            "CFO decision cost": "Refinancing risk is explained too late",
            "Copilot response": "Debt maturity and rate stress monitor",
            "Business impact": "Earlier lender and market-window planning",
        },
        {
            "Client pain point": "Dividend sustainability depends on manual scenario analysis",
            "CFO decision cost": "Dividend credibility risk",
            "Copilot response": "Tax-adjusted dividend coverage score",
            "Business impact": "Clearer board and investor guidance",
        },
        {
            "Client pain point": "Tax impact is not embedded in capital allocation decisions",
            "CFO decision cost": "Hold, sell, and refinance decisions miss cash leakage",
            "Copilot response": "Tax-adjusted scenario engine",
            "Business impact": "Better cash-flow visibility after tax",
        },
        {
            "Client pain point": "Investor Q&A responses are repetitive and time-consuming",
            "CFO decision cost": "Inconsistent investor communication",
            "Copilot response": "Rule-based memo and Q&A generator",
            "Business impact": "More consistent management narrative",
        },
        {
            "Client pain point": "Disclosure data quality is reviewed manually",
            "CFO decision cost": "Governance and readiness gaps",
            "Copilot response": "Disclosure flags and AI readiness diagnostics",
            "Business impact": "Practical roadmap for AX transformation",
        },
        {
            "Client pain point": "Risk indicators are monitored after issues are already visible to the market",
            "CFO decision cost": "Late escalation of maturity, valuation, and disclosure risks",
            "Copilot response": "CFO early-warning cockpit",
            "Business impact": "Earlier cross-functional response planning",
        },
    ]
)

st.subheader("Pain Point to Decision Outcome Map")
st.dataframe(pain_points, width="stretch", hide_index=True)

stakeholder_view = pd.DataFrame(
    [
        {"Stakeholder": "CFO", "Pain area": "Dividend credibility", "Urgency": 92, "Current friction": 84},
        {"Stakeholder": "CFO", "Pain area": "Refinancing planning", "Urgency": 95, "Current friction": 88},
        {"Stakeholder": "AMC", "Pain area": "Asset-level evidence", "Urgency": 82, "Current friction": 76},
        {"Stakeholder": "AMC", "Pain area": "Tax-aware hold/sell view", "Urgency": 78, "Current friction": 72},
        {"Stakeholder": "IR", "Pain area": "Investor Q&A consistency", "Urgency": 86, "Current friction": 80},
        {"Stakeholder": "IR", "Pain area": "Disclosure quality", "Urgency": 81, "Current friction": 74},
        {"Stakeholder": "CFO", "Pain area": "Early warning indicators", "Urgency": 88, "Current friction": 79},
        {"Stakeholder": "AMC", "Pain area": "Control-ready AI adoption", "Urgency": 80, "Current friction": 75},
    ]
)

left, right = st.columns([1.2, 1])

with left:
    fig = px.bar(
        stakeholder_view,
        x="Urgency",
        y="Pain area",
        color="Stakeholder",
        orientation="h",
        color_discrete_map={"CFO": "#263b5e", "AMC": "#007c89", "IR": "#b76e00"},
        labels={"Pain area": "", "Urgency": "Decision urgency"},
    )
    fig.update_layout(height=390, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, width="stretch")

with right:
    st.subheader("Consulting Narrative")
    signal_card(
        "CFO",
        "Capital markets pressure",
        "Needs a single view of refinancing exposure, dividend capacity, and cash-flow sensitivity.",
    )
    signal_card(
        "AMC",
        "Asset evidence gap",
        "Needs asset-specific risk ranking that ties occupancy, WALE, tenants, capex, and valuation to decisions.",
    )
    signal_card(
        "IR",
        "Narrative consistency",
        "Needs repeatable investor answers grounded in approved metrics and disclosure flags.",
    )


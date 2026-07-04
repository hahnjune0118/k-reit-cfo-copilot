import plotly.express as px
import streamlit as st

from modules.data_loader import load_all_data
from modules.risk_scoring import executive_signal_table
from modules.ui_components import format_krw_bn, hero, setup_page, signal_card


setup_page(
    "K-REIT CFO Copilot",
    "AI-powered decision intelligence for listed REIT CFOs, AMCs, and IR teams",
)

data = load_all_data()
signals = executive_signal_table(
    data["reits"],
    data["assets"],
    data["debt"],
    data["readiness"],
    data["flags"],
)

hero(
    "AX consulting prototype",
    "Decision intelligence for listed REIT leadership teams",
    "K-REIT CFO Copilot converts fragmented portfolio, debt, tax, disclosure, and IR signals into "
    "scenario-based decisions, management narrative, and AI readiness diagnostics.",
)

col1, col2, col3 = st.columns(3)
with col1:
    signal_card(
        "Client problem",
        "Fragmented decisions",
        "Debt, asset, tax, dividend, and disclosure workstreams are usually reviewed in separate files.",
    )
with col2:
    signal_card(
        "Copilot lens",
        "CFO action cockpit",
        "The prototype brings risk signals into one decision model for CFOs, AMCs, and IR teams.",
    )
with col3:
    signal_card(
        "Business impact",
        "Faster narrative alignment",
        "Scenario outputs flow into briefing memos, investor Q&A, and AX readiness priorities.",
    )

st.subheader("Portfolio Signal Snapshot")

metric_cols = st.columns(4)
metric_cols[0].metric("Listed REITs in sample", f"{len(data['reits'])}")
metric_cols[1].metric("Gross asset value", format_krw_bn(data["reits"]["gross_asset_value_krw_bn"].sum()))
metric_cols[2].metric("Debt facilities", f"{len(data['debt'])}")
metric_cols[3].metric("Open disclosure flags", f"{len(data['flags'])}")

chart_col, table_col = st.columns([1.25, 1])

with chart_col:
    fig = px.bar(
        signals,
        x="reit_name",
        y="refinancing_risk_score",
        color="risk_tier",
        color_discrete_map={"High": "#c94f4f", "Medium": "#b76e00", "Low": "#007c89"},
        labels={"reit_name": "", "refinancing_risk_score": "Refinancing risk score"},
        text=signals["refinancing_risk_score"].round(0),
    )
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=20, b=10), showlegend=True)
    fig.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(fig, width="stretch")

with table_col:
    st.dataframe(
        signals[
            [
                "reit_name",
                "dividend_status",
                "dividend_coverage",
                "refinancing_risk_score",
                "ai_readiness_score",
                "open_flags",
            ]
        ].rename(
            columns={
                "reit_name": "REIT",
                "dividend_status": "Dividend status",
                "dividend_coverage": "Coverage",
                "refinancing_risk_score": "Refi risk",
                "ai_readiness_score": "AI readiness",
                "open_flags": "Flags",
            }
        ),
        width="stretch",
        hide_index=True,
    )

st.subheader("Six-Page Decision Platform")

modules = [
    {
        "Page": "Client Pain Points",
        "Decision question": "Where does the CFO workflow break today?",
        "Primary output": "Pain point to business impact map",
    },
    {
        "Page": "Executive Dashboard",
        "Decision question": "Which risk signals deserve leadership attention now?",
        "Primary output": "Dividend, refinancing, readiness, and disclosure cockpit",
    },
    {
        "Page": "Scenario Engine",
        "Decision question": "How do rates, rents, values, and tax move cash flow?",
        "Primary output": "Tax-adjusted cash flow and dividend coverage bridge",
    },
    {
        "Page": "Asset & Debt Risk",
        "Decision question": "Which assets and maturities are driving risk?",
        "Primary output": "Asset risk ranking and debt maturity wall",
    },
    {
        "Page": "AI Memo & Investor Q&A",
        "Decision question": "How should management explain the numbers?",
        "Primary output": "Rule-based CFO memo and investor answer draft",
    },
    {
        "Page": "Data Quality & AI Readiness",
        "Decision question": "Is the client ready to scale AI-enabled reporting?",
        "Primary output": "AX readiness score and data remediation roadmap",
    },
]

st.dataframe(modules, width="stretch", hide_index=True)


import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modules.data_loader import load_all_data, reit_id_from_name, reit_options
from modules.risk_scoring import debt_maturity_wall, executive_signal_table, score_assets
from modules.scenario_engine import run_scenario
from modules.ui_components import format_krw_bn, format_pct, hero, setup_page


setup_page("2. CFO Executive Dashboard", "CFO 관점의 dividend, refinancing, Data Quality signal")

data = load_all_data()
reits = data["reits"]
assets = data["assets"]
debt = data["debt"]
flags = data["flags"]
readiness = data["readiness"]

selected_name = st.sidebar.selectbox("Portfolio 선택", reit_options(reits), index=0)
reit_id = reit_id_from_name(reits, selected_name)
reit = reits[reits["reit_id"] == reit_id].iloc[0]
reit_assets = assets[assets["reit_id"] == reit_id]
reit_debt = debt[debt["reit_id"] == reit_id]
reit_flags = flags[flags["reit_id"] == reit_id]

base = run_scenario(reit, reit_assets, reit_debt)
signals = executive_signal_table(reits, assets, debt, readiness, flags)
selected_signal = signals[signals["reit_id"] == reit_id].iloc[0]

hero(
    "Executive Dashboard",
    f"{selected_name}: 다음 management discussion을 위한 핵심 signal",
    f"Management priority: {reit['management_priority']}. 이 Dashboard는 dividend coverage, refinancing risk, "
    "asset pressure, disclosure flags, AI Readiness를 CFO 관점의 leadership view로 연결합니다.",
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Dividend coverage", f"{base['dividend_coverage']:.2f}x", base["dividend_status"])
col2.metric("Refinancing Risk Score", f"{base['refinancing_risk_score']:.0f}/100", base["refinancing_status"])
col3.metric("Stressed LTV", format_pct(base["stressed_ltv_pct"]), "base case")
col4.metric("AI Readiness", f"{selected_signal['ai_readiness_score']:.1f}/5", f"{int(selected_signal['open_flags'])} flags")

left, right = st.columns([1.15, 1])

with left:
    st.subheader("Peer Risk Position")
    fig = px.scatter(
        signals,
        x="dividend_coverage",
        y="refinancing_risk_score",
        size="tax_adjusted_cash_flow_krw_bn",
        color="risk_tier",
        hover_name="reit_name",
        color_discrete_map={"High": "#c94f4f", "Medium": "#b76e00", "Low": "#007c89"},
        labels={
            "dividend_coverage": "Dividend coverage",
            "refinancing_risk_score": "Refinancing Risk Score",
        },
    )
    fig.add_vline(x=1.0, line_dash="dash", line_color="#667085")
    fig.update_layout(height=390, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, width="stretch")

with right:
    st.subheader("Selected REIT Snapshot")
    gauge = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=base["dividend_sustainability_score"],
            title={"text": "Dividend Sustainability Score"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#007c89"},
                "steps": [
                    {"range": [0, 45], "color": "#f8d7da"},
                    {"range": [45, 70], "color": "#fff1cc"},
                    {"range": [70, 100], "color": "#d9f0ee"},
                ],
            },
        )
    )
    gauge.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=10))
    st.plotly_chart(gauge, width="stretch")
    st.write(
        f"Tax-adjusted cash flow: **{format_krw_bn(base['tax_adjusted_cash_flow_krw_bn'], 1)}**. "
        f"Near-term debt: **{format_krw_bn(base['near_term_debt_krw_bn'], 0)}**."
    )

bottom_left, bottom_right = st.columns([1.2, 1])

with bottom_left:
    st.subheader("Debt Maturity Wall")
    wall = debt_maturity_wall(reit_debt)
    fig = px.bar(
        wall,
        x="maturity_year",
        y="principal_krw_bn",
        color_discrete_sequence=["#263b5e"],
        labels={"maturity_year": "Maturity year", "principal_krw_bn": "Principal (KRW bn)"},
        text="principal_krw_bn",
    )
    fig.update_layout(height=330, margin=dict(l=10, r=10, t=20, b=10))
    fig.update_traces(texttemplate="%{text:.0f}", textposition="outside", cliponaxis=False)
    st.plotly_chart(fig, width="stretch")

with bottom_right:
    st.subheader("Top Attention Items")
    asset_scores = score_assets(reit_assets).head(3)
    attention = asset_scores[["asset_name", "risk_tier", "asset_risk_score"]].rename(
        columns={"asset_name": "Asset", "risk_tier": "Risk tier", "asset_risk_score": "Asset Risk Score"}
    )
    st.dataframe(attention, width="stretch", hide_index=True)
    if not reit_flags.empty:
        st.dataframe(
            reit_flags[["area", "severity", "recommended_action"]].rename(
                columns={"area": "공시 영역", "severity": "Severity", "recommended_action": "권고 Action"}
            ),
            width="stretch",
            hide_index=True,
        )

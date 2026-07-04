import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modules.data_loader import load_all_data, reit_id_from_name, reit_options
from modules.scenario_engine import run_peer_scenarios, run_scenario, scenario_waterfall
from modules.ui_components import format_krw_bn, format_pct, hero, setup_page


setup_page("3. Scenario Engine", "금리, rent, asset value, tax impact 기반 scenario analysis")

data = load_all_data()
reits = data["reits"]
assets = data["assets"]
debt = data["debt"]

selected_name = st.sidebar.selectbox("REIT 선택", reit_options(reits), index=0)
reit_id = reit_id_from_name(reits, selected_name)
reit = reits[reits["reit_id"] == reit_id].iloc[0]
reit_assets = assets[assets["reit_id"] == reit_id]
reit_debt = debt[debt["reit_id"] == reit_id]

hero(
    "Scenario Engine",
    "투자자가 가장 자주 묻는 변수들을 CFO 관점으로 stress test",
    "interest rate shock, rent change, asset value change, tax impact를 tax-adjusted cash flow, "
    "dividend coverage, refinancing risk, LTV로 연결합니다.",
)

st.subheader("Scenario Assumptions")
col1, col2, col3, col4 = st.columns(4)
with col1:
    rate_shock = st.slider("Interest rate shock (bp)", -100, 300, 100, 25)
with col2:
    rent_change = st.slider("Rent change (%)", -12.0, 12.0, -2.0, 0.5)
with col3:
    asset_value_change = st.slider("Asset value change (%)", -25.0, 15.0, -5.0, 0.5)
with col4:
    tax_impact = st.slider("Tax impact (% of NOI)", -3.0, 8.0, 1.0, 0.5)

scenario = run_scenario(
    reit,
    reit_assets,
    reit_debt,
    rate_shock_bp=rate_shock,
    rent_change_pct=rent_change,
    asset_value_change_pct=asset_value_change,
    tax_impact_pct=tax_impact,
)

metric_cols = st.columns(5)
metric_cols[0].metric("Tax-adjusted cash flow", format_krw_bn(scenario["tax_adjusted_cash_flow_krw_bn"], 1))
metric_cols[1].metric("Dividend coverage", f"{scenario['dividend_coverage']:.2f}x", scenario["dividend_status"])
metric_cols[2].metric("Refinancing Risk Score", f"{scenario['refinancing_risk_score']:.0f}/100", scenario["refinancing_status"])
metric_cols[3].metric("Stressed LTV", format_pct(scenario["stressed_ltv_pct"]))
metric_cols[4].metric("Dividend buffer", format_krw_bn(scenario["dividend_buffer_krw_bn"], 1))

left, right = st.columns([1.2, 1])

with left:
    st.subheader("Cash-flow Bridge")
    waterfall = scenario_waterfall(scenario)
    fig = go.Figure(
        go.Waterfall(
            x=waterfall["driver"],
            y=waterfall["amount_krw_bn"],
            measure=waterfall["measure"],
            connector={"line": {"color": "#667085"}},
            increasing={"marker": {"color": "#007c89"}},
            decreasing={"marker": {"color": "#c94f4f"}},
            totals={"marker": {"color": "#263b5e"}},
        )
    )
    fig.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=20, b=10),
        yaxis_title="KRW bn",
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch")

with right:
    st.subheader("Scenario Detail")
    detail_rows = [
        {"주요 Driver": "Base FFO", "Impact": format_krw_bn(scenario["base_ffo_krw_bn"], 1)},
        {"주요 Driver": "Rent change", "Impact": format_krw_bn(scenario["rent_delta_krw_bn"], 1)},
        {"주요 Driver": "Rate/refinancing shock", "Impact": f"-{format_krw_bn(scenario['interest_delta_krw_bn'], 1)}"},
        {"주요 Driver": "Tax impact", "Impact": f"-{format_krw_bn(scenario['tax_delta_krw_bn'], 1)}"},
        {"주요 Driver": "Near-term debt", "Impact": format_krw_bn(scenario["near_term_debt_krw_bn"], 0)},
        {"주요 Driver": "Floating-rate debt share", "Impact": format_pct(scenario["floating_rate_pct"])},
    ]
    st.dataframe(detail_rows, width="stretch", hide_index=True)

st.subheader("Peer Impact Under Same Scenario")
peer = run_peer_scenarios(
    reits,
    assets,
    debt,
    rate_shock_bp=rate_shock,
    rent_change_pct=rent_change,
    asset_value_change_pct=asset_value_change,
    tax_impact_pct=tax_impact,
)
peer_chart = px.bar(
    peer.sort_values("dividend_coverage"),
    x="reit_name",
    y="dividend_coverage",
    color="dividend_status",
    color_discrete_map={"Resilient": "#007c89", "Defensible": "#263b5e", "Watch": "#b76e00", "Pressure": "#c94f4f"},
    labels={"reit_name": "", "dividend_coverage": "Dividend coverage"},
    text=peer["dividend_coverage"].round(2),
)
peer_chart.add_hline(y=1.0, line_dash="dash", line_color="#667085")
peer_chart.update_layout(height=360, margin=dict(l=10, r=10, t=20, b=10))
peer_chart.update_traces(textposition="outside", cliponaxis=False)
st.plotly_chart(peer_chart, width="stretch")

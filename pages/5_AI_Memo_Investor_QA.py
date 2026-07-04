import streamlit as st

from modules.data_loader import load_all_data, reit_id_from_name, reit_options
from modules.memo_generator import generate_cfo_memo, generate_investor_qa
from modules.risk_scoring import score_assets
from modules.scenario_engine import run_scenario
from modules.ui_components import hero, setup_page


setup_page("5. AI Memo & Investor Q&A", "Convert quantitative analysis into CFO briefing and investor communication")

data = load_all_data()
reits = data["reits"]
assets = data["assets"]
debt = data["debt"]
flags = data["flags"]

selected_name = st.sidebar.selectbox("REIT", reit_options(reits), index=0)
focus = st.sidebar.selectbox(
    "Memo focus",
    ["Dividend sustainability", "Refinancing risk", "Asset value decline", "Investor communication"],
)
reit_id = reit_id_from_name(reits, selected_name)
reit = reits[reits["reit_id"] == reit_id].iloc[0]
reit_assets = assets[assets["reit_id"] == reit_id]
reit_debt = debt[debt["reit_id"] == reit_id]
reit_flags = flags[flags["reit_id"] == reit_id]

hero(
    "Management narrative generator",
    "Turn scenario outputs into CFO-ready language",
    "This MVP uses deterministic rules and approved data fields only. It is designed to show how future AI "
    "workflows can draft management memos and investor answers without calling external LLM APIs.",
)

st.subheader("Narrative Scenario Inputs")
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
asset_scores = score_assets(reit_assets)

memo = generate_cfo_memo(selected_name, focus, scenario, asset_scores, reit_flags)
qa = generate_investor_qa(selected_name, focus, scenario, asset_scores, reit_flags)

tabs = st.tabs(["CFO Briefing Memo", "Investor Q&A Draft", "Evidence Pack"])

with tabs[0]:
    st.markdown(memo)

with tabs[1]:
    st.markdown(qa)

with tabs[2]:
    cols = st.columns(4)
    cols[0].metric("Dividend coverage", f"{scenario['dividend_coverage']:.2f}x", scenario["dividend_status"])
    cols[1].metric("Refi risk", f"{scenario['refinancing_risk_score']:.0f}/100", scenario["refinancing_status"])
    cols[2].metric("Tax-adjusted CF", f"KRW {scenario['tax_adjusted_cash_flow_krw_bn']:,.1f}bn")
    cols[3].metric("Stressed LTV", f"{scenario['stressed_ltv_pct']:,.1f}%")

    st.dataframe(
        asset_scores[["asset_name", "risk_tier", "asset_risk_score", "strategic_importance"]].rename(
            columns={
                "asset_name": "Asset",
                "risk_tier": "Risk",
                "asset_risk_score": "Score",
                "strategic_importance": "Strategic note",
            }
        ),
        width="stretch",
        hide_index=True,
    )
    st.dataframe(
        reit_flags[["area", "severity", "flag", "recommended_action"]].rename(
            columns={"area": "Area", "severity": "Severity", "flag": "Flag", "recommended_action": "Action"}
        ),
        width="stretch",
        hide_index=True,
    )

combined_text = f"{memo}\n\n{qa}"
st.download_button(
    "Download memo and Q&A draft",
    data=combined_text,
    file_name=f"{reit_id}_cfo_memo_investor_qa.md",
    mime="text/markdown",
)


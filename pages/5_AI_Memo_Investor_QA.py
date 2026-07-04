import streamlit as st

from modules.data_loader import load_all_data, reit_id_from_name, reit_options
from modules.memo_generator import FOCUS_LABELS, generate_cfo_memo, generate_investor_qa
from modules.risk_scoring import score_assets
from modules.scenario_engine import run_scenario
from modules.ui_components import hero, setup_page


setup_page("5. AI Memo & Investor Q&A", "scenario 결과를 CFO briefing과 investor communication으로 전환")

data = load_all_data()
reits = data["reits"]
assets = data["assets"]
debt = data["debt"]
flags = data["flags"]

selected_name = st.sidebar.selectbox("REIT 선택", reit_options(reits), index=0)
focus = st.sidebar.selectbox(
    "Memo focus",
    list(FOCUS_LABELS.keys()),
    format_func=lambda key: FOCUS_LABELS[key],
)
reit_id = reit_id_from_name(reits, selected_name)
reit = reits[reits["reit_id"] == reit_id].iloc[0]
reit_assets = assets[assets["reit_id"] == reit_id]
reit_debt = debt[debt["reit_id"] == reit_id]
reit_flags = flags[flags["reit_id"] == reit_id]

hero(
    "Management narrative generator",
    "숫자를 CFO-ready language와 Investor Q&A draft로 전환",
    "현재 버전은 외부 LLM API를 사용하지 않습니다. approved data field와 rule-based logic만으로 "
    "CFO Memo와 Investor Q&A 초안을 생성해 향후 AI workflow의 구조를 보여줍니다.",
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
    cols[1].metric("Refi Risk Score", f"{scenario['refinancing_risk_score']:.0f}/100", scenario["refinancing_status"])
    cols[2].metric("Tax-adjusted CF", f"KRW {scenario['tax_adjusted_cash_flow_krw_bn']:,.1f}bn")
    cols[3].metric("Stressed LTV", f"{scenario['stressed_ltv_pct']:,.1f}%")

    st.dataframe(
        asset_scores[["asset_name", "risk_tier", "asset_risk_score", "strategic_importance"]].rename(
            columns={
                "asset_name": "Asset",
                "risk_tier": "Risk tier",
                "asset_risk_score": "Asset Risk Score",
                "strategic_importance": "전략적 해석",
            }
        ),
        width="stretch",
        hide_index=True,
    )
    st.dataframe(
        reit_flags[["area", "severity", "flag", "recommended_action"]].rename(
            columns={"area": "공시 영역", "severity": "Severity", "flag": "Flag", "recommended_action": "권고 Action"}
        ),
        width="stretch",
        hide_index=True,
    )

combined_text = f"{memo}\n\n{qa}"
st.download_button(
    "Memo 및 Investor Q&A draft 다운로드",
    data=combined_text,
    file_name=f"{reit_id}_cfo_memo_investor_qa.md",
    mime="text/markdown",
)

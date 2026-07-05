import streamlit as st

from modules.data_loader import load_all_data, reit_id_from_name, reit_options
from modules.memo_generator import (
    FOCUS_LABELS,
    generate_cfo_memo,
    generate_investor_qa,
    markdown_to_plain_text,
)
from modules.risk_scoring import attention_scores, score_assets, top_cfo_alerts
from modules.scenario_engine import run_scenario
from modules.ui_components import hero, setup_page


setup_page(
    "5. AI Memo & Investor Q&A",
    "정량 scenario output을 management language와 investor-facing communication으로 전환",
)

data = load_all_data()
reits = data["reits"]
assets = data["assets"]
debt = data["debt"]
flags = data["flags"]
readiness = data["readiness"]

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
reit_readiness = readiness[readiness["reit_id"] == reit_id]

hero(
    "Management narrative generator",
    "분석 자동화를 넘어 CFO 보고 언어와 Investor Q&A 초안으로 전환",
    "v05는 외부 LLM API를 사용하지 않습니다. Scenario Engine output과 CFO Dashboard risk input을 "
    "rule-based logic으로 연결해 management narrative와 investor-facing communication draft를 생성합니다.",
)

st.subheader("Narrative Scenario Inputs")
col1, col2, col3, col4 = st.columns(4)
with col1:
    rate_shock = st.slider("금리 충격 (bp)", -50, 200, 100, 25)
with col2:
    rent_change = st.slider("임대료 변화율 (%)", -10.0, 10.0, -2.0, 0.5)
with col3:
    asset_value_change = st.slider("자산가치 변화율 (%)", -20.0, 10.0, -5.0, 0.5)
with col4:
    include_tax_effect = st.checkbox("세금효과 반영 여부", value=True)

tax_impact = 1.0 if include_tax_effect else 0.0
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
category_scores, overall = attention_scores(reit, reit_assets, reit_debt, reit_flags, reit_readiness)
alerts = top_cfo_alerts(category_scores)

memo = generate_cfo_memo(selected_name, focus, scenario, asset_scores, reit_flags, category_scores, overall)
qa = generate_investor_qa(selected_name, focus, scenario, asset_scores, reit_flags, category_scores, overall)
combined_markdown = f"{memo}\n\n---\n\n{qa}"
combined_text = markdown_to_plain_text(combined_markdown)

metric_cols = st.columns(5)
metric_cols[0].metric("AFFO estimate", f"KRW {scenario['affo_estimate_krw_bn']:,.1f}bn")
metric_cols[1].metric("Dividend buffer", f"KRW {scenario['dividend_buffer_krw_bn']:,.1f}bn", scenario["dividend_status"])
metric_cols[2].metric("Refi Risk Score", f"{scenario['refinancing_risk_score']:.0f}/100", scenario["refinancing_status"])
metric_cols[3].metric("Stressed LTV", f"{scenario['stressed_ltv_pct']:,.1f}%")
metric_cols[4].metric("Overall Risk", f"{overall['overall_score']:.0f}/100", overall["overall_label"])

tabs = st.tabs(["CFO Briefing Memo", "Investor Q&A Draft", "Evidence Pack"])

with tabs[0]:
    st.markdown(memo)
    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            "CFO Memo 다운로드 (.md)",
            data=memo,
            file_name=f"{reit_id}_cfo_briefing_memo.md",
            mime="text/markdown",
        )
    with dl2:
        st.download_button(
            "CFO Memo 다운로드 (.txt)",
            data=markdown_to_plain_text(memo),
            file_name=f"{reit_id}_cfo_briefing_memo.txt",
            mime="text/plain",
        )

with tabs[1]:
    st.markdown(qa)
    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            "Investor Q&A 다운로드 (.md)",
            data=qa,
            file_name=f"{reit_id}_investor_qa.md",
            mime="text/markdown",
        )
    with dl2:
        st.download_button(
            "Investor Q&A 다운로드 (.txt)",
            data=markdown_to_plain_text(qa),
            file_name=f"{reit_id}_investor_qa.txt",
            mime="text/plain",
        )

with tabs[2]:
    st.subheader("Scenario Evidence")
    cols = st.columns(4)
    cols[0].metric("FFO estimate", f"KRW {scenario['ffo_estimate_krw_bn']:,.1f}bn")
    cols[1].metric("AFFO estimate", f"KRW {scenario['affo_estimate_krw_bn']:,.1f}bn")
    cols[2].metric("Interest impact", f"KRW {scenario['interest_expense_impact_krw_bn']:,.1f}bn")
    cols[3].metric("Tax impact", f"KRW {scenario['tax_delta_krw_bn']:,.1f}bn")

    st.subheader("Top CFO Alerts Feeding Narrative")
    st.dataframe(
        alerts.rename(
            columns={
                "alert_rank": "Rank",
                "category": "Risk category",
                "score": "Risk Score",
                "label": "Label",
                "why": "왜 중요한가",
                "action": "권고 액션",
            }
        ),
        width="stretch",
        hide_index=True,
    )

    st.subheader("Asset & Disclosure Evidence")
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

st.download_button(
    "Memo + Investor Q&A 통합 다운로드 (.md)",
    data=combined_markdown,
    file_name=f"{reit_id}_memo_investor_qa_pack.md",
    mime="text/markdown",
)
st.download_button(
    "Memo + Investor Q&A 통합 다운로드 (.txt)",
    data=combined_text,
    file_name=f"{reit_id}_memo_investor_qa_pack.txt",
    mime="text/plain",
)

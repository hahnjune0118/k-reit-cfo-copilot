import streamlit as st

from modules.data_loader import load_all_data, reit_id_from_name, reit_options
from modules.memo_generator import (
    FOCUS_LABELS,
    generate_cfo_memo,
    generate_investor_qa,
    markdown_to_plain_text,
)
from modules.real_reit_analytics import build_real_reit_dashboard_model
from modules.risk_scoring import attention_scores, score_assets, top_cfo_alerts
from modules.scenario_engine import run_scenario
from modules.ui_components import format_krw, get_real_mode_user_inputs, hero, is_real_api_mode, setup_page

try:
    import modules.real_mode_components as real_components
except Exception:
    real_components = None


def _real_component(name, fallback):
    return getattr(real_components, name, fallback) if real_components is not None else fallback


def _fallback_real_mode_warning(*args, **kwargs):
    st.warning(
        "Real API Mode는 OpenDART·ECOS 등 공개 API로 조회 가능한 사실 정보와 사용자가 직접 입력한 "
        "가정만을 기반으로 합니다. 본 화면은 실제 기업에 대한 투자 의견, 신용 판단, 부정적 리스크 평가를 "
        "제공하지 않습니다."
    )


def _fallback_select_real_reit(*args, **kwargs):
    import pandas as pd

    st.sidebar.info("Real REIT 선택 컴포넌트를 불러오지 못해 fallback 값을 사용합니다.")
    return pd.Series({"real_reit_name": "선택 REIT", "ticker": "", "corp_code": "", "notes": ""})


def _fallback_real_reit_factual_panel(*args, **kwargs):
    st.info("Real REIT factual panel을 불러오지 못했습니다.")


def _fallback_empty_frame_component(message):
    def _inner(*args, **kwargs):
        import pandas as pd

        st.info(message)
        return pd.DataFrame()

    return _inner


def _fallback_real_mode_cfo_interpretation(*args, **kwargs):
    st.info(
        "Real API Mode 해석 컴포넌트를 불러오지 못했습니다. "
        "공개 API 기반 factual data와 사용자 입력 기반 예비 시뮬레이션만 표시합니다."
    )


render_ecos_market_rate_panel = _real_component(
    "render_ecos_market_rate_panel", _fallback_empty_frame_component("ECOS 금리 데이터가 없거나 API fallback 상태입니다.")
)
render_opendart_disclosure_monitor = _real_component(
    "render_opendart_disclosure_monitor", _fallback_empty_frame_component("OpenDART Disclosure Monitor를 불러오지 못했습니다.")
)
render_real_mode_cfo_interpretation = _real_component(
    "render_real_mode_cfo_interpretation", _fallback_real_mode_cfo_interpretation
)
render_real_mode_warning = _real_component("render_real_mode_warning", _fallback_real_mode_warning)
render_real_reit_factual_panel = _real_component("render_real_reit_factual_panel", _fallback_real_reit_factual_panel)
select_real_reit = _real_component("select_real_reit", _fallback_select_real_reit)


setup_page(
    "5. AI Memo & Investor Q&A",
    "정량 scenario output을 management language와 investor-facing communication으로 전환",
)

if is_real_api_mode():
    hero(
        "v12 Real Mode AI Memo & Investor Q&A",
        "정량 output을 CFO-level management narrative와 IR communication draft로 전환",
        "외부 LLM API 없이 rule-based로 작성하며, source label과 confidence를 함께 표시합니다. 투자 의견, 신용 판단, 부정적 리스크 평가는 생성하지 않습니다.",
    )
    real_reit = select_real_reit("Real REIT 선택")
    focus = st.sidebar.selectbox(
        "Memo focus",
        list(FOCUS_LABELS.keys()),
        format_func=lambda key: FOCUS_LABELS[key],
    )
    model = build_real_reit_dashboard_model(real_reit, get_real_mode_user_inputs())
    analysis = model["analysis"]
    metrics = model["metrics"]
    risk_model = model["risk_model"]

    metric_cols = st.columns(4)
    risk_score_text = "Not Available" if risk_model["overall_score"] is None else f"{float(risk_model['overall_score']):.0f}/100"
    metric_cols[0].metric("Risk Score", risk_score_text, risk_model["overall_level"])
    metric_cols[1].metric("Score Type", risk_model["score_type"])
    metric_cols[2].metric("Dividend buffer", format_krw(metrics.get("dividend_buffer_krw")))
    metric_cols[3].metric("Refinancing 가정 금리", f"{float(metrics['refinancing_rate_pct']):.2f}%" if metrics.get("refinancing_rate_pct") is not None else "데이터 없음")

    alerts_text = "\n".join(
        f"- {row['Alert']}: {row['CFO Action']} [{row['Source']} / {row['Confidence']}]"
        for _, row in model["cfo_alerts"].iterrows()
    )
    validation_rows = model["collected_metrics"]
    validation_text = "\n".join(
        f"- {row['Metric']}: {row['Source Type']} / {row['Confidence']}"
        for _, row in validation_rows.iterrows()
        if row["Status"] == "미확보"
    )
    base_rate_text = f"{float(metrics['base_rate_pct']):.2f}%" if metrics.get("base_rate_pct") is not None else "데이터 없음"
    spread_text = (
        f"{float(metrics['refinancing_spread_pct']):.2f}%"
        if metrics.get("refinancing_spread_pct") is not None
        else "데이터 없음"
    )
    memo = f"""## CFO Briefing Memo

### 핵심 요약
- 선택 REIT: {metrics['reit_name']}
- Memo focus: {FOCUS_LABELS[focus]}
- Risk Score: {risk_score_text} ({risk_model['overall_level']})
- Score Type: {risk_model['score_type']}
- 주요 근거: OpenDART API, OpenDART Parsed, ECOS API 또는 fallback assumption을 source label로 구분

### 주요 리스크
{alerts_text}

### 배당가능성 영향
- Dividend buffer: {format_krw(metrics.get('dividend_buffer_krw'))}
- FFO/AFFO 산식은 OpenDART 재무제표와 공시 parser를 먼저 시도했으며, REIT별 조정항목은 manual validation이 필요합니다.

### 리파이낸싱 영향
- 기준금리: {base_rate_text}
- Refinancing spread assumption: {spread_text}
- 차입 만기 구조는 OpenDART 재무제표 기반 proxy를 먼저 사용하며, 약정별 만기는 공시 주석 또는 내부 treasury data 확인이 필요합니다.

### Board-level Risk Summary
- 전체 score는 사용 가능한 risk component 수에 따라 Full, Partial, Limited로 구분합니다.
- v12는 실제 상장 REIT의 투자 의견이나 신용 판단을 제시하지 않고, CFO가 확인해야 할 attention area만 정리합니다.

### 세금효과 고려사항
- 세금효과는 현재 공개 API로 자동 검증하지 않으며 별도 세무 검토가 필요합니다.

### CFO 권고 액션
{validation_text or "- Data Quality 페이지에서 source/confidence가 낮은 항목을 우선 확인하세요."}

> 본 memo는 투자 의견, 신용 판단, 부정적 리스크 평가가 아니며, 공개 API와 사용자 입력 가정 기반의 예비 draft입니다.
"""
    qa = f"""## Investor Q&A Draft

### 예상 질문
금리 및 refinancing spread 변화가 배당가능성과 차입비용에 어떤 영향을 줄 수 있습니까?

### 답변 초안
현재 분석은 OpenDART·ECOS 등 공개 API로 확인 가능한 factual data와 사용자가 입력한 가정, 그리고 수동 관리 macro assumption을 구분해 작성했습니다. Scenario 기준금리와 refinancing spread가 상승하면 interest expense impact와 dividend buffer가 변동할 수 있으므로, 회사는 공시 원문과 내부 treasury data를 기준으로 차입 만기 구조와 FFO/AFFO bridge를 확인해야 합니다.

당사가 현재 확인 가능한 범위는 [OpenDART API] 공시 목록, [OpenDART Parsed] 공시 원문 keyword evidence, [ECOS API/Fallback Assumption] 금리 가정, [KRX / Market Data] 시장 데이터입니다. 미확보 metric은 투자자 커뮤니케이션 전에 manual validation을 거쳐야 합니다.

### 커뮤니케이션 유의사항
- 실제 투자 판단이나 신용 판단으로 표현하지 않습니다.
- 데이터 미확보 항목은 “자동 수집 시도 후 미확보” 또는 “manual validation 필요”로 설명합니다.
- FFO, AFFO, WALE, 임차인 집중도, 자산별 NOI는 원문 공시 또는 내부 자료 확인 후 업데이트해야 합니다.
"""
    tabs = st.tabs(["CFO Briefing Memo", "Investor Q&A Draft", "Evidence Pack"])
    with tabs[0]:
        st.markdown(memo)
    with tabs[1]:
        st.markdown(qa)
    with tabs[2]:
        st.dataframe(model["collected_metrics"], width="stretch", hide_index=True)
        st.dataframe(model["cfo_alerts"], width="stretch", hide_index=True)
        with st.expander("Raw evidence snippets", expanded=False):
            snippets = model.get("parsed_evidence_snippets", [])
            if snippets:
                for item in snippets[:10]:
                    st.caption(f"[OpenDART Parsed] {item.get('keyword', '')}: {item.get('snippet', '')}")
            else:
                st.info("공시 원문 snippet은 아직 확보되지 않았습니다.")

    st.download_button("Real Mode Memo 다운로드 (.md)", data=memo, file_name="real_mode_cfo_memo.md", mime="text/markdown")
    st.download_button("Real Mode Investor Q&A 다운로드 (.md)", data=qa, file_name="real_mode_investor_qa.md", mime="text/markdown")
    st.stop()

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
metric_cols[0].metric("AFFO estimate", format_krw(scenario["affo_estimate_krw_bn"], unit="KRW_BN"))
metric_cols[1].metric("Dividend buffer", format_krw(scenario["dividend_buffer_krw_bn"], unit="KRW_BN"), scenario["dividend_status"])
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
    cols[0].metric("FFO estimate", format_krw(scenario["ffo_estimate_krw_bn"], unit="KRW_BN"))
    cols[1].metric("AFFO estimate", format_krw(scenario["affo_estimate_krw_bn"], unit="KRW_BN"))
    cols[2].metric("Interest impact", format_krw(scenario["interest_expense_impact_krw_bn"], unit="KRW_BN"))
    cols[3].metric("Tax impact", format_krw(scenario["tax_delta_krw_bn"], unit="KRW_BN"))

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

import plotly.express as px
import streamlit as st

from modules.data_loader import load_all_data, load_disclosure_data, load_market_rate_data, reit_id_from_name, reit_options
from modules.risk_scoring import (
    data_quality_flags,
    readiness_roadmap,
    readiness_score,
    weighted_readiness_score,
)
from modules.ui_components import hero, is_real_api_mode, setup_page, signal_card

try:
    import modules.real_mode_components as real_components
except Exception:
    real_components = None


def _real_component(name, fallback):
    return getattr(real_components, name, fallback) if real_components is not None else fallback


def _fallback_real_mode_warning(*args, **kwargs):
    st.warning(
        "Real API Mode는 공개 API factual data와 사용자 입력 가정만 표시합니다. "
        "투자 의견, 신용 판단, 부정적 리스크 평가는 제공하지 않습니다."
    )


def _fallback_select_real_reit(*args, **kwargs):
    import pandas as pd

    st.sidebar.info("Real REIT 선택 컴포넌트를 불러오지 못해 fallback 값을 사용합니다.")
    return pd.Series({"real_reit_name": "선택 REIT", "ticker": "", "corp_code": "", "notes": ""})


def _fallback_real_reit_factual_panel(*args, **kwargs):
    st.info("Real REIT factual panel을 불러오지 못했습니다.")


def _fallback_opendart_disclosure_monitor(*args, **kwargs):
    import pandas as pd

    st.info("OpenDART Disclosure Monitor를 불러오지 못했습니다.")
    return pd.DataFrame()


def _fallback_ecos_market_rate_panel(*args, **kwargs):
    import pandas as pd

    st.info("ECOS Market Rate Panel을 불러오지 못했습니다.")
    return pd.DataFrame()


def _fallback_real_mode_cfo_interpretation(*args, **kwargs):
    st.info(
        "Real API Mode 해석 컴포넌트를 불러오지 못했습니다. "
        "공개 API 기반 factual data와 사용자 입력 기반 예비 시뮬레이션만 표시합니다."
    )


def _fallback_data_availability_matrix(*args, **kwargs):
    import pandas as pd

    st.markdown("### Data Availability Matrix")
    st.info(
        "Data Availability Matrix 컴포넌트를 불러오지 못했습니다. "
        "Real API Mode에서는 공개 API로 자동화 가능한 항목과 manual validation이 필요한 항목을 구분해야 합니다."
    )
    fallback = pd.DataFrame(
        [
            {"Metric": "회사명 / ticker", "Source": "Real REIT master / OpenDART", "API availability": "부분 가능", "Automation level": "High", "Manual validation required?": "No", "Notes": "상장 REIT master data로 관리"},
            {"Metric": "OpenDART 공시 목록", "Source": "OpenDART", "API availability": "가능", "Automation level": "High", "Manual validation required?": "No", "Notes": "공시 목록 조회 가능"},
            {"Metric": "최근 정기공시", "Source": "OpenDART", "API availability": "가능", "Automation level": "High", "Manual validation required?": "Low", "Notes": "사업보고서·반기보고서·분기보고서 확인"},
            {"Metric": "기준금리 / 시장금리", "Source": "ECOS", "API availability": "가능", "Automation level": "High", "Manual validation required?": "No", "Notes": "Scenario Engine 금리 가정"},
            {"Metric": "FFO / AFFO", "Source": "사업보고서 / IR / 내부자료", "API availability": "제한적", "Automation level": "Low", "Manual validation required?": "Yes", "Notes": "REIT별 산식 검증 필요"},
            {"Metric": "WALE", "Source": "사업보고서 주석 / 내부자료", "API availability": "제한적", "Automation level": "Low", "Manual validation required?": "Yes", "Notes": "자산별 임대차 만기 확인 필요"},
            {"Metric": "임차인 집중도", "Source": "사업보고서 주석 / 내부자료", "API availability": "제한적", "Automation level": "Low", "Manual validation required?": "Yes", "Notes": "주요 임차인 및 비중 확인 필요"},
            {"Metric": "자산별 NOI", "Source": "사업보고서 / 내부자료", "API availability": "제한적", "Automation level": "Low", "Manual validation required?": "Yes", "Notes": "자산별 수익·비용 배분 확인 필요"},
            {"Metric": "차입 만기 구조", "Source": "사업보고서 주석 / 차입 약정", "API availability": "부분 가능", "Automation level": "Medium", "Manual validation required?": "Yes", "Notes": "공시 주석 파싱 및 검증 필요"},
            {"Metric": "세금효과", "Source": "세법 검토 / 내부 거래자료", "API availability": "불가", "Automation level": "Low", "Manual validation required?": "Yes", "Notes": "별도 세무 검토 필요"},
            {"Metric": "Investor Q&A", "Source": "공시 / IR / 사용자 입력", "API availability": "부분 가능", "Automation level": "Medium", "Manual validation required?": "Yes", "Notes": "현재 v10은 rule-based"},
        ]
    )
    st.dataframe(fallback, use_container_width=True)
    return fallback


render_data_availability_matrix = _real_component("render_data_availability_matrix", _fallback_data_availability_matrix)
render_ecos_market_rate_panel = _real_component("render_ecos_market_rate_panel", _fallback_ecos_market_rate_panel)
render_opendart_disclosure_monitor = _real_component(
    "render_opendart_disclosure_monitor", _fallback_opendart_disclosure_monitor
)
render_real_mode_cfo_interpretation = _real_component(
    "render_real_mode_cfo_interpretation", _fallback_real_mode_cfo_interpretation
)
render_real_mode_warning = _real_component("render_real_mode_warning", _fallback_real_mode_warning)
render_real_reit_factual_panel = _real_component("render_real_reit_factual_panel", _fallback_real_reit_factual_panel)
select_real_reit = _real_component("select_real_reit", _fallback_select_real_reit)


setup_page(
    "6. 데이터 품질 및 AI Readiness",
    "AX consulting diagnostic: AI를 적용하기 전에 데이터 기반과 프로세스 성숙도를 진단합니다.",
)

if is_real_api_mode():
    hero(
        "Real API Mode",
        "External Data Connection diagnostic",
        "Real API Mode에서는 공개 API 연결 상태와 factual data freshness를 확인합니다. "
        "AI Readiness Score는 실제 고객 내부 데이터와 인터뷰 없이 산정하지 않습니다.",
    )
    render_real_mode_warning()
    real_reit = select_real_reit("Readiness Real REIT 선택")
    render_real_reit_factual_panel(real_reit)
    disclosures = render_opendart_disclosure_monitor(real_reit)
    rates = render_ecos_market_rate_panel()
    render_real_mode_cfo_interpretation(real_reit, disclosures=disclosures, rates=rates)
    render_data_availability_matrix()
    st.subheader("AX Readiness 관점")
    st.info(
        "OpenDART와 ECOS 연결은 데이터 자동 수집, 데이터 최신성, 반복 업무 감소, 시나리오 분석 신뢰성 향상에 기여합니다. "
        "다만 실제 AI Readiness Score는 client internal data, KPI dictionary, approval workflow 확인 후 calibration해야 합니다."
    )
    st.stop()

data = load_all_data()
market_rates = load_market_rate_data(use_api=True)
external_disclosures = load_disclosure_data(use_api=True)
reits = data["reits"]
assets = data["assets"]
debt = data["debt"]
readiness = data["readiness"]
flags = data["flags"]

selected_name = st.sidebar.selectbox("REIT 선택", reit_options(reits), index=0)
reit_id = reit_id_from_name(reits, selected_name)
reit = reits[reits["reit_id"] == reit_id].iloc[0]
reit_assets = assets[assets["reit_id"] == reit_id].copy()
reit_debt = debt[debt["reit_id"] == reit_id].copy()
reit_readiness = readiness[readiness["reit_id"] == reit_id].copy()
reit_flags = flags[flags["reit_id"] == reit_id].copy()

weighted_readiness, readiness_diagnostic = weighted_readiness_score(reit_readiness)
quality_flags = data_quality_flags(reit, reit_assets, reit_debt, reit_flags, reit_readiness)
roadmap = readiness_roadmap(reit_readiness, quality_flags)
peer_scores = readiness_score(readiness, flags).merge(reits[["reit_id", "reit_name"]], on="reit_id", how="left")

interpretation = readiness_diagnostic["interpretation"]
weighted_score = float(readiness_diagnostic["weighted_score"])
weighted_score_pct = float(readiness_diagnostic["weighted_score_pct"])
high_or_watch_flags = int(quality_flags["status"].isin(["High", "Watch"]).sum())
high_flags = int((quality_flags["status"] == "High").sum())
lowest_dimension = weighted_readiness.sort_values("score").iloc[0]

interpretation_text = {
    "Strong": "AI Memo, Investor Q&A, Scenario Engine을 운영 프로세스에 연결할 수 있는 기반이 비교적 안정적입니다.",
    "Moderate": "핵심 데이터는 존재하지만 KPI 정의, 검증 흐름, tax-finance 연결을 보완해야 AX 확장이 가능합니다.",
    "Needs Improvement": "AI 적용보다 먼저 source-of-truth, Data Quality rule, 승인 workflow를 정비해야 합니다.",
}

status_palette = {
    "High": "#c94f4f",
    "Watch": "#b76e00",
    "Low": "#007c89",
}

hero(
    "Data Quality & AI Readiness",
    f"{selected_name} AX 진단 모듈",
    "AX consulting은 AI 기능을 붙이는 것에서 시작하지 않습니다. REIT CFO, AMC, IR팀이 신뢰할 수 있는 "
    "데이터 기반과 KPI 표준화, Scenario Capability, Tax-Finance Integration을 갖추었는지 먼저 진단합니다.",
)

st.subheader("External Data Connection")
dart_fallback = bool(external_disclosures.attrs.get("is_fallback", True))
ecos_fallback = bool(market_rates.attrs.get("is_fallback", True))
latest_rate = float(market_rates.sort_values("date").iloc[-1]["market_rate_pct"]) if not market_rates.empty else 0.0
connection_cols = st.columns(3)
connection_cols[0].metric("OpenDART 연결 상태", "Sample fallback" if dart_fallback else "Connected")
connection_cols[1].metric("ECOS 연결 상태", "Sample fallback" if ecos_fallback else "Connected")
connection_cols[2].metric("Sample data fallback 여부", "예" if dart_fallback or ecos_fallback else "아니오", f"Base rate {latest_rate:.2f}%")
st.caption(
    "External API connection은 데이터 자동 수집, 데이터 최신성, 반복 업무 감소, 시나리오 분석 신뢰성 향상을 통해 "
    "AX Readiness를 높입니다. API key가 없거나 응답이 비어 있으면 sample/mock data로 안전하게 fallback합니다."
)
st.dataframe(
    [
        {
            "데이터 소스": "OpenDART",
            "현재 용도": "공시 목록 및 disclosure signal 확보",
            "상태": external_disclosures.attrs.get("status_message", "상태 정보 없음"),
        },
        {
            "데이터 소스": "ECOS",
            "현재 용도": "Scenario Engine market interest rate assumption",
            "상태": market_rates.attrs.get("status_message", "상태 정보 없음"),
        },
        {
            "데이터 소스": "KRX",
            "현재 용도": "Future roadmap",
            "상태": "v08에서는 placeholder roadmap으로 유지",
        },
    ],
    width="stretch",
    hide_index=True,
)

metric_cols = st.columns(4)
metric_cols[0].metric("Weighted AI Readiness Score", f"{weighted_score:.1f}/5", interpretation)
metric_cols[1].metric("AI Readiness Index", f"{weighted_score_pct:.0f}/100", "weighted scoring")
metric_cols[2].metric("Data Quality Flags", f"{high_or_watch_flags}개", f"High {high_flags}개")
metric_cols[3].metric("최우선 개선 Dimension", lowest_dimension["dimension"], f"{lowest_dimension['score']:.1f}/5")

signal_cols = st.columns(3)
with signal_cols[0]:
    signal_card(
        "진단 관점",
        "Data foundation",
        "AI 적용 가능성은 asset, debt, tax, disclosure 데이터가 하나의 의사결정 흐름으로 연결되는지에서 출발합니다.",
    )
with signal_cols[1]:
    signal_card(
        "해석",
        interpretation,
        interpretation_text[interpretation],
    )
with signal_cols[2]:
    signal_card(
        "CFO 질문",
        "Can we trust it?",
        "Dashboard 숫자, management narrative, Investor Q&A가 같은 source-of-truth에서 나오는지 확인합니다.",
    )

st.subheader("Data Quality Flags")
st.caption("Missing data, Inconsistent values, Unusual movement, Manual review required를 CFO 의사결정 리스크 관점으로 진단합니다.")

flag_display = quality_flags.rename(
    columns={
        "flag_type": "Flag 유형",
        "status": "상태",
        "evidence": "진단 근거",
        "impact": "CFO/IR 영향",
        "action": "권고 액션",
    }
)

st.dataframe(
    flag_display,
    width="stretch",
    hide_index=True,
    column_config={
        "상태": st.column_config.TextColumn("상태", help="Low, Watch, High"),
        "CFO/IR 영향": st.column_config.TextColumn("CFO/IR 영향", width="large"),
        "권고 액션": st.column_config.TextColumn("권고 액션", width="large"),
    },
)

left, right = st.columns([1.15, 1])

with left:
    st.subheader("AI Readiness Score by Dimension")
    st.caption("각 dimension 점수와 가중치를 함께 반영해 Weighted AI Readiness Score를 계산합니다.")
    chart_df = weighted_readiness.sort_values("score").copy()
    chart_df["score_label"] = chart_df["score"].map(lambda value: f"{value:.1f}")
    readiness_fig = px.bar(
        chart_df,
        x="score",
        y="dimension",
        orientation="h",
        text="score_label",
        color="score",
        color_continuous_scale=["#c94f4f", "#b76e00", "#007c89"],
        range_x=[0, 5],
        labels={"score": "Score", "dimension": ""},
    )
    readiness_fig.update_traces(textposition="outside", cliponaxis=False)
    readiness_fig.update_layout(
        height=420,
        margin=dict(l=10, r=60, t=20, b=10),
        coloraxis_showscale=False,
    )
    st.plotly_chart(readiness_fig, width="stretch")

with right:
    st.subheader("Peer AI Readiness")
    peer_fig = px.bar(
        peer_scores.sort_values("ai_readiness_score"),
        x="ai_readiness_score",
        y="reit_name",
        orientation="h",
        color="ai_readiness_score",
        color_continuous_scale=["#c94f4f", "#b76e00", "#007c89"],
        range_x=[0, 5],
        labels={"ai_readiness_score": "AI Readiness", "reit_name": ""},
    )
    peer_fig.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=10), coloraxis_showscale=False)
    st.plotly_chart(peer_fig, width="stretch")

st.subheader("Weighted Scoring Logic")
weighted_display = weighted_readiness.copy()
weighted_display["weight_pct"] = weighted_display["weight"] * 100
weighted_display["weighted_score"] = weighted_display["weighted_score"].round(2)
st.dataframe(
    weighted_display[
        ["dimension", "score", "weight_pct", "weighted_score", "interpretation", "next_step"]
    ].rename(
        columns={
            "dimension": "AI Readiness Dimension",
            "score": "Score",
            "weight_pct": "Weight %",
            "weighted_score": "Weighted Score",
            "interpretation": "진단 해석",
            "next_step": "Next Step",
        }
    ),
    width="stretch",
    hide_index=True,
    column_config={
        "Score": st.column_config.NumberColumn("Score", format="%.1f"),
        "Weight %": st.column_config.NumberColumn("Weight %", format="%.0f%%"),
        "Weighted Score": st.column_config.NumberColumn("Weighted Score", format="%.2f"),
        "진단 해석": st.column_config.TextColumn("진단 해석", width="large"),
        "Next Step": st.column_config.TextColumn("Next Step", width="large"),
    },
)

st.subheader("Interpretation")
interpretation_rows = [
    {
        "구분": "Strong",
        "기준": "3.8점 이상",
        "의미": "AI 기반 memo, Investor Q&A, scenario workflow를 pilot에서 운영 단계로 확장할 수 있습니다.",
    },
    {
        "구분": "Moderate",
        "기준": "3.0점 이상 3.8점 미만",
        "의미": "주요 데이터는 존재하지만 KPI 표준화와 검증 workflow 보완 후 AX 적용을 확대하는 것이 적절합니다.",
    },
    {
        "구분": "Needs Improvement",
        "기준": "3.0점 미만",
        "의미": "AI 기능보다 Data Quality, source owner, approval governance 정비가 우선입니다.",
    },
]
st.dataframe(interpretation_rows, width="stretch", hide_index=True)

st.subheader("Improvement Roadmap")
st.caption("진단 결과를 단기 데이터 정비, 중기 KPI/Scenario 표준화, 장기 AX 운영모델 전환 과제로 변환합니다.")
st.dataframe(
    roadmap.rename(
        columns={
            "horizon": "Roadmap 구간",
            "priority": "기간",
            "initiative": "개선 과제",
            "expected_impact": "기대 효과",
        }
    ),
    width="stretch",
    hide_index=True,
    column_config={
        "개선 과제": st.column_config.TextColumn("개선 과제", width="large"),
        "기대 효과": st.column_config.TextColumn("기대 효과", width="large"),
    },
)

st.subheader("AX Consulting Takeaway")
takeaway_color = status_palette["High" if high_flags else "Watch" if high_or_watch_flags else "Low"]
st.markdown(
    f"""
    <div class="consulting-hero" style="border-left-color:{takeaway_color};">
        <div class="eyebrow">CFO / AMC / IR action</div>
        <div class="hero-title">AI 적용 전에 신뢰 가능한 decision data layer를 먼저 확정해야 합니다.</div>
        <div class="hero-body">
            {selected_name}의 현재 진단은 <strong>{interpretation}</strong>입니다. 우선순위는
            <strong>{lowest_dimension["dimension"]}</strong> 보완과 High/Watch Data Quality Flag 정리입니다.
            이 기반이 갖춰져야 Scenario Engine 결과가 CFO 보고 메모와 Investor Q&A로 일관되게 전환됩니다.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
